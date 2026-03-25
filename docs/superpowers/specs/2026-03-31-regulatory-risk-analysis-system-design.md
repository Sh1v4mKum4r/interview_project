# Automated Regulatory Risk Analysis System — Design Spec

**Date**: 2026-03-31
**Status**: Approved
**Timeline**: ~3-5 days, demo in early April

---

## 1. Overview

A prototype system that processes financial market data and generates statistical and regulatory risk insights. Two main deliverables:

- **Task 1 (20 marks)**: Quantitative Risk Modelling Framework — statistical analysis, risk models, and quantitative techniques
- **Task 2 (30 marks)**: Automated Regulatory Analysis System — data ingestion, UI, backend processing, analytical engine, structured output

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, uvicorn |
| Analytics | numpy, scipy, pandas, scikit-learn, statsmodels |
| Report Gen | openpyxl |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| Charts | Plotly.js |
| HTTP Client | Axios, TanStack React Query |
| Data Format | JSON over REST |

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend                          │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ Parameter  │  │  Dashboard   │  │   Report Download    │ │
│  │  Panel     │  │  (Charts/    │  │   (Excel .xlsx)      │ │
│  │            │  │   Tables)    │  │                      │ │
│  └─────┬─────┘  └──────▲───────┘  └──────────▲───────────┘ │
└────────┼───────────────┼──────────────────────┼─────────────┘
         │ POST          │ JSON                 │ blob
         ▼               │                      │
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ /api/     │───▶│ Analytical   │───▶│ Report Generator │  │
│  │ endpoints │    │ Engine       │    │ (openpyxl)       │  │
│  └──────────┘    └──────┬───────┘    └──────────────────┘  │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐  │
│  │              Engine Modules                           │  │
│  │  ┌────────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐ │  │
│  │  │ Statistics │ │ Risk    │ │ Quant  │ │Regulatory│ │  │
│  │  │ Module     │ │ Module  │ │ Module │ │ Module   │ │  │
│  │  └────────────┘ └─────────┘ └────────┘ └──────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐  │
│  │              Data Layer                               │  │
│  │  ┌─────────────────┐  ┌────────────────────────────┐ │  │
│  │  │ Synthetic Data  │  │ File Ingestion             │ │  │
│  │  │ Generator       │  │ (CSV / Excel upload)       │ │  │
│  │  └─────────────────┘  └────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. User selects parameters in React (asset classes, risk model, time horizon, regulatory regime)
2. Frontend POSTs configuration to FastAPI
3. Backend loads/generates data, runs the analytical engine
4. Engine returns JSON results (statistics, risk metrics, chart data)
5. Frontend renders interactive dashboard
6. User can optionally download a formatted Excel report

## 4. Directory Structure

```
interview_project/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── api/
│   │   ├── routes.py            # All API endpoints
│   │   └── schemas.py           # Pydantic request/response models
│   ├── engine/
│   │   ├── statistics.py        # Moments, correlation, distribution fitting
│   │   ├── risk.py              # VaR (historical, parametric, MC), CVaR
│   │   ├── quantitative.py      # PCA, clustering, regression, exposure
│   │   ├── regulatory.py        # Basel III/IV, MiFID II checks
│   │   └── advanced.py          # Taylor series, Laplace, EVT/GPD
│   ├── data/
│   │   ├── generator.py         # Synthetic data generation
│   │   └── ingestion.py         # CSV/Excel file parsing & validation
│   ├── reports/
│   │   └── excel_report.py      # openpyxl report generation
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ParameterPanel.tsx
│   │   │   ├── DashboardGrid.tsx
│   │   │   ├── RiskSummaryCard.tsx
│   │   │   ├── CorrelationHeatmap.tsx
│   │   │   ├── DistributionChart.tsx
│   │   │   ├── PCAChart.tsx
│   │   │   ├── ClusterMap.tsx
│   │   │   ├── RegulatoryPanel.tsx
│   │   │   └── FileUpload.tsx
│   │   ├── api/
│   │   │   └── client.ts         # Axios instance + React Query hooks
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript interfaces
│   │   └── main.tsx
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── vite.config.ts
├── docs/
│   ├── architecture.md
│   ├── assumptions.md
│   ├── sample_output.md
│   └── models/
│       ├── statistical_risk.md
│       ├── var_models.md
│       ├── pca_factor.md
│       ├── clustering.md
│       ├── advanced.md
│       └── regulatory.md
├── data/                         # Sample datasets
└── README.md
```

