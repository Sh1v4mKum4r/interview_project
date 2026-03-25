"""
Quantitative techniques module for financial risk analysis.

Provides PCA, clustering, multi-factor regression, and exposure/risk
contribution analytics over a returns DataFrame.
"""

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm


# ---------------------------------------------------------------------------
# 1. Principal Component Analysis
# ---------------------------------------------------------------------------

def compute_pca(returns: pd.DataFrame, metadata: dict, config: dict) -> dict:
    """
    Run PCA on standardized asset returns.

    Parameters
    ----------
    returns : pd.DataFrame
        T x N DataFrame of asset returns (columns = assets).
    metadata : dict
        Descriptive information about the assets (unused here).
    config : dict
        Optional configuration (unused here).

    Returns
    -------
    dict  with keys "metrics" and "data".
    """
    asset_names = list(returns.columns)

    # Standardize to zero mean, unit variance
    scaler = StandardScaler()
    standardized = scaler.fit_transform(returns.dropna())

    # Fit PCA keeping all components
    n_components = min(standardized.shape[0], standardized.shape[1])
    pca = PCA(n_components=n_components)
    pca.fit(standardized)

    eigenvalues = pca.explained_variance_.tolist()
    variance_explained = pca.explained_variance_ratio_.tolist()
    cumulative_variance = np.cumsum(pca.explained_variance_ratio_).tolist()

    # Component loadings: each row of components_ is a principal component
    # expressed as linear combination of original features (assets)
    component_loadings = {}
    for i in range(n_components):
        pc_label = f"PC{i + 1}"
        component_loadings[pc_label] = {
            asset: float(pca.components_[i, j])
            for j, asset in enumerate(asset_names)
        }

    top_3_explain = float(cumulative_variance[min(2, len(cumulative_variance) - 1)])

    return {
        "metrics": {
            "n_components": n_components,
            "eigenvalues": eigenvalues,
            "variance_explained": variance_explained,
            "cumulative_variance": cumulative_variance,
            "top_3_components_explain": top_3_explain,
        },
        "data": {
            "eigenvalues": eigenvalues,
            "variance_explained": variance_explained,
            "cumulative_variance": cumulative_variance,
            "component_loadings": component_loadings,
            "labels": asset_names,
        },
    }


# ---------------------------------------------------------------------------
# 2. Clustering
# ---------------------------------------------------------------------------

def _find_optimal_k(inertias: list[float], k_values: list[int]) -> int:
    """
    Detect the elbow in the inertia curve using the largest second-derivative
    (discrete curvature).  Falls back to 3 if nothing stands out.
    """
    if len(inertias) < 3:
        return k_values[0]

    # Second finite differences
    second_diffs = []
    for i in range(1, len(inertias) - 1):
        d2 = inertias[i - 1] - 2 * inertias[i] + inertias[i + 1]
        second_diffs.append(d2)

    # The elbow is the k whose second derivative is largest
    if second_diffs and max(second_diffs) > 0:
        best_idx = int(np.argmax(second_diffs)) + 1  # +1 because we started at index 1
        return k_values[best_idx]

    return 3  # default


