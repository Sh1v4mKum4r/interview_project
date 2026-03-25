"""
Pydantic request/response models for the API layer.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class RiskModelType(str, Enum):
    historical = "historical"
    parametric = "parametric"
    monte_carlo = "monte_carlo"


class TimeHorizon(str, Enum):
    one_day = "1D"
    ten_day = "10D"
    one_month = "1M"
    one_year = "1Y"


class ConfidenceLevel(float, Enum):
    ninety_five = 0.95
    ninety_nine = 0.99


class AnalysisRequest(BaseModel):
    asset_classes: list[str] = Field(
        default=["equity", "fixed_income", "commodity", "fx", "derivative"],
        description="Asset classes to include in the analysis",
    )
    risk_model: RiskModelType = Field(
        default=RiskModelType.historical,
        description="Risk model to use for VaR calculation",
    )
    time_horizon: TimeHorizon = Field(
        default=TimeHorizon.one_day,
        description="Time horizon for risk metrics",
    )
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.ninety_five,
        description="Confidence level for VaR/ES",
    )
    regulatory_regimes: list[str] = Field(
        default=["basel3"],
        description="Regulatory regimes to apply",
    )
    data_source: str = Field(
        default="synthetic",
        description="'synthetic' or 'uploaded'",
    )
    upload_id: Optional[str] = Field(
        default=None,
        description="Reference to previously uploaded file",
    )


class CapitalConfig(BaseModel):
    cet1: float = Field(default=1_200_000, description="CET1 capital")
    tier1: float = Field(default=1_500_000, description="Tier 1 capital")
    total: float = Field(default=2_000_000, description="Total capital")


class ReportRequest(BaseModel):
    analysis_config: AnalysisRequest = Field(default_factory=AnalysisRequest)
    capital_config: CapitalConfig = Field(default_factory=CapitalConfig)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"


class ConfigOptionsResponse(BaseModel):
    asset_classes: list[str] = [
        "equity", "fixed_income", "commodity", "fx", "derivative"
    ]
    risk_models: list[str] = ["historical", "parametric", "monte_carlo"]
    time_horizons: list[str] = ["1D", "10D", "1M", "1Y"]
    confidence_levels: list[float] = [0.95, 0.99]
    regulatory_regimes: list[str] = ["basel3", "mifid2"]


class UploadResponse(BaseModel):
    upload_id: str
    filename: str
    num_assets: int
    num_days: int
    asset_classes: dict[str, str]
    message: str = "File uploaded and parsed successfully"
