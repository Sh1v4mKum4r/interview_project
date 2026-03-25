# Value-at-Risk and Expected Shortfall: Mathematical Documentation

> **Audience:** Candidates performing a live demo walkthrough of the risk analysis system.
> **Code reference:** All formulas map to `backend/engine/risk.py`.
> **Prerequisite:** Basic statistics (mean, standard deviation, percentiles). Everything else is derived below.

---

## Table of Contents

1. [Historical VaR](#1-historical-var)
2. [Parametric VaR -- Normal](#2-parametric-var--normal)
3. [Parametric VaR -- Student-t](#3-parametric-var--student-t)
4. [Monte Carlo VaR](#4-monte-carlo-var)
5. [Expected Shortfall (CVaR)](#5-expected-shortfall-cvar)
6. [Model Comparison](#6-model-comparison)

---

## Notation Reference

| Symbol | Meaning |
|--------|---------|
| R | Vector of historical portfolio returns (daily log-returns or simple returns) |
| R_t | Return on day t |
| alpha | Confidence level (e.g., 0.95 or 0.99) |
| mu | Mean (expected value) of the return distribution |
| sigma | Standard deviation of the return distribution |
| z_alpha | Standard normal quantile at probability alpha |
| t_alpha(df) | Student-t quantile at probability alpha with df degrees of freedom |
| T | Time horizon in trading days |
| Sigma | Covariance matrix of asset returns |
| L | Lower-triangular Cholesky factor of Sigma |
| w | Vector of portfolio weights |
| V | Portfolio notional value (in dollars) |

---

## 1. Historical VaR

### What It Is

Historical VaR is the simplest and most intuitive approach to measuring market risk. You take the actual daily returns your portfolio experienced, sort them from worst to best, and read off the loss at a chosen percentile. There is no assumption about what distribution the returns follow -- you let the data speak for itself. If you had 252 trading days and want the 95th-percentile worst-case, you literally find the 13th worst day (since 5% of 252 is 12.6, rounded up to 13).

### Why It Matters

Historical VaR has been the industry workhorse since the 1990s when JPMorgan published the original RiskMetrics framework. Regulators under Basel II required banks to compute VaR at the 99% confidence level over a 10-day holding period for market risk capital. Even though Basel III FRTB has shifted the primary metric to Expected Shortfall, Historical VaR remains a benchmark that every risk report includes. It is easy to explain to non-quantitative stakeholders: "Based on the last year of actual market data, we would not expect to lose more than $X on 19 out of 20 days."

### The Math

**Step 1: Compute portfolio returns.**

Given asset returns R_i,t for asset i on day t, and portfolio weights w_i, the portfolio return on day t is:

```
R_p,t = sum_i ( w_i * R_i,t )
```

In vector notation:

```
R_p,t = w^T * R_t
```

**Step 2: Sort the returns.**

Arrange the n observed portfolio returns in ascending order:

```
R_(1) <= R_(2) <= ... <= R_(n)
```

where R_(k) denotes the k-th order statistic (the k-th smallest value).

**Step 3: Pick the percentile.**

For confidence level alpha (e.g., 0.95), VaR is the (1 - alpha) quantile of the return distribution. With n observations:

```
VaR_alpha = -Percentile(R_p, (1 - alpha) * 100)
```

More precisely, find index k = floor((1 - alpha) * n). Then:

```
VaR_alpha = -R_(k)
```

The negative sign converts a negative return (a loss) into a positive VaR number. Convention: VaR is reported as a positive number representing the magnitude of loss.

**Concrete example at 95% confidence with 252 days:**

```
k = floor(0.05 * 252) = floor(12.6) = 12
```

So VaR is the negative of the 12th-to-13th worst daily return (numpy's `percentile` interpolates between adjacent order statistics).

**Step 4: Scale to the desired time horizon.**

The square-root-of-time rule scales a 1-day VaR to a T-day VaR. This relies on the assumption that returns are independently and identically distributed (i.i.d.):

```
VaR_T = VaR_1D * sqrt(T)
```

For a 10-day holding period: `VaR_10D = VaR_1D * sqrt(10) = VaR_1D * 3.162`

**Step 5: Convert to dollar terms.**

```
VaR_$ = VaR_T * V
```

where V is the portfolio notional value.

### Implementation

In `backend/engine/risk.py`, the function `compute_historical_var` implements this model.

**Portfolio return computation** (lines 96-97):
```python
port_ret = _portfolio_returns(returns, weights)
sorted_returns = np.sort(port_ret.values)
```
The helper `_portfolio_returns` computes `returns[assets].dot(w)`, which is the vector dot product `w^T * R_t` for each day t.

**VaR calculation** (lines 100-101):
```python
alpha = 1 - confidence_level
var_pct = np.percentile(sorted_returns, alpha * 100)
```
`np.percentile(data, 5)` returns the 5th percentile of the sorted data, which is the (1 - 0.95) quantile. This value is a negative number (representing a loss).

**Time scaling** (lines 108):
```python
var_scaled = var_pct * scale
```
where `scale = np.sqrt(_get_horizon_days(time_horizon))`. For "10D", scale = sqrt(10) = 3.162.

**Dollar conversion** (line 112):
```python
var_dollar = abs(var_scaled) * portfolio_value
```
`abs()` makes the dollar amount positive.

**Per-asset breakdown** (lines 116-128): The same procedure is repeated for each individual asset's return series, allowing the demo to show which asset contributes the most risk.

### Interpretation Guide

| Output Field | What It Means |
|---|---|
| `portfolio_var` | The VaR as a decimal return (negative). E.g., -0.023 means "the portfolio could lose 2.3% or more on a bad day." |
| `var_dollar` | The dollar-equivalent loss. E.g., with V = $10M and VaR = -0.023, `var_dollar` = $230,000. |
| `portfolio_es` | Expected Shortfall (see Section 5). The average loss *given that* VaR is breached. Always larger than VaR in magnitude. |
| `es_dollar` | Dollar-equivalent of ES. |
| `per_asset` | Shows individual asset VaR/ES so you can identify which position drives the most risk. |
| `sorted_returns` | The full sorted return series. The histogram visualizes this. The VaR line marks the cutoff point on the left tail. |

**Key signal:** If `portfolio_var` at 95% confidence is, say, -0.018 and at 99% it jumps to -0.032, the tail is getting heavier quickly. That gap tells you the distribution has fat tails.

### Demo Talking Points

- "Historical VaR makes zero distributional assumptions -- it uses only what actually happened. The trade-off is that it can only capture risks that are present in the historical window. If your window doesn't include a crash, VaR won't reflect crash risk."
- "At 95% confidence with one year of data (252 days), we are looking at roughly the 13th worst trading day. The system sorts all daily returns and reads that value directly."
- "The square-root-of-time scaling from 1-day to 10-day VaR assumes returns are independent. In reality, volatility clusters (bad days tend to follow bad days), so the 10-day number may understate risk during stressed periods."
- "Look at the per-asset breakdown to see which position is the biggest risk contributor. This drives the conversation about rebalancing or hedging."

---

## 2. Parametric VaR -- Normal

### What It Is

Parametric VaR assumes that portfolio returns follow a known probability distribution -- in this case, the Normal (Gaussian) distribution. Instead of sorting historical returns, you estimate just two parameters -- the mean and the standard deviation -- and then use the analytical formula for the Normal quantile. This gives you a closed-form answer that is extremely fast to compute and easy to decompose across risk factors. The price you pay is the assumption: real financial returns have fatter tails and more extreme events than the Normal distribution predicts.

### Why It Matters

The original JPMorgan RiskMetrics system (1994) was essentially parametric Normal VaR with exponentially-weighted moving average (EWMA) volatility. Most banks' internal models started here. Regulators accepted it for Basel I market risk amendments. The Normal assumption makes portfolio-level VaR decomposition elegant -- since the sum of Normal random variables is Normal, you can analytically compute the marginal contribution of each asset. However, the 2008 financial crisis starkly demonstrated that extreme losses occur far more often than the Normal distribution predicts, which is one reason regulators pushed for Expected Shortfall and fat-tailed models.

### The Math

**Step 1: Estimate parameters from data.**

Given n observations of portfolio returns R_p,1, R_p,2, ..., R_p,n:

```
mu = (1/n) * sum_{t=1}^{n} R_p,t

sigma = sqrt( (1/(n-1)) * sum_{t=1}^{n} (R_p,t - mu)^2 )
```

These are the sample mean and sample standard deviation.

**Step 2: Assume R_p ~ N(mu, sigma^2).**

The probability density function (PDF) of the Normal distribution is:

```
f(x) = (1 / (sigma * sqrt(2 * pi))) * exp( -(x - mu)^2 / (2 * sigma^2) )
```

The cumulative distribution function (CDF) is:

```
F(x) = P(R_p <= x) = integral from -infinity to x of f(u) du
```

**Step 3: Find the VaR quantile.**

VaR at confidence level alpha is the value x such that:

```
P(R_p <= -VaR_alpha) = 1 - alpha
```

Using the standard Normal variable Z = (R_p - mu) / sigma:

```
P(Z <= z_alpha) = 1 - alpha
```

where z_alpha = Phi^{-1}(1 - alpha) is the inverse CDF (quantile function) of the standard Normal evaluated at (1 - alpha).

Key z-values:
```
z_{0.95} = Phi^{-1}(0.05) = -1.645
z_{0.99} = Phi^{-1}(0.01) = -2.326
```

The VaR in return terms (a negative number representing the loss threshold):

```
VaR_alpha (return) = mu + z_alpha * sigma
```

Since z_alpha is negative, this gives a value in the left tail. As a positive loss:

```
VaR_alpha = -(mu + z_alpha * sigma)
```

**Worked example:** Suppose mu = 0.0003 (daily), sigma = 0.012, alpha = 0.95:

```
VaR_0.95 = -(0.0003 + (-1.645) * 0.012)
         = -(0.0003 - 0.01974)
         = -(-0.01944)
         = 0.01944   (i.e., 1.944% daily loss)
```

**Step 4: Scale to the desired horizon.**

```
VaR_T = VaR_1D * sqrt(T)
```

Same square-root-of-time rule as Historical VaR.

**Step 5: Expected Shortfall under the Normal distribution.**

There is a closed-form expression for ES under normality:

```
ES_alpha = -(mu - sigma * phi(z_alpha) / (1 - alpha))
```

where phi(z) is the standard Normal PDF:

```
phi(z) = (1 / sqrt(2 * pi)) * exp(-z^2 / 2)
```

Derivation: ES is the conditional expectation of loss given that the loss exceeds VaR:

```
ES_alpha = -E[R_p | R_p <= quantile_{1-alpha}]
         = -(mu - sigma * phi(Phi^{-1}(1 - alpha)) / (1 - alpha))
```

This follows from the truncated Normal mean formula. For alpha = 0.95:

```
phi(-1.645) = 0.1031
ES_0.95 = -(mu - sigma * 0.1031 / 0.05)
        = -(mu - sigma * 2.063)
```

Note that the ES multiplier (2.063) is larger than the VaR multiplier (1.645), confirming that ES always exceeds VaR.

### Implementation

In `backend/engine/risk.py`, the function `compute_parametric_var` implements both Normal and Student-t variants. The Normal-specific portion:

**Parameter estimation** (lines 170-171):
```python
mu = port_ret.mean()
sigma = port_ret.std()
```
pandas `.std()` uses n-1 denominator (Bessel's correction) by default.

**Normal VaR** (lines 174-175):
```python
z_alpha = stats.norm.ppf(alpha)    # alpha = 1 - confidence_level = 0.05
normal_var = mu + z_alpha * sigma   # negative number
```
`stats.norm.ppf(0.05)` returns -1.6449, which is z_{0.95}.

**Normal ES** (line 177):
```python
normal_es = mu - sigma * stats.norm.pdf(z_alpha) / alpha
```
This is the closed-form `mu - sigma * phi(z_alpha) / (1 - confidence_level)`. Note that in the code, `alpha` is already `1 - confidence_level`, so this matches the formula exactly.

**Per-asset decomposition** (lines 198-209): For each asset individually, compute VaR and ES using the same Normal formulas but with that asset's own mu and sigma.

### Interpretation Guide

| Output Field | What It Means |
|---|---|
| `normal_var` | Parametric Normal VaR, scaled to the chosen horizon. Compare this against `portfolio_var` from Historical VaR. If Historical VaR is significantly larger, returns have fatter tails than Normal. |
| `normal_es` | Parametric Normal ES. Under normality, ES is about 25% larger than VaR at 95% confidence (multiplier ratio: 2.063 / 1.645 = 1.25). |
| `portfolio_var` | In the parametric output, this defaults to the Normal VaR value. |
| `per_asset` | Per-asset Normal VaR/ES. Useful for marginal risk contribution analysis. |

**Key signal:** If the Historical VaR is, say, -0.025 but Normal VaR is -0.020, the returns have heavier tails than Normal. The 0.005 gap represents tail risk that the Normal model misses.

### Demo Talking Points

- "Parametric Normal VaR boils the entire return distribution down to two numbers: the mean and the standard deviation. The formula `VaR = -(mu + z * sigma)` is a closed-form answer -- no simulation needed."
- "The z-value of -1.645 for 95% confidence comes from the inverse Normal CDF. This is the same z-score from introductory statistics courses, applied directly to financial risk."
- "The weakness is the normality assumption. Real financial returns exhibit excess kurtosis -- meaning extreme events happen more often than a bell curve predicts. If you look at the histogram of actual returns versus the fitted Normal overlay, you will see the actual tails are fatter."
- "Compare the Normal VaR to the Historical VaR. The difference quantifies how much tail risk the Normal model ignores."

---

## 3. Parametric VaR -- Student-t

### What It Is

The Student-t distribution is a bell-shaped distribution like the Normal, but with heavier tails controlled by a parameter called degrees of freedom (df). When df is small (e.g., 3-5), the tails are very heavy -- extreme returns are much more likely than under the Normal. As df approaches infinity, the Student-t converges to the Normal. For typical equity returns, fitted df values range from 3 to 8, confirming that financial data consistently has fatter tails than Normal. This makes the Student-t a more realistic model for financial returns while retaining the analytical tractability of a parametric approach.

### Why It Matters

The excess kurtosis of financial returns is one of the most well-documented "stylized facts" of quantitative finance (Mandelbrot 1963, Fama 1965). The Normal distribution has a kurtosis of exactly 3. Financial returns typically exhibit kurtosis of 4 to 10 or higher. The Student-t distribution with df degrees of freedom has kurtosis = 3 + 6/(df - 4) for df > 4, so a df of 5 gives kurtosis = 9 -- much closer to reality. This matters for risk management because underestimating tail risk means underestimating the probability and magnitude of extreme losses. Basel III's shift from VaR to Expected Shortfall was partly motivated by the desire to better capture tail behavior.

### The Math

**Step 1: The Student-t distribution.**

The PDF of the standardized Student-t with df degrees of freedom (often denoted nu) is:

```
f(x; nu) = ( Gamma((nu + 1)/2) ) / ( sqrt(nu * pi) * Gamma(nu/2) ) * (1 + x^2/nu)^(-(nu+1)/2)
```

where Gamma is the gamma function.

For a location-scale Student-t with parameters (loc, scale, df):

```
f(x; nu, loc, scale) = (1/scale) * f_standard((x - loc)/scale; nu)
```

This distribution has:
- Mean = loc (for df > 1)
- Variance = scale^2 * df / (df - 2) (for df > 2)
- Kurtosis = 3 + 6 / (df - 4) (for df > 4)

**Step 2: Fit the distribution to data.**

Given portfolio returns R_p,1, ..., R_p,n, use maximum likelihood estimation (MLE) to find the three parameters (df, loc, scale) that best fit the data.

The log-likelihood function is:

```
log L(nu, loc, scale) = sum_{t=1}^{n} log f(R_p,t; nu, loc, scale)
```

MLE finds the (nu, loc, scale) that maximizes this. In practice, `scipy.stats.t.fit()` performs this optimization numerically using the L-BFGS-B algorithm.

**Step 3: Compute VaR.**

The VaR is the (1 - alpha) quantile of the fitted distribution:

```
VaR_alpha (return) = loc + t_{1-alpha}(df) * scale
```

where t_{1-alpha}(df) is the (1 - alpha) quantile of the standardized Student-t with df degrees of freedom. This is computed via the inverse CDF (percent point function):

```
t_{0.05}(df=5) = -2.015    (compare to z_{0.05} = -1.645 for Normal)
t_{0.01}(df=5) = -3.365    (compare to z_{0.01} = -2.326 for Normal)
```

Notice that the Student-t quantiles are more extreme than the Normal quantiles, especially far in the tail. This is exactly how the model captures higher tail risk.

As a positive loss:

```
VaR_alpha = -(loc + t_{1-alpha}(df) * scale)
```

**Step 4: Expected Shortfall under the Student-t.**

The closed-form ES for a standardized Student-t is:

```
ES_{standard}(alpha) = -( f_t(t_alpha; df) / (1 - alpha) ) * ( (df + t_alpha^2) / (df - 1) )
```

where f_t is the standardized Student-t PDF and t_alpha = t_{1-alpha}(df) is the standardized quantile.

For the location-scale version:

```
ES_alpha = -(loc + scale * ES_{standard}(alpha))
```

Or equivalently (as implemented in the code):

```
ES_alpha = -(loc + scale * ( -f_t(t_alpha; df) / (1 - alpha) * (df + t_alpha^2) / (df - 1) ))
```

**Step 5: Time scaling.**

Same square-root-of-time rule:

```
VaR_T = VaR_1D * sqrt(T)
```

Note: This scaling is approximate for the Student-t. The sum of t-distributed variables is not exactly t-distributed, but the approximation is standard practice.

### Implementation

In `backend/engine/risk.py`, the Student-t variant lives within `compute_parametric_var`.

**Fitting the distribution** (line 180):
```python
df, t_loc, t_scale = stats.t.fit(port_ret.values)
```
`scipy.stats.t.fit()` performs MLE, returning (degrees of freedom, location, scale).

**Student-t VaR** (line 181):
```python
t_var = stats.t.ppf(alpha, df, loc=t_loc, scale=t_scale)
```
`ppf` is the percent point function (inverse CDF). With alpha = 0.05, this returns the 5th percentile of the fitted t-distribution.

**Student-t ES** (lines 183-186):
```python
t_quantile = stats.t.ppf(alpha, df)                 # standardized quantile
t_es = t_loc + t_scale * (
    -stats.t.pdf(t_quantile, df) / alpha * (df + t_quantile ** 2) / (df - 1)
)
```
This matches the closed-form formula above. `stats.t.pdf(t_quantile, df)` evaluates the standardized Student-t PDF at the quantile.

**Output fields** (lines 219-223):
```python
"t_var": float(t_var_scaled),
"t_es": float(t_es_scaled),
"t_df": float(df),
```
The fitted `t_df` is reported in the output so the user can see how heavy the tails are.

### Interpretation Guide

| Output Field | What It Means |
|---|---|
| `t_var` | Student-t VaR, scaled to the chosen horizon. Should be larger in magnitude than `normal_var` because heavier tails push the quantile outward. |
| `t_es` | Student-t ES. The gap between `t_es` and `t_var` is wider than the gap between `normal_es` and `normal_var`, reflecting the heavier tail. |
| `t_df` | Fitted degrees of freedom. **This is the single most informative number.** df < 5: very heavy tails, extreme events are common. df = 5-10: moderate fat tails (typical for equities). df > 30: tails are nearly Normal. |

**Key signal:** If `t_df` is around 4, the kurtosis is 3 + 6/(4-4) = undefined (actually infinite theoretical kurtosis for df <= 4), meaning the tails are extremely heavy and even the Student-t ES may understate risk. If `t_df` is 8, kurtosis = 3 + 6/4 = 4.5, which is fairly typical for a diversified equity portfolio.

### Demo Talking Points

- "The Student-t distribution adds one parameter -- degrees of freedom -- that controls how fat the tails are. The system fits this from the data using maximum likelihood estimation. A low df value means the portfolio has experienced more extreme moves than a Normal distribution would predict."
- "Compare `t_var` to `normal_var`. The difference is entirely due to the heavier tails. For a typical df of 5, the 99% Student-t VaR can be 40-50% larger than Normal VaR -- a massive difference in capital requirements."
- "The `t_df` value in the output is a quick diagnostic. Below 5, you have very heavy tails and should pay close attention to the tail risk measures. Above 10, the Normal approximation is reasonably close."
- "Financial regulators moved toward Expected Shortfall partly because VaR does not 'see' what happens beyond the threshold. ES averages the entire tail, and under the Student-t, that tail average is far worse than under the Normal."

---

## 4. Monte Carlo VaR

### What It Is

Monte Carlo VaR uses computer simulation to generate thousands of hypothetical portfolio returns, then extracts VaR and ES from the simulated distribution. The process works in three stages: (1) estimate the statistical properties of each asset's returns and their correlations, (2) use the Cholesky decomposition of the covariance matrix to generate correlated random returns that respect those statistical relationships, and (3) compute the portfolio return for each simulation, sort the results, and read off the percentile. This is the most flexible approach: it can handle non-linear instruments (options, structured products), complex portfolio structures, and non-Normal distributions, though the implementation here uses a multivariate Normal assumption for the simulation step.

### Why It Matters

Monte Carlo simulation is the most general-purpose risk engine in quantitative finance. While Historical and Parametric VaR have analytical shortcuts, Monte Carlo can model virtually any payoff structure. Banks use it for portfolios containing options (where risk is non-linear), path-dependent instruments (barrier options, Asian options), and complex multi-asset derivatives. The Basel Committee allows Monte Carlo models for internal model approval (IMA) under both Basel II.5 and Basel III. The trade-off is computational cost: you need thousands of simulations for stable results, and tens of thousands for accurate tail estimates. The implementation uses 10,000 simulations with a fixed random seed for reproducibility.

### The Math

**Step 1: Estimate the mean vector and covariance matrix.**

For n assets, compute:

Mean vector (n x 1):
```
mu = [mu_1, mu_2, ..., mu_n]^T
```
where `mu_i = (1/T) * sum_{t=1}^{T} R_i,t` is the sample mean of asset i's returns.

Covariance matrix (n x n):
```
Sigma = Cov(R) where Sigma_ij = (1/(T-1)) * sum_{t=1}^{T} (R_i,t - mu_i)(R_j,t - mu_j)
```

The covariance matrix is symmetric and positive semi-definite. The diagonal entries are variances; the off-diagonal entries capture how assets co-move.

**Step 2: Cholesky decomposition.**

To generate correlated random vectors, we decompose the covariance matrix:

```
Sigma = L * L^T
```

where L is a lower-triangular matrix. This factorization exists and is unique for any positive-definite matrix.

For a 2x2 example:
```
Sigma = | sigma_1^2        rho*sigma_1*sigma_2 |
        | rho*sigma_1*sigma_2   sigma_2^2       |

L = | sigma_1                   0          |
    | rho*sigma_2    sigma_2*sqrt(1-rho^2) |
```

You can verify that L * L^T = Sigma.

**Step 3: Generate correlated random returns.**

Draw N independent standard Normal random vectors:

```
z_k ~ N(0, I_n)    for k = 1, 2, ..., N
```

where each z_k is an n-dimensional vector with independent N(0,1) components, and I_n is the n x n identity matrix.

Transform to correlated returns:

```
r_k = mu + L * z_k
```

**Why this works:** The covariance of the simulated returns is:

```
Cov(r_k) = Cov(mu + L * z_k)
          = L * Cov(z_k) * L^T
          = L * I * L^T
          = L * L^T
          = Sigma
```

So the simulated returns have exactly the same covariance structure as the historical data.

**Step 4: Compute portfolio returns for each simulation.**

```
R_p,k = w^T * r_k    for k = 1, ..., N
```

This gives N simulated portfolio returns.

**Step 5: Extract VaR and ES.**

Sort the N simulated portfolio returns and apply the same percentile logic as Historical VaR:

```
VaR_alpha = -Percentile(R_p,1, ..., R_p,N; (1 - alpha) * 100)
```

For ES, average all simulated returns that fall at or below the VaR threshold:

```
ES_alpha = -Mean(R_p,k | R_p,k <= -VaR_alpha)
```

With N = 10,000 simulations at alpha = 0.95, you are averaging the worst 500 simulated outcomes.

**Step 6: Scale and convert to dollars.**

```
VaR_T = VaR_1D * sqrt(T)
VaR_$ = VaR_T * V
```

### Implementation

In `backend/engine/risk.py`, the function `compute_monte_carlo_var` implements this model.

**Asset alignment** (lines 262-264):
```python
assets = [a for a in weights if a in returns.columns]
w = np.array([weights[a] for a in assets])
ret_matrix = returns[assets]
```
This ensures the weight vector and return matrix are ordered consistently.

**Mean and covariance** (lines 266-267):
```python
mu = ret_matrix.mean().values     # shape: (n_assets,)
cov = ret_matrix.cov().values     # shape: (n_assets, n_assets)
```

**Cholesky decomposition** (line 270):
```python
L = np.linalg.cholesky(cov)
```
numpy's `cholesky` returns the lower-triangular factor L such that `cov = L @ L.T`.

**Generate simulations** (lines 273-275):
```python
rng = np.random.RandomState(42)
z = rng.standard_normal((num_simulations, len(assets)))   # shape: (10000, n_assets)
simulated_asset_returns = mu + z @ L.T                     # shape: (10000, n_assets)
```
Note the transpose `L.T`: since z has shape (N, n), and L has shape (n, n), the operation `z @ L.T` gives shape (N, n). Each row is one simulated scenario. The formula is `r = mu + z * L^T`, which is equivalent to `r = mu + L * z` when operating on column vectors, because `(L * z)^T = z^T * L^T`.

**Portfolio returns** (line 278):
```python
simulated_port_returns = simulated_asset_returns @ w    # shape: (10000,)
```
This is `w^T * r_k` for each simulation k.

**VaR and ES extraction** (lines 281-283):
```python
var_pct = np.percentile(simulated_port_returns, alpha * 100)
tail = simulated_port_returns[simulated_port_returns <= var_pct]
es_pct = tail.mean() if len(tail) > 0 else var_pct
```

**Reproducibility** (line 273): The seed `RandomState(42)` ensures that every run produces identical simulation results. This is critical for demo reproducibility and for regression testing.

### Interpretation Guide

| Output Field | What It Means |
|---|---|
| `portfolio_var` | Monte Carlo VaR, scaled to the chosen horizon. Based on 10,000 simulated scenarios. |
| `portfolio_es` | Monte Carlo ES, the average of the worst (1-alpha)*10,000 simulated outcomes. |
| `var_dollar` / `es_dollar` | Dollar equivalents. |
| `num_simulations` | Always 10,000 in this implementation. More simulations give more stable estimates, but with diminishing returns. The standard error of the VaR estimate decreases as 1/sqrt(N). |
| `simulated_returns` | The first 1,000 entries of the sorted simulated returns (truncated for performance). The histogram shows the full distribution. |

**Key signal:** If Monte Carlo VaR is close to Parametric Normal VaR, the Normal assumption is holding well (expected, since the simulation draws from a multivariate Normal). If Monte Carlo VaR is significantly different from Historical VaR, the historical period may have been unusually calm or volatile relative to the fitted distribution.

### Demo Talking Points

- "Monte Carlo VaR generates 10,000 hypothetical portfolio returns using the Cholesky decomposition to preserve the correlation structure between assets. This is the same technique used in production risk systems at major banks."
- "The Cholesky decomposition is the key mathematical operation. It factors the covariance matrix into L times L-transpose, giving us a 'square root' of the covariance that lets us transform independent random numbers into correlated ones."
- "With 10,000 simulations, our VaR estimate is statistically stable. At 95% confidence, we're averaging the worst 500 outcomes. The seed is fixed at 42 for demo reproducibility."
- "In production systems, Monte Carlo is essential for portfolios with options and other non-linear instruments. Here we are simulating linear returns, but the same framework extends to pricing any derivative payoff across thousands of scenarios."

---

## 5. Expected Shortfall (CVaR)

### What It Is

Expected Shortfall (ES), also called Conditional Value-at-Risk (CVaR), answers the question: "If we have a really bad day -- one that exceeds our VaR threshold -- how bad is it on average?" VaR tells you the boundary of the worst 5% (or 1%) of outcomes. ES tells you the average loss within that worst-case region. This makes ES a strictly more informative measure: it tells you about the severity of tail events, not just their threshold. Mathematically, ES is always greater than or equal to VaR in magnitude.

### Why It Matters

The Basel Committee's Fundamental Review of the Trading Book (FRTB), finalized in January 2016 and effective from January 2023, replaced VaR with ES as the primary market risk measure for calculating capital requirements. The shift from 99% VaR to 97.5% ES was motivated by three key problems with VaR:

1. **VaR ignores tail severity.** Two portfolios can have the same VaR but vastly different tail losses. ES captures this.
2. **VaR is not subadditive.** Diversification should reduce risk, but VaR can paradoxically increase when portfolios are combined. ES always satisfies subadditivity (see below).
3. **VaR incentivizes hiding risk.** A trader can construct positions that have low VaR but catastrophic tail losses. ES penalizes this.

Under FRTB, the capital charge is based on ES at the 97.5% confidence level (2.5% tail), scaled across multiple liquidity horizons.

### The Math

**Definition:**

```
ES_alpha = -E[R_p | R_p <= -VaR_alpha]
```

In words: the negative of the expected return, conditional on the return being in the worst (1 - alpha) fraction of outcomes.

Equivalently, using the loss variable L = -R_p:

```
ES_alpha = E[L | L >= VaR_alpha]
```

This is the average loss, given that the loss exceeds VaR.

**Continuous formulation:**

If f(x) is the PDF and F(x) is the CDF of the return distribution:

```
ES_alpha = -(1 / (1 - alpha)) * integral from -infinity to F^{-1}(1 - alpha) of x * f(x) dx
```

**Discrete formulation (used in Historical and Monte Carlo):**

Given n sorted returns R_(1) <= R_(2) <= ... <= R_(n):

```
k = floor((1 - alpha) * n)

ES_alpha = -(1/k) * sum_{i=1}^{k} R_(i)
```

This is simply the average of the k worst returns.

**Closed-form under Normal distribution:**

```
ES_alpha = -(mu - sigma * phi(z_alpha) / (1 - alpha))
```

where phi is the standard Normal PDF and z_alpha = Phi^{-1}(1 - alpha). (Derived in Section 2.)

**Closed-form under Student-t distribution:**

```
ES_alpha = -(loc + scale * ( -f_t(t_alpha; df) / (1 - alpha) * (df + t_alpha^2) / (df - 1) ))
```

(Derived in Section 3.)

**Subadditivity property:**

For any two portfolios A and B:

```
ES(A + B) <= ES(A) + ES(B)
```

This means that diversification always reduces (or at worst, maintains) the ES of a combined portfolio. VaR does not have this property in general. A risk measure that satisfies subadditivity (along with monotonicity, positive homogeneity, and translation invariance) is called a "coherent risk measure" in the Artzner et al. (1999) framework. ES is coherent; VaR is not.

**Why this matters practically:** Suppose a trading desk has two books, each with VaR of $5M. A risk manager combining them might find the combined VaR is $11M -- more than the sum. This violates the intuition that diversification should help. With ES, the combined ES is always <= $10M (the sum of the individual ES values). This makes capital allocation and risk budgeting mathematically consistent.

**FRTB calibration:**

Under FRTB, the relationship between 99% VaR and 97.5% ES was calibrated so that for a Normal distribution:

```
ES_{97.5%} (Normal) = 2.338 * sigma
VaR_{99%} (Normal)  = 2.326 * sigma
```

These are approximately equal for Normal returns, ensuring backward compatibility. However, for fat-tailed distributions, ES_{97.5%} is substantially larger than VaR_{99%}, which is exactly the point: ES captures the additional tail risk.

### Implementation

ES is computed alongside VaR in every function in `backend/engine/risk.py`. The pattern is the same across all three methods.

**Historical ES** (lines 104-105 in `compute_historical_var`):
```python
tail = sorted_returns[sorted_returns <= var_pct]
es_pct = tail.mean() if len(tail) > 0 else var_pct
```
Boolean indexing selects all returns at or below the VaR threshold, then averages them.

**Parametric Normal ES** (line 177):
```python
normal_es = mu - sigma * stats.norm.pdf(z_alpha) / alpha
```

**Parametric Student-t ES** (lines 183-186):
```python
t_quantile = stats.t.ppf(alpha, df)
t_es = t_loc + t_scale * (
    -stats.t.pdf(t_quantile, df) / alpha * (df + t_quantile ** 2) / (df - 1)
)
```

**Monte Carlo ES** (lines 282-283):
```python
tail = simulated_port_returns[simulated_port_returns <= var_pct]
es_pct = tail.mean() if len(tail) > 0 else var_pct
```

**FRTB ES** (lines 258-264 in `backend/engine/regulatory.py`): The regulatory module computes ES at 97.5% confidence (2.5% tail) specifically for FRTB capital calculation:
```python
es_quantile = 0.025
threshold = np.percentile(portfolio_returns, es_quantile * 100)
tail = portfolio_returns[portfolio_returns <= threshold]
frtb_es = abs(tail.mean()) * portfolio_value
```

### Interpretation Guide

| Output Field | What It Means |
|---|---|
| `portfolio_es` | Expected Shortfall as a decimal return (negative). Always larger in magnitude than `portfolio_var`. |
| `es_dollar` | Dollar loss. "On average, when we breach VaR, the loss is this amount." |
| `es_line` | Plotted on the histogram, this line sits to the left of the VaR line, deeper in the tail. The area between these two lines and the left edge of the histogram represents the tail region that ES averages. |

**Key signal:** The ratio ES/VaR reveals the shape of the tail. Under the Normal distribution at 95% confidence, ES/VaR is approximately 1.25. If your data shows ES/VaR = 1.5 or higher, the tail is heavier than Normal -- meaning extreme losses are not just more likely but also more severe than a bell curve predicts.

### Demo Talking Points

- "Expected Shortfall answers the question VaR leaves open: 'When things go bad, how bad do they get?' VaR gives you the threshold; ES gives you the average severity beyond that threshold."
- "Basel III FRTB replaced 99% VaR with 97.5% ES as the primary market risk measure starting in 2023. The shift was motivated by the 2008 crisis, where portfolios with similar VaR experienced vastly different tail losses."
- "ES is a coherent risk measure, meaning it always respects diversification. If you combine two portfolios, the combined ES is never worse than the sum of the individual ES values. VaR does not guarantee this, which can lead to perverse incentives in capital allocation."
- "Look at the ES/VaR ratio in the output. Under Normal assumptions, it is about 1.25 at 95% confidence. If the historical data shows a ratio of 1.5 or higher, the tail is fat and the Normal model is materially underestimating risk."

---

## 6. Model Comparison

### Why the Three VaR Numbers Differ

When you run `compute_var_summary` (lines 313-373 of `backend/engine/risk.py`), the system computes all four VaR estimates side by side: Historical, Parametric Normal, Parametric Student-t, and Monte Carlo. These will almost never agree exactly, and the differences are informative.

**Historical vs. Parametric Normal:**

Historical VaR makes no distributional assumption; it uses whatever the data contains. Parametric Normal forces the data into a bell curve. If historical returns have fat tails (as financial data usually does), Historical VaR will be larger in magnitude than Normal VaR because the actual 5th percentile is further out than the Normal model predicts. If the historical window was unusually calm, Historical VaR could be *smaller* than Normal VaR.

**Parametric Normal vs. Student-t:**

The Student-t has heavier tails than the Normal by construction (when df < infinity). At the 95% level, the difference is moderate. At the 99% level, the gap widens significantly because the very far tail of the Student-t distribution contains much more probability mass. The Student-t VaR will always be >= Normal VaR when the fitted df is finite.

**Monte Carlo vs. Parametric Normal:**

In this implementation, Monte Carlo draws from a multivariate Normal, so it should converge to the Parametric Normal VaR as the number of simulations increases. Any remaining difference is simulation noise. With 10,000 simulations, expect the Monte Carlo VaR to be within 5-10% of the Parametric Normal VaR. If the gap is larger, increase the simulation count.

**Monte Carlo vs. Historical:**

This comparison reveals whether the fitted multivariate Normal adequately describes the historical return distribution. A large gap suggests that the historical period contained regime changes, volatility clustering, or tail events that the Normal model cannot capture.

### When to Use Which Model

| Model | Best For | Limitations |
|---|---|---|
| **Historical** | Transparent reporting, regulatory backtesting, capturing regime-specific behavior in the historical window. | Limited by the data window. Cannot forecast risks not in the sample. Sensitive to window length. |
| **Parametric Normal** | Fast computation, risk decomposition, marginal VaR analysis, large portfolios where speed matters. | Underestimates tail risk. Kurtosis of financial returns exceeds 3 almost universally. |
| **Parametric Student-t** | Portfolios with known fat tails, single-asset risk, comparing against Normal to quantify tail risk. | Assumes a single distributional form. Cannot capture skewness (the Student-t is symmetric). Fitting can be unstable with small samples. |
| **Monte Carlo** | Non-linear instruments (options), multi-asset portfolios with complex correlation structures, stress testing with custom scenarios. | Computationally expensive. Only as good as the assumed distribution for simulation (Normal in this implementation). Requires seed management for reproducibility. |

### Why Basel III Moved from VaR to ES

The transition from VaR to ES in the FRTB framework was driven by fundamental deficiencies in VaR that became painfully apparent during the 2007-2008 financial crisis:

**1. VaR is blind beyond the threshold.**

VaR at 99% tells you: "There is a 1% chance of losing more than $X." It says nothing about *how much* more. Portfolio A might lose $X+1 in the worst case; Portfolio B might lose $X+100. Both have the same VaR. ES distinguishes them by averaging the entire tail.

**2. VaR fails the subadditivity test.**

A risk measure should reward diversification: combining two positions should not increase total risk. VaR can violate this for non-elliptical distributions and discrete loss distributions. ES is mathematically guaranteed to satisfy subadditivity. This makes ES suitable for consistent top-down capital allocation across business lines.

**3. VaR can be gamed.**

Traders discovered that certain positions (e.g., selling deep out-of-the-money options) could generate income while keeping VaR low, because the probability of a large loss was just below the VaR threshold. ES captures these buried tail risks because it considers the full conditional expectation of losses in the tail.

**4. Calibration equivalence for Normal distributions.**

The Basel Committee chose 97.5% ES specifically because, under the Normal distribution:

```
ES_{97.5%} approx= VaR_{99%}
```

This means that for well-behaved (Normal) portfolios, capital requirements stay roughly the same. But for portfolios with fat tails, the ES-based capital charge is appropriately higher. This penalizes tail risk without over-penalizing plain-vanilla portfolios.

**5. Consistency across liquidity horizons.**

FRTB requires risk to be measured at multiple liquidity horizons (10, 20, 40, 60, 120 days), depending on how quickly a position can be unwound. ES aggregates more naturally across these horizons than VaR.

### Summary Comparison Table

For a typical equity portfolio (mu approx= 0, sigma = 1.5% daily, df approx= 5):

| Metric | Normal | Student-t | Historical (typical) |
|---|---|---|---|
| 95% VaR (1D) | 2.47% | ~3.03% | ~2.5-3.5% |
| 99% VaR (1D) | 3.49% | ~5.05% | ~3.5-5.0% |
| 95% ES (1D) | 3.10% | ~4.20% | ~3.5-4.5% |
| 99% ES (1D) | 3.87% | ~7.50% | ~5.0-7.0% |

Key observations:
- At 95% confidence, all models are in the same ballpark.
- At 99% confidence, the gap between Normal and Student-t widens dramatically.
- Historical estimates depend entirely on the sample period.
- ES always exceeds VaR, and the ES/VaR ratio increases for heavier-tailed distributions.

### Demo Talking Points for the Comparison View

- "The comparison chart in the system runs all four models on the same data and shows them side by side. The differences tell a story about the shape of the return distribution."
- "If the Student-t VaR is much larger than the Normal VaR, the data has fat tails. The `t_df` parameter quantifies exactly how fat. This is the single most important diagnostic for choosing between models."
- "Basel III FRTB moved from 99% VaR to 97.5% Expected Shortfall. For Normal returns, these are roughly equivalent. But for fat-tailed portfolios, ES captures significantly more risk -- which is the whole point of the regulatory change."
- "In production, you would run all models and present the range. The spread between the most optimistic (Normal VaR) and most conservative (Student-t ES) gives stakeholders a sense of model uncertainty. Risk management is about understanding what you don't know as much as what you do know."