def compute_clustering(returns: pd.DataFrame, metadata: dict, config: dict) -> dict:
    """
    Cluster assets by statistical features of their return series.

    Features per asset: annualized mean return, annualized volatility,
    skewness, kurtosis.

    Parameters
    ----------
    returns : pd.DataFrame
        T x N DataFrame of asset returns.
    metadata : dict
        Descriptive information about the assets (unused here).
    config : dict
        Optional configuration (unused here).

    Returns
    -------
    dict  with keys "metrics" and "data".
    """
    asset_names = list(returns.columns)
    clean = returns.dropna()

    # Build feature matrix: one row per asset
    ann_mean = clean.mean() * 252
    ann_vol = clean.std() * np.sqrt(252)
    skew = clean.skew()
    kurt = clean.kurtosis()

    features_df = pd.DataFrame({
        "ann_mean": ann_mean,
        "ann_vol": ann_vol,
        "skewness": skew,
        "kurtosis": kurt,
    }, index=asset_names)

    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features_df.values)

    # Elbow method: k = 2..6
    k_values = list(range(2, 7))
    inertias: list[float] = []
    for k in k_values:
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        km.fit(features_scaled)
        inertias.append(float(km.inertia_))

    optimal_k = _find_optimal_k(inertias, k_values)

    # Final clustering
    km_final = KMeans(n_clusters=optimal_k, n_init=10, random_state=42)
    labels = km_final.fit_predict(features_scaled)
    centroids = km_final.cluster_centers_

    # PCA to 2D for scatter visualisation
    pca_2d = PCA(n_components=2)
    coords_2d = pca_2d.fit_transform(features_scaled)
    centroids_2d = pca_2d.transform(centroids)

    assignments = {asset: int(labels[i]) for i, asset in enumerate(asset_names)}

    return {
        "metrics": {
            "n_clusters": optimal_k,
            "assignments": assignments,
            "centroids": centroids.tolist(),
            "inertia": float(km_final.inertia_),
        },
        "data": {
            "scatter": {
                "x": coords_2d[:, 0].tolist(),
                "y": coords_2d[:, 1].tolist(),
                "labels": asset_names,
                "clusters": [int(l) for l in labels],
                "centroids_x": centroids_2d[:, 0].tolist(),
                "centroids_y": centroids_2d[:, 1].tolist(),
            },
            "elbow": {
                "k_values": k_values,
                "inertias": inertias,
            },
        },
    }


# ---------------------------------------------------------------------------
# 3. Multi-Factor Regression (Fama-French style)
# ---------------------------------------------------------------------------

def compute_regression(returns: pd.DataFrame, metadata: dict, config: dict) -> dict:
    """
    Run Fama-French-style multi-factor OLS regressions for every asset.

    Synthetic factors are built from the returns data itself:
      MKT  – equal-weighted mean of all equity returns, excess of rf
      SMB  – small-minus-big (by volatility)
      HML  – high-minus-low (by mean return)

    Parameters
    ----------
    returns : pd.DataFrame
        T x N DataFrame of asset returns.
    metadata : dict
        Descriptive information about the assets (unused here).
    config : dict
        Optional configuration (unused here).

    Returns
    -------
    dict  with keys "metrics" and "data".
    """
    clean = returns.dropna()
    asset_names = list(clean.columns)
    rf_daily = 0.04 / 252  # daily risk-free rate

    # ---- Build synthetic factors ----

    # MKT: equal-weighted mean excess return
    mkt = clean.mean(axis=1) - rf_daily

    # SMB: sort assets by volatility
    vols = clean.std().sort_values()
    n = len(asset_names)
    small_assets = vols.index[:3].tolist()
    big_assets = vols.index[-3:].tolist()
    smb = clean[small_assets].mean(axis=1) - clean[big_assets].mean(axis=1)

    # HML: sort assets by mean return
    means = clean.mean().sort_values()
    high_assets = means.index[-2:].tolist()
    low_assets = means.index[:2].tolist()
    hml = clean[high_assets].mean(axis=1) - clean[low_assets].mean(axis=1)

    factors = pd.DataFrame({"MKT": mkt, "SMB": smb, "HML": hml}, index=clean.index)
    factors_with_const = sm.add_constant(factors)

    # ---- Per-asset regressions ----
    metrics_per_asset: dict[str, dict] = {}
    all_coefficients: list[list[float]] = []
    all_r_squared: list[float] = []

    for asset in asset_names:
        y = clean[asset] - rf_daily  # excess return
        model = sm.OLS(y, factors_with_const).fit()

        # Coefficients: const (alpha), MKT, SMB, HML
        alpha = float(model.params["const"])
        beta_mkt = float(model.params["MKT"])
        beta_smb = float(model.params["SMB"])
        beta_hml = float(model.params["HML"])

        t_stats = {
            "alpha": float(model.tvalues["const"]),
            "beta_mkt": float(model.tvalues["MKT"]),
            "beta_smb": float(model.tvalues["SMB"]),
            "beta_hml": float(model.tvalues["HML"]),
        }

        p_values = {
            "alpha": float(model.pvalues["const"]),
            "beta_mkt": float(model.pvalues["MKT"]),
            "beta_smb": float(model.pvalues["SMB"]),
            "beta_hml": float(model.pvalues["HML"]),
        }

        metrics_per_asset[asset] = {
            "alpha": alpha,
            "beta_mkt": beta_mkt,
            "beta_smb": beta_smb,
            "beta_hml": beta_hml,
            "r_squared": float(model.rsquared),
            "adj_r_squared": float(model.rsquared_adj),
            "t_stats": t_stats,
            "p_values": p_values,
        }

        all_coefficients.append([alpha, beta_mkt, beta_smb, beta_hml])
        all_r_squared.append(float(model.rsquared))

    return {
        "metrics": metrics_per_asset,
        "data": {
            "factor_names": ["MKT", "SMB", "HML"],
            "assets": asset_names,
            "coefficients": all_coefficients,
            "r_squared": all_r_squared,
        },
    }