## 5. Analytical Engine

### 5.1 Statistical Risk Analysis Module (`engine/statistics.py`)

**Distribution moments** — per asset and portfolio level:
- Mean: μ = (1/n) Σ xᵢ
- Variance: σ² = (1/(n-1)) Σ (xᵢ - μ)²
- Skewness: γ₁ = (1/n) Σ ((xᵢ - μ)/σ)³
- Kurtosis: κ = (1/n) Σ ((xᵢ - μ)/σ)⁴

**Correlation matrix** — pairwise Pearson correlations: ρ(X,Y) = cov(X,Y) / (σₓ · σᵧ)

**Distribution fitting** — fit returns to Normal, Student-t, Skewed-t distributions using MLE via `scipy.stats.fit()`. Compare using AIC/BIC.

**Factor distribution modelling** — decompose returns as: rᵢ = αᵢ + Σⱼ βᵢⱼ · Fⱼ + εᵢ where F are common factors extracted via PCA.

### 5.2 Risk Models Module (`engine/risk.py`)

**Historical VaR**:
- Sort historical returns ascending
- VaR_α = return at the (1-α) percentile
- For 95%: 13th worst day out of 252

**Parametric VaR**:
- VaR_α = μ + z_α · σ
- z₀.₉₅ = -1.645, z₀.₉₉ = -2.326
- Also implement Student-t variant for fat tails

**Monte Carlo VaR**:
- Cholesky decompose covariance matrix: Σ = L · Lᵀ
- Generate 10,000 correlated random vectors: r = μ + L · z where z ~ N(0,I)
- VaR = percentile of simulated portfolio returns

**Expected Shortfall (CVaR)**:
- ES_α = E[L | L > VaR_α]
- Average of all losses exceeding VaR
- Required by Basel III FRTB as replacement for VaR

### 5.3 Quantitative Module (`engine/quantitative.py`)

**PCA**:
- Compute covariance/correlation matrix of returns
- Eigenvalue decomposition: Σ = V · Λ · Vᵀ
- Principal components = eigenvectors sorted by descending eigenvalue
- Variance explained ratio: λᵢ / Σλ

**K-means clustering**:
- Features: mean return, volatility, skewness, kurtosis per asset
- Standardize features, run k-means with k=3-5 (elbow method)
- Output: cluster assignments and centroids

**Multi-factor regression**:
- Fama-French style: rᵢ - rf = αᵢ + β₁·MKT + β₂·SMB + β₃·HML + εᵢ
- Synthetic market, size, and value factors
- Output: coefficients, R², t-statistics, p-values

**Asset class exposure analysis**:
- Portfolio weight by asset class
- Risk contribution: wᵢ · (∂σₚ/∂wᵢ) = wᵢ · (Σw)ᵢ / σₚ
- Marginal VaR per asset class

### 5.4 Advanced Techniques Module (`engine/advanced.py`)

**Taylor series (Delta-Gamma) approximation**:
- ΔV ≈ δ·ΔS + ½·γ·(ΔS)²
- For derivative portfolios, second-order expansion captures convexity
- Apply to options positions using stored Greeks

**Laplace transforms**:
- Moment generating function: M(t) = E[e^(tX)]
- For aggregate loss: M_S(t) = M_N(ln(M_X(t))) where N is frequency, X is severity
- Demonstrate for credit risk aggregate loss estimation

**Extreme Value Theory / GPD**:
- Peaks-over-threshold method
- Fit Generalized Pareto Distribution to tail losses: F(x) = 1 - (1 + ξx/β)^(-1/ξ)
- ξ (shape), β (scale) estimated via MLE
- Produces tail VaR and ES estimates superior to normal assumption

### 5.5 Module Interface Contract

Every engine module function follows this signature pattern:

