# Statistical Risk Analysis

## 1. Distribution Moments

### What it is
Statistical moments describe the shape of a probability distribution. For financial returns, we compute four moments: mean (central tendency), variance (spread), skewness (asymmetry), and kurtosis (tail heaviness).

### Why it matters
Moments are the foundation of risk analysis. Variance measures risk (Markowitz portfolio theory). Skewness and kurtosis reveal whether standard models (which assume normality) are appropriate — and for financial data, they almost never are. Regulators and risk managers need to understand these properties to avoid underestimating tail risk.

### The math

**Mean** (first moment):
```
μ = (1/n) Σᵢ xᵢ
```
Annualized: μ_annual = μ_daily × 252

**Variance** (second central moment):
```
σ² = (1/(n-1)) Σᵢ (xᵢ - μ)²
```
We use n-1 (Bessel's correction) for an unbiased estimator from a sample.
Annualized: σ²_annual = σ²_daily × 252

**Skewness** (third standardized moment):
```
γ₁ = (1/n) Σᵢ ((xᵢ - μ)/σ)³
```
- γ₁ = 0: symmetric distribution (like normal)
- γ₁ < 0: left tail is heavier (negative skew) — large losses more likely than large gains
- γ₁ > 0: right tail is heavier (positive skew)

Financial returns typically exhibit **negative skewness**: crashes are larger and more sudden than rallies.

**Kurtosis** (fourth standardized moment):
```
κ = (1/n) Σᵢ ((xᵢ - μ)/σ)⁴
```
We report **excess kurtosis** = κ - 3 (relative to the normal distribution which has κ = 3).
- Excess κ = 0: tails like a normal distribution
- Excess κ > 0: **leptokurtic** — fatter tails, more extreme events than normal predicts
- Excess κ < 0: **platykurtic** — thinner tails

Financial returns are almost always leptokurtic (excess κ typically 3-10), meaning extreme events happen far more often than a normal distribution predicts.

**Portfolio moments**:
- Portfolio mean: μ_p = Σᵢ wᵢ × μᵢ (simple weighted average)
- Portfolio variance: σ²_p = w' × Σ × w (requires the full covariance matrix)
- Portfolio skewness/kurtosis: we use a weighted average approximation (exact computation requires co-skewness and co-kurtosis tensors, which are beyond prototype scope)

### Implementation
File: `backend/engine/statistics.py`, function `compute_moments()`
- Uses `pandas.Series.mean()`, `.var(ddof=1)`, `.skew()`, `.kurtosis()` (which returns excess kurtosis)
- Portfolio variance computed via matrix multiplication: `w' @ Σ @ w`

### Interpretation guide
- **Mean of 0.0003 daily** = approximately 7.6% annualized return
- **Variance of 0.0004 daily** = approximately 10% annualized volatility (√(0.0004 × 252) ≈ 0.317)
- **Skewness of -0.3** = moderately left-skewed, losses tend to be larger than gains
- **Excess kurtosis of 4.0** = significantly fat-tailed, extreme events ~4x more frequent than normal predicts

### Demo talking points
- "Financial returns show negative skewness and positive excess kurtosis — fat tails. This means the normal distribution systematically underestimates the probability of large losses."
- "The variance is the foundation of risk measurement — it's what drives VaR and portfolio optimization."
- "Kurtosis of 4+ means we see extreme events several times more often than a bell curve would predict. This is why we test multiple distributions, not just the normal."

---

## 2. Correlation Matrix

### What it is
The correlation matrix shows pairwise linear relationships between all assets in the portfolio. Each entry ρ(X,Y) ranges from -1 (perfect negative correlation) to +1 (perfect positive correlation).

### Why it matters
Correlation is the engine of diversification. When assets are imperfectly correlated, combining them reduces portfolio risk below the weighted average of individual risks. This is the core insight of Modern Portfolio Theory (Markowitz, 1952). Regulators also care about correlation because during crises, correlations tend to spike toward 1.0, undermining diversification exactly when it's needed most.

### The math
**Pearson correlation**:
```
ρ(X,Y) = cov(X,Y) / (σ_X × σ_Y)
```
where:
```
cov(X,Y) = (1/(n-1)) Σᵢ (xᵢ - μ_X)(yᵢ - μ_Y)
```

Properties:
- ρ ∈ [-1, +1]
- ρ = 1: perfect positive linear relationship
- ρ = 0: no linear relationship (but could still be nonlinearly dependent!)
- ρ = -1: perfect negative linear relationship

**Limitation**: Pearson correlation only captures **linear** dependence. Two assets could have ρ = 0 yet still be strongly dependent through nonlinear relationships. For financial data, this is a known limitation — copula models address this but are outside our prototype scope.

### Implementation
File: `backend/engine/statistics.py`, function `compute_correlation()`
- Uses `pandas.DataFrame.corr(method="pearson")`

### Interpretation guide
- **ρ > 0.7**: Strongly correlated — limited diversification benefit
- **ρ = 0.3-0.7**: Moderately correlated — some diversification
- **ρ ≈ 0**: Uncorrelated — good diversification
- **ρ < -0.3**: Negatively correlated — excellent diversification (hedging)
- Intra-sector equity correlation (e.g., AAPL-MSFT): typically 0.6-0.8
- Equity-bond correlation: typically -0.2 to 0.2
- Gold-equity correlation: typically near 0 or slightly negative

### Demo talking points
- "Notice the block structure — tech stocks are highly correlated with each other (~0.7) but much less with bonds or commodities. This is diversification in action."
- "The equity-bond negative correlation is why balanced portfolios work — when stocks fall, bonds tend to rise."
- "Correlation only measures linear dependence. During crises, correlations spike — this is the 'correlation breakdown' problem that regulators worry about."

---

## 3. Distribution Fitting

### What it is
We fit three candidate probability distributions to each asset's return series and select the best one using a statistical criterion. This tells us which mathematical model best describes how returns are distributed.

### Why it matters
The choice of distribution directly affects risk estimates. If you assume normality but returns are actually fat-tailed, you'll underestimate VaR and ES — potentially by a factor of 2-3x for extreme quantiles. Distribution fitting provides evidence for the right model.

### The math

**Maximum Likelihood Estimation (MLE)**:
For a given distribution with parameters θ, the likelihood is:
```
L(θ) = Πᵢ f(xᵢ | θ)
```
We maximize the log-likelihood:
```
ln L(θ) = Σᵢ ln f(xᵢ | θ)
```

**Candidate distributions**:

1. **Normal** (2 parameters: μ, σ):
   ```
   f(x) = (1/(σ√(2π))) × exp(-(x-μ)²/(2σ²))
   ```

2. **Student-t** (3 parameters: ν, μ, σ):
   ```
   f(x) = Γ((ν+1)/2) / (Γ(ν/2) × √(νπ) × σ) × (1 + ((x-μ)/σ)²/ν)^(-(ν+1)/2)
   ```
   The degrees of freedom ν controls tail heaviness. As ν → ∞, Student-t → Normal.
   For financial data, ν typically fits between 3-8, indicating heavy tails.

3. **Skewed Normal** (3 parameters: α, μ, σ):
   Adds an asymmetry parameter α. When α = 0, it reduces to the normal distribution.

**Model selection via AIC** (Akaike Information Criterion):
```
AIC = 2k - 2 ln(L)
```
where k = number of parameters, L = maximized likelihood.
Lower AIC is better. AIC balances goodness-of-fit against model complexity (penalizes extra parameters).

### Implementation
File: `backend/engine/statistics.py`, function `compute_distribution_fitting()`
- Uses `scipy.stats.norm.fit()`, `scipy.stats.t.fit()`, `scipy.stats.skewnorm.fit()` for MLE
- AIC computed as `2k - 2*log_likelihood`

### Interpretation guide
- **Student-t wins** (most common for financial data): confirms fat tails, ν parameter indicates how heavy
  - ν ≈ 3-4: very heavy tails (highly volatile assets)
  - ν ≈ 6-10: moderate tails
  - ν > 30: effectively normal
- **Skewed Normal wins**: the dominant feature is asymmetry rather than tail heaviness
- **Normal wins**: rare for financial data, might indicate a very stable instrument

### Demo talking points
- "For most assets, the Student-t distribution wins because it captures the fat tails we see in financial returns."
- "The degrees-of-freedom parameter tells us how fat the tails are. Our equity returns fit with ν ≈ 5, meaning extreme events are much more likely than a normal distribution predicts."
- "This is why parametric VaR using a normal distribution can be dangerous — it systematically underestimates risk. Using the fitted Student-t distribution gives more conservative and realistic risk estimates."

---

## 4. Factor Distribution Modelling

### What it is
Factor modelling decomposes each asset's returns into components driven by common (systematic) factors plus an asset-specific (idiosyncratic) residual. We use PCA to extract the factors, then regress each asset on them.

### Why it matters
Factor models are the backbone of institutional risk management. They explain WHY assets move together (common factors) and separate diversifiable risk (idiosyncratic) from non-diversifiable risk (systematic). This decomposition drives hedging strategies, performance attribution, and regulatory capital calculations.

### The math

**Step 1: Extract factors via PCA** (see PCA documentation)
Extract top-3 principal components from the returns matrix → F₁, F₂, F₃

**Step 2: Regress each asset on factors**:
```
rᵢ = αᵢ + β₁ᵢ × F₁ + β₂ᵢ × F₂ + β₃ᵢ × F₃ + εᵢ
```

Where:
- αᵢ = intercept (alpha) — return not explained by factors
- βⱼᵢ = factor loading — sensitivity of asset i to factor j
- εᵢ = residual — idiosyncratic return, uncorrelated across assets (by construction)

**Coefficient of determination**:
```
R² = 1 - SS_res / SS_tot
```
- R² near 1: asset returns are almost entirely driven by common factors
- R² near 0: asset returns are mostly idiosyncratic

**Variance decomposition**:
```
Var(rᵢ) = Σⱼ βⱼᵢ² × Var(Fⱼ) + Var(εᵢ)
         = systematic risk    + idiosyncratic risk
```

### Implementation
File: `backend/engine/statistics.py`, function `compute_factor_model()`
- PCA via `sklearn.decomposition.PCA(n_components=3)`
- OLS regression via `statsmodels.api.OLS`

### Interpretation guide
- **High R²** (> 0.6): Asset is predominantly driven by systematic factors — harder to diversify
- **Low R²** (< 0.3): Asset has strong idiosyncratic component — easier to diversify in a portfolio
- **Alpha significantly different from 0**: Asset generates excess return beyond what factors explain
- **Large β₁**: High sensitivity to the primary market factor (typically overall equity market direction)
- **Residual volatility**: The "specific risk" that can be diversified away

### Demo talking points
- "The factor model separates systematic risk — which you can't diversify away — from idiosyncratic risk — which you can."
- "Equities typically show high R² because they're all driven by the same market factor. Bonds and commodities show lower R², meaning they add genuine diversification."
- "The residual volatility is the risk you can eliminate by holding a diversified portfolio. This is why portfolio risk is always less than the sum of individual asset risks."