# ---------------------------------------------------------------------------
# 4. Exposure / Risk Contribution
# ---------------------------------------------------------------------------

def compute_exposure(returns: pd.DataFrame, metadata: dict, config: dict) -> dict:
    """
    Compute portfolio weight and risk-contribution breakdowns by asset and
    asset class.

    Parameters
    ----------
    returns : pd.DataFrame
        T x N DataFrame of asset returns.
    metadata : dict
        Must contain asset-class mapping.  Accepts either:
          - metadata[asset]["class"]  (dict of dicts), or
          - metadata[asset]           (dict mapping asset -> class string)
    config : dict
        Must contain "weights": {asset_name: weight}.

    Returns
    -------
    dict  with keys "metrics" and "data".
    """
    weights_dict: dict[str, float] = config.get("weights", {})
    asset_names = list(returns.columns)
    clean = returns.dropna()

    # Build weight vector aligned with columns
    w = np.array([weights_dict.get(a, 0.0) for a in asset_names], dtype=float)

    # Covariance matrix (annualised)
    cov = clean.cov().values * 252

    # Portfolio volatility
    port_var = float(w @ cov @ w)
    port_vol = float(np.sqrt(port_var)) if port_var > 0 else 0.0

    # Risk contributions: RC_i = w_i * (Sigma @ w)_i / sigma_p
    sigma_w = cov @ w  # N-vector
    if port_vol > 0:
        rc = (w * sigma_w) / port_vol
    else:
        rc = np.zeros_like(w)

    rc_by_asset = {asset: float(rc[i]) for i, asset in enumerate(asset_names)}

    # Resolve asset class for each asset
    ac_map = metadata.get("asset_classes", {})
    asset_classes = {a: ac_map.get(a, "unknown") for a in asset_names}

    # Aggregate weights and risk contributions by class
    weight_by_class: dict[str, float] = {}
    rc_by_class: dict[str, float] = {}
    for i, asset in enumerate(asset_names):
        cls = asset_classes[asset]
        weight_by_class[cls] = weight_by_class.get(cls, 0.0) + float(w[i])
        rc_by_class[cls] = rc_by_class.get(cls, 0.0) + float(rc[i])

    classes_list = list(weight_by_class.keys())

    return {
        "metrics": {
            "weight_by_class": weight_by_class,
            "risk_contribution_by_class": rc_by_class,
            "risk_contribution_by_asset": rc_by_asset,
            "portfolio_volatility": port_vol,
        },
        "data": {
            "classes": classes_list,
            "weights": [weight_by_class[c] for c in classes_list],
            "risk_contributions": [rc_by_class[c] for c in classes_list],
            "assets": asset_names,
            "asset_risk_contributions": [float(rc[i]) for i in range(len(asset_names))],
        },
    }
