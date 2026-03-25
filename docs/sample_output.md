# Sample Output Walkthrough

This guide walks through a complete analysis run using the default synthetic data. Use this as a script for your live demo.

## Starting the Analysis

When the page loads, it auto-runs an analysis with default parameters:
- **Asset classes**: All (Equities, Fixed Income, Commodities, FX, Derivatives)
- **Risk model**: Historical
- **Time horizon**: 1 Day
- **Confidence level**: 95%
- **Regulatory regime**: Basel III/IV

## Reading the Dashboard

### 1. Risk Summary Cards (Top Row)

You'll see four key metrics:

- **VaR (95%, 1D): ~$91,600** — "This means that on 95% of trading days, we expect portfolio losses not to exceed $91,600. Or equivalently, there's a 5% chance of losing more than this on any given day."

- **Expected Shortfall: ~$130,000** — "When we DO exceed VaR — in that worst 5% of days — the average loss is about $130,000. ES tells us how bad the bad days actually are, which VaR alone doesn't."

- **Portfolio Volatility: ~12%** — "Annualized standard deviation of portfolio returns. This is the overall risk level — comparable to a moderate balanced fund."

- **Sharpe Ratio** — "Risk-adjusted return. Values above 1.0 suggest the portfolio is generating good returns for the risk taken."

### 2. Correlation Heatmap (Left Middle)

"The heatmap shows pairwise correlations between all 25 assets. Notice several patterns:

- **Equities within the same sector are highly correlated** (dark red blocks along the diagonal for Tech stocks AAPL/MSFT/GOOGL, Finance stocks JPM/GS/BAC). This is expected — they're driven by similar economic factors.

- **Equities and Fixed Income show low/negative correlation** — this is the diversification benefit that portfolio theory depends on. When stocks fall, bonds tend to hold or rise.

- **Commodities (GOLD, OIL, NATGAS) show low correlation to equities** — another diversification source, especially gold as a safe haven.

- **FX pairs** show moderate correlation to equities, reflecting global risk appetite flows."

### 3. Distribution Chart (Right Middle)

"This shows the distribution of portfolio returns with fitted curves:

- **The histogram** shows the actual observed daily returns — notice it's roughly bell-shaped but with heavier tails than a normal distribution.

- **The Normal curve (red)** doesn't capture the tails well — it underestimates extreme events.

- **The Student-t curve (green)** fits better because it has heavier tails, controlled by the degrees-of-freedom parameter.

- **Moments displayed**: The negative skewness (-0.1 to -0.3) confirms the left tail is heavier — large losses are more likely than large gains. Kurtosis above 3 confirms fat tails. This is why parametric VaR assuming normality can be dangerous."

### 4. PCA Scree Plot (Left Bottom)

"Principal Component Analysis decomposes portfolio variance into independent risk factors:

- **PC1 explains ~25-30% of variance** — this is typically the 'market factor', the overall direction of equity markets.

- **PC2 explains ~12-15%** — often captures the equity-vs-bonds rotation.

- **PC3 explains ~8-10%** — might capture sector rotation or commodity effects.

- **The first 3 components explain ~50% of total variance**, meaning about half the portfolio's risk comes from just 3 systematic factors. The remaining variance is diversified, idiosyncratic risk."

### 5. Cluster Map (Right Bottom)

"K-means clustering groups assets with similar risk profiles:

- **Cluster 0 (blue)** — typically the equity names, characterized by moderate-to-high volatility and negative skewness.

- **Cluster 1 (orange)** — often contains fixed income instruments, with lower volatility and smaller tails.

- **Cluster 2 (green)** — commodities and FX, with distinct volatility and mean-reversion characteristics.

This tells a portfolio manager: if you want to diversify, add assets from different clusters."

### 6. Advanced Techniques (Full Width)

"This section demonstrates sophisticated quantitative modelling beyond standard risk metrics:

- **Taylor Series (Delta-Gamma)** — 'For our derivatives portfolio, we use second-order approximations. Standard Delta-only VaR is ~$45,000, but when we add the Gamma term to account for convexity, the VaR increases to ~$52,000. This $7,000 Gamma correction is critical for option portfolios.'

- **Laplace Transforms (Aggregate Loss)** — 'We model aggregate credit losses as a compound Poisson process. This shows the expected annual loss is about $500,000, but the 99% aggregate VaR is over $1.2M. This helps us set aside capital for extreme loss events.'

- **Extreme Value Theory (EVT/GPD)** — 'We fit a Generalized Pareto Distribution to the 10% worst losses. The shape parameter (ξ) of 0.15 confirms fat tails. Notice the EVT VaR is 15-20% higher than the normal VaR, showing why the normal distribution is insufficient for tail risk.'"

### 7. Regulatory Compliance Panel (Bottom)

"The traffic-light panel shows Basel III/IV compliance:

- **CET1 Ratio: ~17% (Green ✓)** — well above the 4.5% minimum. 'The portfolio's common equity tier 1 capital is 17% of risk-weighted assets, providing a comfortable buffer.'

- **Tier 1 Ratio: ~21% (Green ✓)** — above the 6% minimum.

- **Total Capital: ~28% (Green ✓)** — above 8% minimum.

- **Leverage Ratio: ~3.2% (Amber ⚠)** — just above the 3% minimum. 'This is marginal — if exposure increases, we could breach the leverage limit. This is worth flagging to risk management.'

- **LCR: ~134% (Green ✓)** — above 100%, meaning sufficient liquid assets to cover 30-day stress outflows.

The amber leverage ratio demonstrates the system working correctly — it identifies areas of concern, not just blanket passes."

## Excel Report

Click "Download Report" to generate the formatted Excel workbook:

- **Sheet 1 (Executive Summary)**: One-page overview with key metrics and regulatory status
- **Sheet 2 (Statistical Analysis)**: Per-asset moments table, full correlation matrix, distribution fits
- **Sheet 3 (Risk Model Output)**: Side-by-side VaR comparison across all three models
- **Sheet 4 (Quantitative Analysis)**: PCA results, cluster assignments, factor regression coefficients
- **Sheet 5 (Regulatory Report)**: Basel III ratios with thresholds, RWA breakdown, MiFID II transaction reports
- **Sheet 6 (Raw Data)**: Returns matrix and asset metadata for audit trail

## Key Demo Talking Points

1. "The system demonstrates end-to-end risk analysis: from raw market data through statistical modelling to regulatory compliance assessment."

2. "We implement three different VaR methodologies because each has trade-offs: Historical is assumption-free but backward-looking; Parametric is fast but assumes a distribution; Monte Carlo is flexible but computationally expensive."

3. "Basel III moved from VaR to Expected Shortfall as the primary risk metric because VaR doesn't tell you how bad losses can get in the tail. Our system implements both, showing why ES gives a more complete picture."

4. "The PCA analysis reveals that despite having 25 assets, most portfolio risk is driven by just 3-5 systematic factors. This has practical implications for hedging — you can hedge most of your risk by trading just a few factor-mimicking portfolios."

5. "The regulatory module isn't just checking boxes — it's computing actual capital adequacy ratios from the portfolio data using Basel III standardized approach weights. The amber leverage warning shows the system correctly identifying areas of concern."
