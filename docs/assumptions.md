# Assumptions and Simplifications

This document lists all simplifications made in the prototype system, explains what a production system would do differently, and justifies why each simplification is acceptable for this demonstration.

---

## Statistical Assumptions

### 1. Returns are assumed i.i.d.
**Simplification**: Parametric models assume returns are independent and identically distributed across time.
**Production alternative**: Use GARCH models for time-varying volatility, regime-switching models, or rolling-window estimation.
**Justification**: i.i.d. is the standard baseline assumption in most textbook and regulatory frameworks. GARCH adds complexity without changing the fundamental risk measures for a prototype.

### 2. Sample covariance matrix (no shrinkage)
**Simplification**: We use the raw sample covariance matrix for correlation, PCA, and portfolio risk.
**Production alternative**: Ledoit-Wolf shrinkage estimator, factor-based covariance, or Bayesian estimation to reduce estimation error.
**Justification**: With 252 observations and 25 assets, the sample covariance is reasonably well-conditioned. Shrinkage matters more when assets >> observations.

### 3. Correlation assumed constant
**Simplification**: A single correlation matrix estimated from the full sample period.
**Production alternative**: DCC-GARCH (Dynamic Conditional Correlation) or regime-switching models that allow correlation to change over time.
**Justification**: Constant correlation is the standard assumption in Basel III standardized approach and most portfolio optimization frameworks.

### 4. Portfolio weights are equal-weighted by default
**Simplification**: Non-derivative assets receive equal weights summing to 1.
**Production alternative**: Market-cap weighting, risk parity, mean-variance optimization, or custom weights.
**Justification**: Equal weighting is a simple, transparent baseline. The system accepts any weight vector through the API.

---

## Risk Model Assumptions

### 5. Risk-free rate assumed at 4% annualized
**Simplification**: A fixed 0.04/252 daily risk-free rate for excess return calculations.
**Production alternative**: Dynamic risk-free rate from treasury curves (e.g., 3-month T-bill rate from FRED).
**Justification**: The exact risk-free rate has minimal impact on VaR/ES calculations. 4% is a reasonable approximation for the current rate environment.

### 6. Monte Carlo uses 10,000 simulations
**Simplification**: Fixed 10,000 paths with a normal copula.
**Production alternative**: More simulations (100,000+), variance reduction techniques (antithetic variates, importance sampling), Student-t copula.
**Justification**: 10,000 simulations give stable VaR estimates at 95% and 99% confidence. More simulations improve precision but increase computation time for a demo.

### 7. VaR time scaling uses square-root-of-time rule
**Simplification**: VaR_T = VaR_1D × √T
**Production alternative**: Multi-day simulation or scaling with autocorrelation adjustment.
**Justification**: Square-root-of-time is the standard industry convention assumed in Basel III. It's exact under i.i.d. assumptions.

---

## Regulatory Assumptions

### 8. Basel RWA uses Standardized Approach only
**Simplification**: Fixed risk weights by asset class and rating.
**Production alternative**: Internal Ratings-Based (IRB) approach with institution-specific risk models, or Advanced Measurement Approach for operational risk.
**Justification**: The Standardized Approach is the prescribed method for banks that don't have regulatory approval for internal models. It demonstrates the framework correctly.

### 9. LCR uses simplified HQLA classification
**Simplification**: Assets classified as Level 1/2A/2B based on asset class and rating. Net outflow = 5% of portfolio value.
**Production alternative**: Detailed liability-side modelling, contractual cash flows, behavioural adjustments for deposit runoff.
**Justification**: The simplified approach demonstrates the LCR concept and calculation mechanics. A full implementation requires institution-specific balance sheet data.

### 10. Capital amounts are configurable defaults
**Simplification**: CET1 = $1.2M, Tier 1 = $1.5M, Total = $2.0M against a $10M portfolio.
**Production alternative**: Real capital figures from the institution's balance sheet.
**Justification**: These defaults produce realistic ratios that demonstrate the system working correctly, including triggering amber warnings to show the monitoring logic.

---

## Derivative Assumptions

### 11. Greeks are pre-computed, not dynamically updated
**Simplification**: Delta, gamma, and vega are set at option inception and held constant.
**Production alternative**: Dynamic Greek computation using Black-Scholes or more sophisticated pricing models, updated daily with current market data.
**Justification**: Pre-computed Greeks are sufficient to demonstrate the delta-gamma approximation concept. Dynamic computation would require a full pricing engine.

### 12. Black-Scholes assumes constant volatility
**Simplification**: Flat volatility for option pricing — no volatility smile or term structure.
**Production alternative**: Local volatility, stochastic volatility (Heston), or SABR model with a full volatility surface.
**Justification**: Black-Scholes is the standard reference model. The volatility smile exists in real markets, but our prototype focuses on risk methodology rather than pricing accuracy.

---

## Data Assumptions

### 13. Synthetic data uses multivariate normal returns
**Simplification**: Equity returns are generated from a multivariate normal distribution (though commodities use Ornstein-Uhlenbeck).
**Production alternative**: Real market data, possibly with GARCH-filtered residuals or bootstrapped returns.
**Justification**: Multivariate normal generates realistic-looking returns with controllable properties (correlation, volatility). The system also supports uploading real data.

### 14. MiFID II uses mock transaction data
**Simplification**: Transaction reports, ISINs, LEIs, and venue MICs are synthetically generated.
**Production alternative**: Real transaction feeds from the firm's order management system.
**Justification**: The prototype demonstrates the report structure and compliance checks. Real transaction data integration requires specific exchange connectivity.

---

## Scope Limitations

### 15. No transaction costs or market impact
**Simplification**: Trades are costless and don't move prices.
**Why acceptable**: Portfolio risk measurement typically ignores transaction costs. They matter for execution and portfolio optimization but not for risk reporting.

### 16. No credit risk modelling beyond RWA
**Simplification**: No probability of default, loss given default, or exposure at default models.
**Why acceptable**: Full credit risk modelling (IRB approach) is a separate system. We cover it conceptually through the Laplace transform aggregate loss model.

### 17. No operational risk
**Simplification**: Basel operational risk requirements are not implemented.
**Why acceptable**: Operational risk uses different methodologies (Basic Indicator, Standardized, or AMA) and is conceptually distinct from market risk.
