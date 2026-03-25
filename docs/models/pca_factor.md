# Principal Component Analysis & Factor Modelling

## 1. Principal Component Analysis (PCA)

### What it is
PCA is a dimensionality reduction technique that transforms correlated variables into a smaller set of uncorrelated variables called principal components. In finance, it identifies the dominant risk factors driving portfolio returns — typically, a handful of components explain the majority of return variation across dozens of assets.

### Why it matters
With 25 assets, understanding risk through individual correlations is impractical (300 pairwise correlations). PCA reveals that most of this complexity is driven by just 3-5 underlying factors. This has practical implications: you can hedge most of your portfolio risk by trading just a few factor-mimicking instruments.

### The math

**Step 1: Compute the covariance (or correlation) matrix**
```
Σ = (1/(n-1)) × Xᵀ × X
```
where X is the (T × N) returns matrix centered at zero.

**Step 2: Eigenvalue decomposition**
```
Σ = V × Λ × Vᵀ
```
where:
- Λ = diag(λ₁, λ₂, ..., λₙ) — eigenvalues sorted descending
- V = [v₁, v₂, ..., vₙ] — eigenvectors (principal component directions)

**Step 3: Variance explained**
```
Proportion of variance explained by PCₖ = λₖ / Σᵢ λᵢ
Cumulative variance explained by top k = Σⱼ₌₁ᵏ λⱼ / Σᵢ λᵢ
```

**Step 4: Principal component scores** (the actual factor time series)
```
F = X × V
```
where F[:,k] is the time series of the k-th factor.

**Interpretation of eigenvectors (loadings)**:
Each eigenvector vₖ tells you the "recipe" for that factor. If v₁ has roughly equal positive weights on all equities, PC1 is a "market factor." If v₂ has positive weights on bonds and negative on equities, PC2 captures the equity-bond rotation.

### Implementation
File: `backend/engine/quantitative.py`, function `compute_pca()`
- Standardizes returns with `sklearn.preprocessing.StandardScaler`
- Runs `sklearn.decomposition.PCA` retaining all components
- Returns eigenvalues, variance explained, cumulative variance, and per-component loadings

### Interpretation guide
- **Scree plot**: Look for the "elbow" — the point where additional components add diminishing explanatory power
- **Top 3 components explain ~50-70%**: Typical for a diversified multi-asset portfolio
- **PC1 explains > 40%**: One dominant factor (usually "market risk") drives most of the portfolio
- **Component loadings**: Show which assets contribute most to each factor

### Demo talking points
- "Despite having 25 assets, about 50% of portfolio risk comes from just 3 systematic factors. The first factor is essentially 'market direction' — when it moves, all equities move together."
- "The scree plot shows diminishing returns from adding more components. After the first 5, each additional component explains less than 5% — that's the idiosyncratic, diversifiable risk."
- "PCA is model-free — it discovers the factors from the data rather than assuming them upfront. This makes it more robust than pre-specified factor models."

---

## 2. Multi-Factor Regression (Fama-French Style)

### What it is
A multi-factor model explains each asset's returns using a set of known risk factors. We use a Fama-French-style decomposition with three factors: Market (MKT), Size (SMB), and Value (HML).

### Why it matters
Factor models are the industry standard for performance attribution ("where did returns come from?"), risk decomposition ("what drives portfolio risk?"), and alpha generation ("is the manager adding value beyond factor exposure?"). The Fama-French model won the Nobel Prize in Economics.

### The math

**Model for each asset i**:
```
rᵢ - rf = αᵢ + β₁ᵢ × MKT + β₂ᵢ × SMB + β₃ᵢ × HML + εᵢ
```

Where:
- rᵢ - rf = excess return of asset i over risk-free rate
- rf = risk-free rate (4% annualized = 0.04/252 daily)
- MKT = market excess return (equal-weighted mean of equity returns minus rf)
- SMB = "Small Minus Big" — return spread between small and large stocks (by volatility as proxy for size)
- HML = "High Minus Low" — return spread between high and low mean-return stocks (as proxy for value)
- αᵢ = alpha — abnormal return not explained by factors
- β₁ᵢ = market beta — sensitivity to overall market
- εᵢ = residual — idiosyncratic, uncorrelated noise

**Estimated via Ordinary Least Squares (OLS)**:
```
β̂ = (XᵀX)⁻¹ × Xᵀy
```

**Key statistics**:
- **R²**: Proportion of return variance explained by factors. R² = 1 - SS_res/SS_tot
- **Adjusted R²**: Penalizes for number of factors: R²_adj = 1 - ((1-R²)(n-1))/(n-k-1)
- **t-statistic**: Tests if a coefficient is statistically different from zero: t = β̂/SE(β̂)
- **p-value**: Probability of observing this t-stat under the null hypothesis β = 0

### Implementation
File: `backend/engine/quantitative.py`, function `compute_regression()`
- Constructs synthetic MKT, SMB, HML factors from the return data
- Runs `statsmodels.OLS` per asset
- Returns alpha, betas, R², t-stats, p-values

### Interpretation guide
- **α > 0 with p < 0.05**: Asset generates statistically significant positive excess return (alpha)
- **β_MKT ≈ 1.0**: Asset moves 1:1 with the market
- **β_MKT > 1.0**: More volatile than the market (amplifies market moves)
- **β_MKT < 1.0**: Less volatile (defensive)
- **R² > 0.5**: Most variation explained by these three factors
- **R² < 0.2**: Factors don't explain much — asset has strong idiosyncratic drivers

### Demo talking points
- "The Fama-French model decomposes returns into market risk, size risk, and value risk. A high market beta means the asset amplifies market swings."
- "Alpha is the holy grail — it represents return above what the factors explain. In efficient markets, alpha should be close to zero for passive investments."
- "Notice how bonds and commodities have low R² with these equity-centric factors — they're driven by different forces entirely, which is why they're valuable for diversification."

---

## 3. Asset Class Exposure Analysis

### What it is
Breaks down portfolio risk by asset class, showing not just how much capital is allocated (weight) but how much risk each class contributes (risk contribution).

### Why it matters
A portfolio may have equal weights across asset classes but highly unequal risk contributions. Equities typically dominate risk even in "balanced" portfolios. Understanding this gap between weight and risk contribution is essential for risk budgeting.

### The math

**Risk contribution of asset i**:
```
RC_i = w_i × (Σ × w)_i / σ_p
```
Where:
- w_i = weight of asset i
- Σ = annualized covariance matrix
- (Σ × w)_i = i-th element of the matrix-vector product
- σ_p = portfolio volatility = √(w' × Σ × w)

Property: Σᵢ RC_i = σ_p (risk contributions sum to total portfolio risk)

**Percentage risk contribution**:
```
%RC_i = RC_i / σ_p = w_i × (Σ × w)_i / σ_p²
```

### Implementation
File: `backend/engine/quantitative.py`, function `compute_exposure()`
- Computes annualized covariance matrix
- Calculates per-asset and per-class risk contributions

### Interpretation guide
- If equities are 40% of weight but 75% of risk contribution → portfolio risk is dominated by equity exposure
- Negative risk contribution means the asset is hedging other positions
- Risk parity would target equal risk contributions across classes

### Demo talking points
- "Even with equal weighting, equities contribute the majority of portfolio risk because they're more volatile and more correlated with each other."
- "The gap between weight allocation and risk allocation is what risk budgeting aims to address."
- "A negative risk contribution means that asset is actually reducing total portfolio risk — it's a natural hedge."
