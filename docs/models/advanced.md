# Advanced Quantitative Techniques

## 1. Taylor Series (Delta-Gamma) Approximation

### What it is
The delta-gamma approximation uses a second-order Taylor expansion to estimate how a derivative portfolio's value changes when the underlying asset price moves. Delta captures the linear sensitivity, and gamma captures the curvature (convexity).

### Why it matters
For portfolios containing options and other derivatives, a simple linear approximation (delta only) underestimates risk because it ignores convexity. The gamma correction is essential for accurate risk measurement of non-linear instruments. This is how derivative desks compute their daily P&L risk.

### The math

**Taylor expansion of portfolio value V around current price S**:
```
ΔV ≈ δ × ΔS + ½ × γ × (ΔS)²
```

Where:
- ΔV = change in portfolio value
- δ (delta) = ∂V/∂S — first-order price sensitivity
- γ (gamma) = ∂²V/∂S² — second-order price sensitivity (convexity)
- ΔS = change in underlying price

**Delta-only VaR** (linear approximation):
```
VaR_δ = δ × S × σ × z_α
```

**Delta-gamma VaR** (quadratic approximation):
The P&L distribution is no longer normal due to the γ term. We use the **Cornish-Fisher expansion** to adjust for non-normality:

```
z_CF = z_α + (1/6)(z_α² - 1) × γ₁ + (1/24)(z_α³ - 3z_α) × (κ - 3) - (1/36)(2z_α³ - 5z_α) × γ₁²
```

Where γ₁ = skewness and κ = kurtosis of the P&L distribution.

**For a portfolio of derivatives**:
```
Portfolio delta = Σᵢ (position_i × δᵢ)
Portfolio gamma = Σᵢ (position_i × γᵢ)
ΔV_portfolio = Σᵢ [δᵢ × ΔSᵢ + ½ × γᵢ × (ΔSᵢ)²]
```

### Implementation
File: `backend/engine/advanced.py`, function `compute_taylor_series()`
- For each derivative: extract delta and gamma from metadata, compute underlying price changes
- Calculate P&L for each historical day using both delta-only and delta-gamma formulas
- Apply Cornish-Fisher adjustment for portfolio-level VaR
- Compare delta-only vs delta-gamma VaR to show the gamma correction impact

### Interpretation guide
- **Delta-gamma VaR > delta-only VaR**: Gamma is adding risk (typical for long gamma positions in volatile markets)
- **Gamma correction**: The difference shows how much convexity matters — larger corrections mean the linear approximation is less reliable
- **The P&L distribution**: If it shows noticeable skewness, the normal VaR assumption breaks down for this portfolio

### Demo talking points
- "The delta-only approximation treats derivatives as linear instruments, but options have curvature. The gamma term captures this — it's the difference between a straight line and a curve."
- "For our derivative positions, the gamma correction adds roughly X% to the VaR estimate. Ignoring it would systematically understate risk."
- "The Cornish-Fisher expansion adjusts VaR for the non-normality introduced by gamma. This is more accurate than assuming the delta-gamma P&L is normally distributed."

---

## 2. Laplace Transforms / Moment Generating Functions

### What it is
The moment generating function (MGF) approach uses Laplace transforms to derive the distribution of aggregate losses in credit risk. We model total portfolio losses as a compound process: a random number of loss events, each with a random severity.

### Why it matters
Aggregate loss modelling is fundamental to credit risk capital calculations. Insurers and banks need to know the distribution of total losses — not just the expected loss, but how bad the total could get. The MGF approach provides an elegant analytical framework for this.

### The math

**Compound Poisson model**:
- N = number of loss events ~ Poisson(λ)
- Xₖ = severity of k-th event ~ Exponential(μ)
- S = X₁ + X₂ + ... + X_N = aggregate loss

**Moment Generating Function (MGF)**:
```
M_X(t) = E[e^(tX)]
```

For Exponential severity:
```
M_X(t) = 1 / (1 - t × μ)     for t < 1/μ
```

**Compound Poisson MGF**:
```
M_S(t) = exp(λ × (M_X(t) - 1))
       = exp(λ × (1/(1 - tμ) - 1))
```

**Properties from the MGF**:
- E[S] = λ × μ (expected aggregate loss = frequency × mean severity)
- Var(S) = λ × E[X²] = λ × 2μ²

**Numerical approach**: Since inverting the MGF analytically is complex, we use Monte Carlo simulation:
1. Draw N ~ Poisson(λ)
2. Draw X₁, ..., X_N ~ Exponential(μ)
3. Compute S = Σ Xₖ
4. Repeat 10,000 times
5. Extract VaR and ES from the empirical distribution of S

