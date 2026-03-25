# System Architecture

## Overview

The Regulatory Risk Analysis System is a full-stack prototype for automated financial market data analysis and regulatory risk reporting. It processes portfolio data through a quantitative analytics engine and presents results via an interactive dashboard.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                    │
│                                                             │
│  ParameterPanel ──► API Client (Axios) ──► DashboardGrid   │
│  FileUpload          React Query           6 Chart Components│
│                                            RegulatoryPanel  │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API (JSON)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Python)                    │
│                                                             │
│  API Layer (routes.py, schemas.py)                          │
│       │                                                     │
│       ├──► Analytical Engine                                │
│       │    ├── statistics.py  (moments, correlation, dist)  │
│       │    ├── risk.py        (VaR, ES)                     │
│       │    ├── quantitative.py (PCA, clustering, regression)│
│       │    ├── regulatory.py  (Basel III, MiFID II)         │
│       │    └── advanced.py    (Taylor, Laplace, EVT)        │
│       │                                                     │
│       ├──► Data Layer                                       │
│       │    ├── generator.py   (synthetic data)              │
│       │    └── ingestion.py   (CSV/Excel upload)            │
│       │                                                     │
│       └──► Report Generator                                 │
│            └── excel_report.py (6-sheet .xlsx)              │
└─────────────────────────────────────────────────────────────┘
```

## Design Principles

### Separation of Concerns
Each engine module is independent — no module imports from another. The API routes layer orchestrates calls to the appropriate modules based on user parameters. This makes each module testable and replaceable independently.

### Uniform Interface Contract
Every engine function follows the same signature:
```python
def compute_<analysis>(returns: pd.DataFrame, metadata: dict, config: dict) -> dict
```
Returns a dict with `"metrics"` (summary values) and `"data"` (chart-ready arrays). This uniform contract means the API layer can call any module without special handling.

### Data Flow
1. **Input**: User selects parameters in React UI (asset classes, risk model, time horizon, regulatory regime)
2. **Request**: Frontend POSTs configuration as JSON to `/api/analyze`
3. **Data Loading**: Backend loads synthetic data or retrieves previously uploaded data
4. **Filtering**: Data is filtered to include only selected asset classes
5. **Analysis**: Engine modules run in sequence: statistics → risk → quantitative → regulatory → advanced
6. **Response**: Results returned as JSON with numpy types converted to Python natives
7. **Rendering**: React renders interactive Plotly.js charts and summary cards
8. **Export**: Optional Excel report generated server-side and streamed as download

### Technology Choices

| Choice | Rationale |
|---|---|
| FastAPI | Async-ready, auto-generated OpenAPI docs, Pydantic validation |
| React + TypeScript | Type safety, component reuse, professional demo appearance |
| Plotly.js | Best-in-class financial charting, interactive (zoom, hover, pan) |
| Tailwind CSS | Rapid styling, consistent design, responsive by default |
| openpyxl | Full control over Excel formatting, conditional formatting, charts |
| scipy/sklearn | Industry-standard implementations of statistical methods |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/config/options` | Available parameter choices |
| GET | `/api/data/default` | Default synthetic dataset info |
| POST | `/api/analyze` | Run full analysis pipeline |
| POST | `/api/upload` | Upload CSV/Excel data |
| POST | `/api/report/excel` | Generate Excel report |

## Running the System

### Backend
```bash
cd interview_project
source .venv/bin/activate
python -m uvicorn backend.main:app --reload --port 6969
```

### Frontend
```bash
cd interview_project/frontend
npm run dev
```

The frontend dev server proxies `/api/*` requests to the backend at port 6969.