```python
def compute_<analysis>(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict   # time_horizon, confidence_level, etc.
) -> dict:
    """Returns a results dict with 'data' (for charts) and 'metrics' (for summary)."""
```

No module imports from another module. The API layer orchestrates calls.

## 6. Regulatory Framework

### 6.1 Basel III/IV (`engine/regulatory.py`)

**Capital adequacy**:
- CET1 ratio = CET1 capital / RWA ≥ 4.5%
- Tier 1 ratio = Tier 1 capital / RWA ≥ 6.0%
- Total capital ratio = Total capital / RWA ≥ 8.0%

**Risk-weighted assets** (Standardized Approach):
- Equities: 100% weight
- Sovereign bonds: 0% (AAA) to 150% (below B-)
- Corporate bonds: 20% (AAA/AA) to 150% (below B-)
- FX: 8% of net open position
- Derivatives: Current Exposure Method (replacement cost + PFE add-on)

**Leverage ratio**: Tier 1 capital / total exposure ≥ 3%

**LCR**: HQLA / net cash outflows (30 days) ≥ 100%
- Simplified: classify assets into Level 1 (govt bonds) and Level 2 (corp bonds)
- Apply haircuts: Level 1 = 0%, Level 2A = 15%, Level 2B = 50%

**FRTB alignment**: Use Expected Shortfall (97.5%) as primary market risk metric instead of VaR

### 6.2 MiFID II

**Transaction reporting**: Generate mock RTS 25 reports with fields — instrument ISIN, price, quantity, venue MIC, timestamp, buyer/seller LEI

**Best execution**: Compare execution price vs. VWAP benchmark, flag deviations > 1 standard deviation

**Position limits**: Configurable thresholds for commodity derivatives; flag breaches

**Transparency reports**: Pre/post-trade reports showing bid/ask spreads and trade sizes

### 6.3 UI Integration

- Regulatory regime selected via checkboxes (Basel III/IV, MiFID II, or both)
- Compliance panel with traffic-light indicators: green (pass), amber (marginal), red (fail)
- Drill-down per metric shows calculation breakdown
- Report includes regulatory summary sheet

## 7. Data Layer

### 7.1 Synthetic Data Generator (`data/generator.py`)

**Equities** (10 stocks across 4 sectors):
- Sectors: Tech (3), Finance (3), Healthcare (2), Energy (2)
- Daily log-returns via multivariate normal with realistic covariance
- Annualized vol: 15-40% depending on sector
- 252 trading days default

**Fixed Income** (5 bonds):
- GOV_2Y, GOV_10Y, GOV_30Y, CORP_5Y_A, CORP_10Y_BBB
- Yield simulation → price via duration: ΔP/P ≈ -D · Δy
- Ratings assigned for RWA calculation

**Commodities** (3 assets):
- Gold, Oil, Natural Gas
- Ornstein-Uhlenbeck process: dX = θ(μ - X)dt + σdW
- Higher vol, lower equity correlation

**FX** (4 pairs):
- EUR/USD, GBP/USD, USD/JPY, USD/CHF
- Correlated with equity markets at realistic levels (ρ ≈ 0.1-0.3)

**Derivatives** (3 options):
- European call/put on select equities
- Black-Scholes pricing: C = S·N(d₁) - K·e^(-rT)·N(d₂)
- Store Greeks: delta, gamma, vega

### 7.2 File Ingestion (`data/ingestion.py`)

- Accept CSV (.csv) and Excel (.xlsx) via file upload endpoint
- Auto-detect columns: date column + numeric asset columns
- Validation: missing values, non-numeric data, date parsing errors
- Normalization: convert prices → returns if needed, align date index
- Clear error messages for unrecognizable formats

### 7.3 Internal Data Format

```python
{
    "returns": pd.DataFrame,       # (dates × assets) daily log-returns
    "prices": pd.DataFrame,        # (dates × assets) price levels
    "metadata": {
        "asset_classes": {"AAPL": "equity", "GOV_10Y": "fixed_income", ...},
        "sectors": {"AAPL": "tech", "JPM": "finance", ...},
        "ratings": {"GOV_10Y": "AAA", "CORP_5Y_A": "A", ...},
        "derivatives": {
            "AAPL_CALL": {"type": "call", "strike": 150, "expiry": "2026-06-30",
                          "delta": 0.65, "gamma": 0.03, "vega": 0.25}
        }
    }
}
```

