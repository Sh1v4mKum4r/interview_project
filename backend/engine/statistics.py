"""
Statistical Risk Analysis Module

Provides four core analyses for financial return data:
  - Moment analysis (mean, variance, skewness, kurtosis)
  - Correlation matrix computation
  - Distribution fitting (Normal, Student-t, Skewed Normal) with AIC selection
  - PCA-based factor model with OLS regressions

Every public function follows the interface contract:
    def compute_<analysis>(returns: pd.DataFrame, metadata: dict, config: dict) -> dict
and returns {"data": ..., "metrics": ...}.
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA
import statsmodels.api as sm


# ---------------------------------------------------------------------------
# 1. Moment Analysis
# ---------------------------------------------------------------------------

def compute_moments(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Calculate per-asset and portfolio-level statistical moments.

    Annualisation convention (daily data, 252 trading days):
      - mean  *= 252
      - variance *= 252
      - skewness and kurtosis are left un-annualised (they are unit-free /
        their annualisation is model-dependent)

    Parameters
    ----------
    returns : pd.DataFrame
        Daily log- or simple-return series. Columns are asset names.
    metadata : dict
        Contextual information (unused here, kept for interface consistency).
    config : dict
        Must contain ``"weights"`` — a list/array of portfolio weights aligned
        with the columns of *returns*.

    Returns
    -------
    dict
        ``"metrics"`` maps each asset name to {mean, variance, skewness, kurtosis}.
        ``"data"`` provides parallel arrays suitable for charting.
    """
    assets = list(returns.columns)
    weights_input = config.get("weights", {})
    if isinstance(weights_input, dict):
        weights = np.array([weights_input.get(a, 1.0 / len(assets)) for a in assets])
    else:
        weights = np.array(weights_input)
    # Normalize in case of rounding issues
    if weights.sum() > 0:
        weights = weights / weights.sum()

    per_asset_metrics = {}
    means = []
    variances = []
    skews = []
    kurts = []

    for asset in assets:
        series = returns[asset].dropna()
        m = float(series.mean() * 252)
        v = float(series.var(ddof=1) * 252)
        s = float(series.skew())
        k = float(series.kurtosis())  # excess kurtosis (Fisher)

        per_asset_metrics[asset] = {
            "mean": m,
            "variance": v,
            "skewness": s,
            "kurtosis": k,
        }
        means.append(m)
        variances.append(v)
        skews.append(s)
        kurts.append(k)

    # Portfolio-level moments --------------------------------------------------
    daily_means = returns.mean().values
    cov_matrix = returns.cov().values  # sample covariance (ddof=1 by default)

    port_mean = float(np.dot(weights, daily_means) * 252)
    port_var = float(np.dot(weights, cov_matrix @ weights) * 252)

    # Weighted skewness / kurtosis (simple weighted average of marginals —
    # a pragmatic approximation; exact portfolio higher moments require
    # co-skewness / co-kurtosis tensors which are outside scope).
    asset_skews = np.array([returns[a].skew() for a in assets])
    asset_kurts = np.array([returns[a].kurtosis() for a in assets])
    port_skew = float(np.dot(weights, asset_skews))
    port_kurt = float(np.dot(weights, asset_kurts))

    per_asset_metrics["portfolio"] = {
        "mean": port_mean,
        "variance": port_var,
        "skewness": port_skew,
        "kurtosis": port_kurt,
    }

    return {
        "metrics": per_asset_metrics,
        "data": {
            "assets": assets,
            "mean": means,
            "variance": variances,
            "skewness": skews,
            "kurtosis": kurts,
        },
    }


# ---------------------------------------------------------------------------
# 2. Correlation Analysis
# ---------------------------------------------------------------------------