### Implementation
File: `backend/engine/advanced.py`, function `compute_laplace_transforms()`
- λ = 5 (expected 5 loss events per year)
- μ = 1% of portfolio value (mean loss severity)
- 10,000 Monte Carlo simulations of compound Poisson
- VaR and ES at 95% and 99% from simulated aggregate loss distribution
- MGF curve computed analytically for visualization

### Interpretation guide
- **Expected loss = λ × μ**: The average annual aggregate loss. For λ=5 and μ=$100,000: E[S] = $500,000
- **Aggregate VaR 99%**: "In 99% of years, total losses won't exceed this amount"
- **Aggregate ES 99%**: "In the worst 1% of years, average total losses will be this amount"
- **MGF curve**: Shows how the transform behaves — it must diverge at t = 1/μ

### Demo talking points
- "This models total credit losses as a compound Poisson process — we don't know how many loss events will occur or how large each will be."
- "The expected loss is λ × μ = $500,000, but the 99% VaR is significantly higher — the distribution has a long right tail because multiple large losses can compound."
- "The moment generating function provides the theoretical framework. We use Monte Carlo simulation for the practical computation because analytically inverting the MGF is intractable for most severity distributions."

---

## 3. Extreme Value Theory (EVT) / Generalized Pareto Distribution

### What it is
Extreme Value Theory is a branch of statistics specifically designed to model the tails of distributions — the extreme events that matter most for risk management. Rather than fitting a distribution to all returns, EVT focuses only on the extreme observations using the Peaks-Over-Threshold (POT) method and the Generalized Pareto Distribution (GPD).

### Why it matters
Standard distributions (Normal, even Student-t) are calibrated to the entire return distribution, which is dominated by typical observations. But risk managers care about the extremes — the 1% worst days. EVT provides a theoretically grounded framework for modelling exactly these tail events. It's used by regulators, reinsurance companies, and sophisticated risk managers.

### The math

**Peaks-Over-Threshold method**:
1. Choose a threshold u (typically the 90th percentile of losses)
2. Extract exceedances: yᵢ = xᵢ - u for all xᵢ > u
3. Fit GPD to the exceedances

**Generalized Pareto Distribution**:
```
F(y) = 1 - (1 + ξy/β)^(-1/ξ)     for y > 0
```

Parameters:
- ξ (xi) = **shape parameter** — controls tail heaviness
  - ξ > 0: heavy tails (Pareto-like, infinite higher moments)
  - ξ = 0: exponential tails (light tails, reduces to exponential distribution)
  - ξ < 0: bounded tails (finite endpoint at -β/ξ)
- β (beta) = **scale parameter** — controls spread

For financial losses, ξ typically falls between 0 and 0.5, indicating moderately heavy tails.

**Tail VaR using GPD**:
```
VaR_α = u + (β/ξ) × [(n/(N_u × (1-α)))^ξ - 1]
```
Where:
- u = threshold
- n = total number of observations
- N_u = number of exceedances above u
- α = confidence level

**Tail Expected Shortfall**:
```
ES_α = VaR_α / (1-ξ) + (β - ξ×u) / (1-ξ)
```
(valid for ξ < 1)

**Comparison with normal assumption**:
```
Normal VaR_α = μ + z_α × σ
Normal ES_α = μ + σ × φ(z_α) / (1-α)
```
where φ is the standard normal PDF.

GPD typically gives HIGHER VaR and ES than the normal assumption because it correctly captures the fat tails that the normal distribution misses.

### Implementation
File: `backend/engine/advanced.py`, function `compute_evt_gpd()`
- Threshold at 90th percentile of losses (negative returns)
- GPD fitted via `scipy.stats.genpareto.fit()`
- Tail VaR and ES computed using GPD formulas
- Normal-assumption VaR/ES computed for comparison
- QQ plot data generated for visual tail fit assessment

### Interpretation guide
- **ξ ≈ 0.1-0.3**: Moderately heavy tails (typical for equity portfolios)
- **ξ > 0.5**: Very heavy tails — extreme caution, rare events will be very large
- **ξ < 0**: Bounded tail — unusual for financial returns
- **GPD VaR > Normal VaR**: Confirms that the normal assumption underestimates tail risk
- **QQ plot**: Points above the diagonal indicate fatter tails than the fitted reference

### Demo talking points
- "EVT is purpose-built for modelling extremes. Instead of fitting the entire distribution and hoping the tails are right, we focus exclusively on the observations that matter most — the extreme losses."
- "Our GPD fit shows ξ ≈ 0.15, indicating moderately heavy tails. The EVT-based VaR at 99% is roughly 30% higher than the normal-assumption VaR — that's the risk the normal distribution misses."
- "This is why sophisticated risk managers and regulators favour EVT for tail risk: it provides a theoretically rigorous framework that doesn't assume the tails look like a bell curve."
- "The Peaks-Over-Threshold method is like studying flood risk by looking only at water levels above the dam height — you don't need to model the entire river flow, just the extremes."