## 8. Frontend

### 8.1 Layout

Three-panel dashboard:
- **Left sidebar**: Parameter selection panel (asset classes, risk model, time horizon, regulatory regime, file upload, "Run Analysis" button)
- **Main area**: Responsive grid of chart/card components
- **Top bar**: Logo, system title, upload and download buttons
- **Bottom bar**: Status messages

### 8.2 Components

| Component | Chart Type | Data Source |
|---|---|---|
| RiskSummaryCard | KPI cards | VaR, CVaR, Sharpe, volatility |
| CorrelationHeatmap | Plotly heatmap | Correlation matrix |
| DistributionChart | Histogram + line overlay | Return distribution + fitted curve, moments |
| PCAChart | Bar + line (scree plot) | Eigenvalues, cumulative variance |
| ClusterMap | 2D scatter, colored by cluster | PCA-reduced asset positions |
| RegulatoryPanel | Traffic-light indicators + table | Regulatory metric pass/fail |

### 8.3 Interaction Flow

1. Page loads → auto-runs default analysis with synthetic data
2. User adjusts parameters → clicks "Run Analysis" → loading state → dashboard refreshes
3. All charts are interactive (hover tooltips, zoom, pan via Plotly)
4. "Download Report" generates Excel server-side and streams to browser

## 9. Excel Report

Six sheets generated via openpyxl:

| Sheet | Contents |
|---|---|
| Executive Summary | Portfolio overview, key risk metrics, regulatory pass/fail |
| Statistical Analysis | Per-asset moments, correlation matrix, distribution fits, PCA |
| Risk Model Output | VaR by model type, by asset class, CVaR alongside |
| Quantitative Analysis | Cluster assignments, regression coefficients, exposure breakdown |
| Regulatory Report | Basel III/IV ratios with thresholds, MiFID II transaction reports |
| Raw Data | Returns matrix, price series, asset metadata |

Formatting: styled headers, alternating row colors, conditional formatting on pass/fail, frozen headers, auto-fitted columns.

## 10. Documentation

```
docs/
├── architecture.md
├── assumptions.md
├── sample_output.md
└── models/
    ├── statistical_risk.md
    ├── var_models.md
    ├── pca_factor.md
    ├── clustering.md
    ├── advanced.md
    └── regulatory.md
```

Each model doc contains:
1. **What it is** — plain English explanation
2. **Why it matters** — regulatory/market context
3. **The math** — full derivation, step by step
4. **Implementation** — how code maps to math
5. **Interpretation guide** — what output values mean
6. **Demo talking points** — 3-4 bullets for live walkthrough

### Assumptions Document

Single file listing all simplifications:
- Returns assumed i.i.d. for parametric models
- Sample covariance (no shrinkage estimator)
- Basel RWA uses Standardized Approach only
- LCR uses simplified HQLA classification
- Derivative Greeks pre-computed, not dynamic
- MiFID II uses mock transaction data
- Black-Scholes assumes constant volatility

### Sample Output Walkthrough

Guided interpretation of one complete analysis run with narrative connecting dashboard visuals to risk insights and regulatory implications.

## 11. API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/analyze` | Run full analysis with given parameters |
| POST | `/api/upload` | Upload CSV/Excel data file |
| GET | `/api/data/default` | Get default synthetic dataset info |
| POST | `/api/report/excel` | Generate and download Excel report |
| GET | `/api/config/options` | Get available asset classes, models, regimes |

### Request Schema for `/api/analyze`

```json
{
    "asset_classes": ["equity", "fixed_income", "commodity", "fx", "derivative"],
    "risk_model": "historical" | "parametric" | "monte_carlo",
    "time_horizon": "1D" | "10D" | "1M" | "1Y",
    "confidence_level": 0.95 | 0.99,
    "regulatory_regimes": ["basel3", "mifid2"],
    "data_source": "synthetic" | "uploaded",
    "upload_id": "optional - reference to previously uploaded file"
}
```
