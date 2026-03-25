# Automated Regulatory Risk Analysis System

A full-stack prototype for automated financial market data analysis and regulatory risk reporting.

## Features

### Quantitative Risk Modelling (Task 1)
- **Statistical Analysis**: Distribution moments (mean, variance, skewness, kurtosis), correlation matrices, distribution fitting (Normal, Student-t, Skewed Normal with AIC selection)
- **Risk Models**: Historical VaR, Parametric VaR (Normal + Student-t), Monte Carlo VaR (10,000 simulations), Expected Shortfall/CVaR
- **Quantitative Techniques**: PCA, K-means clustering, Fama-French factor regression, asset class exposure analysis
- **Advanced Techniques**: Delta-Gamma (Taylor series) approximation, Laplace transforms for aggregate loss, Extreme Value Theory (GPD)

### Automated Analysis System (Task 2)
- **Data Ingestion**: Synthetic multi-asset data generator + CSV/Excel file upload
- **Asset Classes**: Equities (10), Fixed Income (5), Commodities (3), FX (4), Derivatives (3)
- **Interactive Dashboard**: React UI with Plotly.js charts (heatmaps, histograms, scree plots, scatter plots)
- **Regulatory Framework**: Basel III/IV (capital adequacy, RWA, leverage, LCR, FRTB) + MiFID II (transaction reporting, best execution, position limits)
- **Excel Reports**: 6-sheet formatted workbook with styling, conditional formatting, and full analysis output

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, uvicorn |
| Analytics | NumPy, SciPy, Pandas, scikit-learn, statsmodels |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Charts | Plotly.js (react-plotly.js) |
| Reports | openpyxl |

### Quick Start

Prerequisites:
- Python 3.11+
- Node.js 18+

#### One-Command Start
```bash
./start.sh
```

#### Manual Start

##### Backend
```bash
# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Start the API server
python -m uvicorn backend.main:app --reload --port 6969
```

##### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the dashboard auto-loads with synthetic data analysis.

## Project Structure


```
interview_project/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── api/                 # REST endpoints and Pydantic schemas
│   ├── engine/              # Analytical engine (5 modules)
│   ├── data/                # Data generation and ingestion
│   └── reports/             # Excel report generation
├── frontend/
│   └── src/
│       ├── components/      # React dashboard components
│       ├── api/             # API client (Axios + React Query)
│       └── types/           # TypeScript interfaces
├── docs/
│   ├── architecture.md      # System architecture
│   ├── assumptions.md       # Simplifications and limitations
│   ├── sample_output.md     # Demo walkthrough script
│   └── models/              # Mathematical documentation per model
└── data/                    # Sample datasets
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/config/options` | Available parameters |
| POST | `/api/analyze` | Run full analysis |
| POST | `/api/upload` | Upload data file |
| POST | `/api/report/excel` | Generate Excel report |

## Documentation

See `docs/` for:
- **Architecture**: System design and data flow
- **Model Documentation**: Mathematical derivations for every implemented model
- **Assumptions**: All simplifications with justification
- **Sample Output**: Guided walkthrough for the demo
