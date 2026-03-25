# Cluster Analysis

## K-Means Clustering

### What it is
K-means clustering groups assets with similar risk-return profiles into clusters. Each asset is described by a feature vector (mean return, volatility, skewness, kurtosis), and the algorithm finds natural groupings by minimizing within-cluster distances.

### Why it matters
Clustering reveals hidden structure in a portfolio. Assets in the same cluster respond similarly to market events, meaning holding multiple assets from the same cluster provides less diversification than holding assets from different clusters. This insight drives portfolio construction and risk management.

### The math

**Objective function** (minimize within-cluster sum of squares):
```
J = Σₖ₌₁ᴷ Σᵢ∈Cₖ ||xᵢ - μₖ||²
```
Where:
- K = number of clusters
- Cₖ = set of assets assigned to cluster k
- xᵢ = feature vector for asset i
- μₖ = centroid (mean) of cluster k

**Algorithm (Lloyd's algorithm)**:
1. Initialize K centroids randomly
2. **Assignment step**: Assign each asset to the nearest centroid
   ```
   Cₖ = {xᵢ : ||xᵢ - μₖ||² ≤ ||xᵢ - μⱼ||² for all j}
   ```
3. **Update step**: Recompute each centroid as the mean of its members
   ```
   μₖ = (1/|Cₖ|) Σᵢ∈Cₖ xᵢ
   ```
4. Repeat steps 2-3 until convergence (assignments stop changing)

**Feature vector per asset** (4 dimensions):
```
xᵢ = [annualized_mean_return, annualized_volatility, skewness, kurtosis]
```

**Feature standardization** (z-score):
```
x'ᵢⱼ = (xᵢⱼ - μⱼ) / σⱼ
```
This ensures all features contribute equally — otherwise volatility (large values) would dominate mean return (small values).

**Choosing K — the Elbow Method**:
- Run K-means for k = 2, 3, 4, 5, 6
- Plot total inertia J against k
- Look for the "elbow" — the k where adding more clusters gives diminishing reduction in J
- We also use the second derivative (acceleration) to detect the elbow programmatically
- Default to k=3 if no clear elbow

**Visualization via PCA projection**:
- Reduce 4D features to 2D using PCA for scatter plot
- Color points by cluster assignment
- Mark centroids with X

### Implementation
File: `backend/engine/quantitative.py`, function `compute_clustering()`
- Feature extraction from returns (mean, vol, skew, kurt per asset)
- Standardization via `sklearn.preprocessing.StandardScaler`
- Elbow method with `sklearn.cluster.KMeans` for k=2..6
- Final clustering with optimal k
- 2D projection via `sklearn.decomposition.PCA(n_components=2)`

### Interpretation guide
- **3 clusters typical**: Often maps to (1) high-vol equities, (2) low-vol bonds, (3) commodities/FX
- **Assets in same cluster**: Similar risk profiles, limited diversification between them
- **Assets in different clusters**: Different risk profiles, good diversification candidates
- **Centroid location**: The "typical" asset in that cluster
- **Inertia**: Total within-cluster variance — lower is tighter clusters

### Demo talking points
- "The clustering algorithm discovers three natural groups in our portfolio: equities characterised by moderate-to-high volatility and negative skew, fixed income with low volatility and near-zero skew, and commodities/FX with distinct mean-reversion characteristics."
- "If you want to diversify, add assets from different clusters. Holding five tech stocks from the same cluster gives you less diversification than holding one equity, one bond, and one commodity."
- "We use the elbow method to avoid over-fitting — too many clusters would split natural groups, while too few would merge different risk profiles."
- "The 2D scatter plot uses PCA to project the 4D feature space down to two dimensions while preserving as much variation as possible."
