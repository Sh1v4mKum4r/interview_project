"""
FastAPI routes — all REST API endpoints.
Orchestrates engine modules: loads data, calls the right engine functions, returns JSON.
"""

import uuid
import io
import json
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from backend.api.schemas import (
    AnalysisRequest,
    ReportRequest,
    HealthResponse,
    ConfigOptionsResponse,
    UploadResponse,
)
from backend.data.generator import generate_synthetic_data, generate_portfolio_weights
from backend.data.ingestion import ingest_file
from backend.engine.statistics import (
    compute_moments,
    compute_correlation,
    compute_distribution_fitting,
    compute_factor_model,
)
from backend.engine.risk import compute_var_summary
from backend.engine.quantitative import (
    compute_pca,
    compute_clustering,
    compute_regression,
    compute_exposure,
)
from backend.engine.regulatory import compute_regulatory_summary
from backend.engine.advanced import compute_advanced_summary
from backend.reports.excel_report import generate_excel_report


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def _numpy_safe(obj):
    """Recursively convert numpy types to Python native types."""
    if isinstance(obj, dict):
        return {k: _numpy_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_numpy_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


router = APIRouter(prefix="/api")

# In-memory storage for uploaded datasets (prototype — not for production)
_uploaded_data: dict[str, dict] = {}
_cached_synthetic: dict | None = None


def _get_synthetic_data() -> dict:
    """Get or generate cached synthetic data."""
    global _cached_synthetic
    if _cached_synthetic is None:
        _cached_synthetic = generate_synthetic_data()
    return _cached_synthetic


def _filter_by_asset_classes(data: dict, asset_classes: list[str]) -> dict:
    """Filter dataset to only include the selected asset classes."""
    ac_map = data["metadata"]["asset_classes"]
    keep = [asset for asset, cls in ac_map.items() if cls in asset_classes]

    if not keep:
        raise HTTPException(
            status_code=400,
            detail=f"No assets match the selected classes: {asset_classes}",
        )

    returns = data["returns"][keep] if all(k in data["returns"].columns for k in keep) else data["returns"]
    prices = data["prices"][keep] if all(k in data["prices"].columns for k in keep) else data["prices"]

    filtered_meta = {
        "asset_classes": {k: v for k, v in ac_map.items() if k in keep},
        "sectors": {k: v for k, v in data["metadata"].get("sectors", {}).items() if k in keep},
        "ratings": {k: v for k, v in data["metadata"].get("ratings", {}).items() if k in keep},
        "derivatives": {k: v for k, v in data["metadata"].get("derivatives", {}).items() if k in keep},
    }

    return {"returns": returns, "prices": prices, "metadata": filtered_meta}


def _build_config(req: AnalysisRequest, metadata: dict, portfolio_value: float = 10_000_000) -> dict:
    """Build the config dict that all engine modules expect."""
    weights = generate_portfolio_weights(metadata)
    return {
        "confidence_level": req.confidence_level.value,
        "time_horizon": req.time_horizon.value,
        "weights": weights,
        "portfolio_value": portfolio_value,
        "capital": {"cet1": 1_200_000, "tier1": 1_500_000, "total": 2_000_000},
    }


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse()


@router.get("/config/options", response_model=ConfigOptionsResponse)
def get_config_options():
    return ConfigOptionsResponse()


@router.get("/data/default")
def get_default_data():
    """Return info about the default synthetic dataset."""
    data = _get_synthetic_data()
    return {
        "num_assets": len(data["returns"].columns),
        "num_days": len(data["returns"]),
        "asset_classes": data["metadata"]["asset_classes"],
        "sectors": data["metadata"]["sectors"],
        "assets": list(data["returns"].columns),
        "date_range": {
            "start": str(data["returns"].index[0].date()),
            "end": str(data["returns"].index[-1].date()),
        },
    }


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a CSV or Excel file for analysis."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        data = ingest_file(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    upload_id = str(uuid.uuid4())[:8]
    _uploaded_data[upload_id] = data

    return UploadResponse(
        upload_id=upload_id,
        filename=file.filename,
        num_assets=len(data["returns"].columns),
        num_days=len(data["returns"]),
        asset_classes=data["metadata"]["asset_classes"],
    )


@router.post("/analyze")
def run_analysis(req: AnalysisRequest):
    """Run the full analysis pipeline and return all results."""
    # Load data
    if req.data_source == "uploaded" and req.upload_id:
        if req.upload_id not in _uploaded_data:
            raise HTTPException(status_code=404, detail="Upload not found. Please re-upload.")
        data = _uploaded_data[req.upload_id]
    else:
        data = _get_synthetic_data()

    # Filter by selected asset classes
    data = _filter_by_asset_classes(data, req.asset_classes)
    config = _build_config(req, data["metadata"])
    returns = data["returns"]
    metadata = data["metadata"]

    results = {}

    # Statistical analysis
    try:
        results["moments"] = compute_moments(returns, metadata, config)
        results["correlation"] = compute_correlation(returns, metadata, config)
        results["distribution_fitting"] = compute_distribution_fitting(returns, metadata, config)
        results["factor_model"] = compute_factor_model(returns, metadata, config)
    except Exception as e:
        results["statistics_error"] = str(e)

    # Risk models
    try:
        results["risk"] = compute_var_summary(returns, metadata, config)
    except Exception as e:
        results["risk_error"] = str(e)

    # Quantitative techniques
    try:
        results["pca"] = compute_pca(returns, metadata, config)
        results["clustering"] = compute_clustering(returns, metadata, config)
        results["regression"] = compute_regression(returns, metadata, config)
        results["exposure"] = compute_exposure(returns, metadata, config)
    except Exception as e:
        results["quantitative_error"] = str(e)

    # Regulatory analysis
    try:
        if req.regulatory_regimes:
            results["regulatory"] = compute_regulatory_summary(returns, metadata, config)
    except Exception as e:
        results["regulatory_error"] = str(e)

    # Advanced techniques
    try:
        results["advanced"] = compute_advanced_summary(returns, metadata, config)
    except Exception as e:
        results["advanced_error"] = str(e)

    return JSONResponse(content=_numpy_safe(results))


@router.post("/report/excel")
def generate_report(req: ReportRequest):
    """Generate and download a formatted Excel report."""
    # Run full analysis first
    analysis_req = req.analysis_config
    if analysis_req.data_source == "uploaded" and analysis_req.upload_id:
        if analysis_req.upload_id not in _uploaded_data:
            raise HTTPException(status_code=404, detail="Upload not found.")
        data = _uploaded_data[analysis_req.upload_id]
    else:
        data = _get_synthetic_data()

    data = _filter_by_asset_classes(data, analysis_req.asset_classes)
    config = _build_config(analysis_req, data["metadata"])
    config["capital"] = {
        "cet1": req.capital_config.cet1,
        "tier1": req.capital_config.tier1,
        "total": req.capital_config.total,
    }

    returns = data["returns"]
    metadata = data["metadata"]

    # Collect all results
    analysis_results = {}
    try:
        analysis_results["moments"] = compute_moments(returns, metadata, config)
        analysis_results["correlation"] = compute_correlation(returns, metadata, config)
        analysis_results["distribution_fitting"] = compute_distribution_fitting(returns, metadata, config)
        analysis_results["risk"] = compute_var_summary(returns, metadata, config)
        analysis_results["pca"] = compute_pca(returns, metadata, config)
        analysis_results["clustering"] = compute_clustering(returns, metadata, config)
        analysis_results["regression"] = compute_regression(returns, metadata, config)
        analysis_results["exposure"] = compute_exposure(returns, metadata, config)
        analysis_results["regulatory"] = compute_regulatory_summary(returns, metadata, config)
        analysis_results["advanced"] = compute_advanced_summary(returns, metadata, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # Generate Excel
    try:
        excel_bytes = generate_excel_report(analysis_results, returns, data["prices"], metadata, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=risk_analysis_report.xlsx"},
    )