def compute_correlation(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Pearson correlation matrix across all assets.

    Parameters
    ----------
    returns : pd.DataFrame
        Daily return series. Columns are asset names.
    metadata : dict
        Contextual information (unused).
    config : dict
        Reserved for future options (e.g. method="spearman").

    Returns
    -------
    dict
        ``"metrics"`` and ``"data"`` both expose the correlation matrix as a
        nested list together with asset labels.
    """
    corr = returns.corr(method="pearson")
    labels = list(corr.columns)
    matrix = corr.values.tolist()

    return {
        "metrics": {
            "matrix": matrix,
        },
        "data": {
            "labels": labels,
            "matrix": matrix,
        },
    }


# ---------------------------------------------------------------------------
# 3. Distribution Fitting
# ---------------------------------------------------------------------------

def _aic(k: int, log_likelihood: float) -> float:
    """Akaike Information Criterion: AIC = 2k - 2 ln(L)."""
    return 2.0 * k - 2.0 * log_likelihood


def _fit_and_score(data: np.ndarray) -> dict:
    """Fit Normal, Student-t, and Skewed Normal; return params, AIC, pdf curves.

    Returns
    -------
    dict
        Keys: ``"best_fit"``, ``"params"``, ``"aic"``, ``"histogram"``,
        ``"fitted_curves"``.
    """
    results = {}

    # --- Normal ---------------------------------------------------------------
    mu, sigma = stats.norm.fit(data)
    ll_norm = np.sum(stats.norm.logpdf(data, loc=mu, scale=sigma))
    results["Normal"] = {
        "params": {"loc": float(mu), "scale": float(sigma)},
        "k": 2,
        "log_likelihood": float(ll_norm),
        "aic": _aic(2, ll_norm),
        "dist": stats.norm,
        "fit_args": (mu, sigma),
    }

    # --- Student-t ------------------------------------------------------------
    df_t, loc_t, scale_t = stats.t.fit(data)
    ll_t = np.sum(stats.t.logpdf(data, df_t, loc=loc_t, scale=scale_t))
    results["Student-t"] = {
        "params": {"df": float(df_t), "loc": float(loc_t), "scale": float(scale_t)},
        "k": 3,
        "log_likelihood": float(ll_t),
        "aic": _aic(3, ll_t),
        "dist": stats.t,
        "fit_args": (df_t, loc_t, scale_t),
    }

    # --- Skewed Normal --------------------------------------------------------
    a_sn, loc_sn, scale_sn = stats.skewnorm.fit(data)
    ll_sn = np.sum(stats.skewnorm.logpdf(data, a_sn, loc=loc_sn, scale=scale_sn))
    results["Skewed Normal"] = {
        "params": {"a": float(a_sn), "loc": float(loc_sn), "scale": float(scale_sn)},
        "k": 3,
        "log_likelihood": float(ll_sn),
        "aic": _aic(3, ll_sn),
        "dist": stats.skewnorm,
        "fit_args": (a_sn, loc_sn, scale_sn),
    }

    # Select best fit by lowest AIC
    best_name = min(results, key=lambda n: results[n]["aic"])

    # Build histogram data
    counts, bin_edges = np.histogram(data, bins="auto", density=True)
    bin_centres = 0.5 * (bin_edges[:-1] + bin_edges[1:])

    # Build fitted pdf curves over a common x range
    x_min = float(data.min())
    x_max = float(data.max())
    x_grid = np.linspace(x_min, x_max, 200)

    fitted_curves = {}
    for name, info in results.items():
        dist = info["dist"]
        fit_args = info["fit_args"]
        if name == "Normal":
            y = dist.pdf(x_grid, loc=fit_args[0], scale=fit_args[1])
        elif name == "Student-t":
            y = dist.pdf(x_grid, fit_args[0], loc=fit_args[1], scale=fit_args[2])
        elif name == "Skewed Normal":
            y = dist.pdf(x_grid, fit_args[0], loc=fit_args[1], scale=fit_args[2])
        fitted_curves[name] = {
            "x": x_grid.tolist(),
            "y": y.tolist(),
        }

    aic_summary = {name: results[name]["aic"] for name in results}
    params_summary = {name: results[name]["params"] for name in results}

    return {
        "best_fit": best_name,
        "params": params_summary,
        "aic": aic_summary,
        "histogram": {
            "bins": bin_centres.tolist(),
            "counts": counts.tolist(),
        },
        "fitted_curves": fitted_curves,
    }


def compute_distribution_fitting(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Fit candidate distributions to each asset's return series and pick the
    best one via AIC.

    Candidate distributions:
      - Normal  (2 params)
      - Student-t  (3 params)
      - Skewed Normal  (3 params)

    Parameters
    ----------
    returns : pd.DataFrame
        Daily return series.
    metadata : dict
        Contextual information (unused).
    config : dict
        Reserved for future options.

    Returns
    -------
    dict
        ``"metrics"`` contains per-asset best-fit info.
        ``"data"`` contains histogram and fitted-curve arrays for charting.
    """
    assets = list(returns.columns)
    metrics = {}
    data_out = {}

    for asset in assets:
        series = returns[asset].dropna().values
        result = _fit_and_score(series)

        metrics[asset] = {
            "best_fit": result["best_fit"],
            "params": result["params"],
            "aic": result["aic"],
        }
        data_out[asset] = {
            "histogram": result["histogram"],
            "fitted_curves": result["fitted_curves"],
        }

    return {
        "metrics": metrics,
        "data": data_out,
    }


# ---------------------------------------------------------------------------
# 4. PCA-Based Factor Model
# ---------------------------------------------------------------------------

def compute_factor_model(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Extract latent factors via PCA then regress each asset on those factors.

    Model per asset *i*:
        r_i = alpha_i + sum_j(beta_ij * F_j) + epsilon_i

    where F_1..F_3 are the top-3 principal components of the returns matrix.

    Parameters
    ----------
    returns : pd.DataFrame
        Daily return series. Columns are asset names.
    metadata : dict
        Contextual information (unused).
    config : dict
        Optional ``"n_components"`` (default 3).

    Returns
    -------
    dict
        ``"metrics"`` maps each asset to {alpha, betas, r_squared, residual_vol}.
        ``"data"`` contains the factor-loading matrix for charting.
    """
    n_components = config.get("n_components", 3)
    assets = list(returns.columns)

    # Drop rows with any NaN so PCA and regressions use aligned observations
    clean = returns.dropna()
    returns_matrix = clean.values  # shape (T, N)

    # Clamp n_components to the maximum feasible value
    max_components = min(returns_matrix.shape[0], returns_matrix.shape[1])
    n_components = min(n_components, max_components)

    # PCA — extract factors
    pca = PCA(n_components=n_components)
    factors = pca.fit_transform(returns_matrix)  # shape (T, n_components)

    factor_names = [f"PC{i+1}" for i in range(n_components)]

    # OLS regression per asset
    X = sm.add_constant(factors)  # (T, 1 + n_components)
    per_asset_metrics = {}
    factor_loadings = []  # one row per asset

    for idx, asset in enumerate(assets):
        y = clean[asset].values
        model = sm.OLS(y, X).fit()

        alpha = float(model.params[0])
        betas = [float(b) for b in model.params[1:]]
        r_squared = float(model.rsquared)
        residuals = model.resid
        residual_vol = float(np.std(residuals, ddof=1) * np.sqrt(252))

        per_asset_metrics[asset] = {
            "alpha": alpha,
            "betas": betas,
            "r_squared": r_squared,
            "residual_vol": residual_vol,
        }
        factor_loadings.append(betas)

    return {
        "metrics": per_asset_metrics,
        "data": {
            "factor_loadings": factor_loadings,
            "assets": assets,
            "factors": factor_names,
        },
    }
