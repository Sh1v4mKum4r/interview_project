"""
Risk models module for financial risk analysis.

Provides Value-at-Risk (VaR) and Expected Shortfall (ES) computations
using historical, parametric, and Monte Carlo simulation approaches.

Every public function follows the interface contract:
    def compute_<analysis>(returns: pd.DataFrame, metadata: dict, config: dict) -> dict
    Returns a results dict with 'data' (for charts) and 'metrics' (for summary).
"""

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_horizon_days(horizon: str) -> int:
    """Map a time-horizon label to the number of trading days."""
    mapping = {"1D": 1, "10D": 10, "1M": 21, "1Y": 252}
    if horizon not in mapping:
        raise ValueError(
            f"Unknown time horizon '{horizon}'. "
            f"Supported values: {list(mapping.keys())}"
        )
    return mapping[horizon]


def _portfolio_returns(returns: pd.DataFrame, weights: dict) -> pd.Series:
    """Compute weighted portfolio returns from per-asset return columns.

    Parameters
    ----------
    returns : pd.DataFrame
        Columns are asset names, rows are time periods.
    weights : dict
        Mapping of asset name -> portfolio weight.  Only assets present in
        both *returns* and *weights* are used.

    Returns
    -------
    pd.Series
        Weighted sum of asset returns for each time period.
    """
    assets = [a for a in weights if a in returns.columns]
    w = np.array([weights[a] for a in assets])
    return returns[assets].dot(w)


def _make_histogram(data: np.ndarray, bins: int = 100) -> dict:
    """Return a JSON-friendly histogram dict."""
    counts, bin_edges = np.histogram(data, bins=bins)
    return {
        "bins": bin_edges.tolist(),
        "counts": counts.tolist(),
    }


def _scale_factor(horizon: str) -> float:
    """Return sqrt(days) scaling factor for the given horizon."""
    return np.sqrt(_get_horizon_days(horizon))


def _extract_config(config: dict):
    """Pull common configuration values with sensible defaults."""
    confidence_level = config.get("confidence_level", 0.95)
    time_horizon = config.get("time_horizon", "1D")
    weights = config.get("weights", {})
    portfolio_value = config.get("portfolio_value", 10_000_000)
    return confidence_level, time_horizon, weights, portfolio_value


# ---------------------------------------------------------------------------
# 1. Historical VaR
# ---------------------------------------------------------------------------

def compute_historical_var(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Historical simulation Value-at-Risk and Expected Shortfall.

    Sorts realised portfolio returns, picks the (1 - alpha) percentile as VaR,
    and averages all losses beyond that threshold for ES.  Also computes
    per-asset VaR/ES.  Results are scaled by the requested time horizon
    (sqrt-of-time rule) and expressed in dollar terms using *portfolio_value*.
    """
    confidence_level, time_horizon, weights, portfolio_value = _extract_config(config)
    scale = _scale_factor(time_horizon)

    # Portfolio-level returns
    port_ret = _portfolio_returns(returns, weights)
    sorted_returns = np.sort(port_ret.values)

    # VaR: the (1 - alpha) quantile of the return distribution (a negative number)
    alpha = 1 - confidence_level
    var_pct = np.percentile(sorted_returns, alpha * 100)

    # Expected Shortfall: mean of returns that fall at or below the VaR threshold
    tail = sorted_returns[sorted_returns <= var_pct]
    es_pct = tail.mean() if len(tail) > 0 else var_pct

    # Scale to chosen horizon
    var_scaled = var_pct * scale
    es_scaled = es_pct * scale

    # Dollar amounts (VaR/ES are losses, so negate to get positive dollar loss)
    var_dollar = abs(var_scaled) * portfolio_value
    es_dollar = abs(es_scaled) * portfolio_value

    # Per-asset breakdown
    per_asset: dict = {}
    for asset in weights:
        if asset not in returns.columns:
            continue
        asset_ret = returns[asset].values
        sorted_asset = np.sort(asset_ret)
        a_var = np.percentile(sorted_asset, alpha * 100)
        a_tail = sorted_asset[sorted_asset <= a_var]
        a_es = a_tail.mean() if len(a_tail) > 0 else a_var
        per_asset[asset] = {
            "var": float(a_var * scale),
            "es": float(a_es * scale),
        }

    return {
        "metrics": {
            "portfolio_var": float(var_scaled),
            "portfolio_es": float(es_scaled),
            "var_dollar": float(var_dollar),
            "es_dollar": float(es_dollar),
            "per_asset": per_asset,
        },
        "data": {
            "sorted_returns": sorted_returns.tolist(),
            "var_line": float(var_scaled),
            "es_line": float(es_scaled),
            "histogram": _make_histogram(sorted_returns),
        },
    }


# ---------------------------------------------------------------------------
# 2. Parametric VaR
# ---------------------------------------------------------------------------

def compute_parametric_var(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Parametric Value-at-Risk using Normal and Student-t assumptions.

    Normal variant:  VaR_alpha = mu + z_alpha * sigma
    Student-t variant: fits a t-distribution to the portfolio returns and uses
    t.ppf for the quantile.

    Returns the same structure as historical VaR with additional
    'normal_var' and 't_var' entries in metrics.
    """
    confidence_level, time_horizon, weights, portfolio_value = _extract_config(config)
    scale = _scale_factor(time_horizon)
    alpha = 1 - confidence_level

    port_ret = _portfolio_returns(returns, weights)
    mu = port_ret.mean()
    sigma = port_ret.std()

    # --- Normal variant ---
    z_alpha = stats.norm.ppf(alpha)
    normal_var = mu + z_alpha * sigma  # negative number for a loss
    # ES under normal: mu - sigma * phi(z_alpha) / alpha
    normal_es = mu - sigma * stats.norm.pdf(z_alpha) / alpha

    # --- Student-t variant ---
    df, t_loc, t_scale = stats.t.fit(port_ret.values)
    t_var = stats.t.ppf(alpha, df, loc=t_loc, scale=t_scale)
    # ES under Student-t: loc + scale * [ -t_pdf / alpha * (df + t_quantile^2) / (df - 1) ]
    t_quantile = stats.t.ppf(alpha, df)
    t_es = t_loc + t_scale * (
        -stats.t.pdf(t_quantile, df) / alpha * (df + t_quantile ** 2) / (df - 1)
    )

    # Scale and dollar amounts — use normal_var as the primary "portfolio_var"
    normal_var_scaled = normal_var * scale
    normal_es_scaled = normal_es * scale
    t_var_scaled = t_var * scale
    t_es_scaled = t_es * scale

    var_dollar = abs(normal_var_scaled) * portfolio_value
    es_dollar = abs(normal_es_scaled) * portfolio_value

    # Per-asset breakdown (normal only for simplicity/consistency)
    per_asset: dict = {}
    for asset in weights:
        if asset not in returns.columns:
            continue
        a_mu = returns[asset].mean()
        a_sigma = returns[asset].std()
        a_var = (a_mu + z_alpha * a_sigma) * scale
        a_es = (a_mu - a_sigma * stats.norm.pdf(z_alpha) / alpha) * scale
        per_asset[asset] = {
            "var": float(a_var),
            "es": float(a_es),
        }

    sorted_returns = np.sort(port_ret.values)

    return {
        "metrics": {
            "portfolio_var": float(normal_var_scaled),
            "portfolio_es": float(normal_es_scaled),
            "var_dollar": float(var_dollar),
            "es_dollar": float(es_dollar),
            "normal_var": float(normal_var_scaled),
            "t_var": float(t_var_scaled),
            "normal_es": float(normal_es_scaled),
            "t_es": float(t_es_scaled),
            "t_df": float(df),
            "per_asset": per_asset,
        },
        "data": {
            "sorted_returns": sorted_returns.tolist(),
            "var_line": float(normal_var_scaled),
            "es_line": float(normal_es_scaled),
            "histogram": _make_histogram(sorted_returns),
        },
    }


# ---------------------------------------------------------------------------
# 3. Monte Carlo VaR
# ---------------------------------------------------------------------------

def compute_monte_carlo_var(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Monte Carlo simulation Value-at-Risk.

    1. Estimate mean vector (mu) and covariance matrix (Sigma) from historical
       returns.
    2. Cholesky-decompose Sigma = L * L^T.
    3. Generate 10,000 correlated random return vectors: r = mu + L * z,
       where z ~ N(0, I).
    4. Compute portfolio return for each simulation using the given weights.
    5. VaR = percentile of simulated portfolio returns; ES = mean of tail.

    Uses numpy seed 42 for reproducibility.
    """
    confidence_level, time_horizon, weights, portfolio_value = _extract_config(config)
    scale = _scale_factor(time_horizon)
    alpha = 1 - confidence_level
    num_simulations = 10_000

    # Align assets between weights and returns columns
    assets = [a for a in weights if a in returns.columns]
    w = np.array([weights[a] for a in assets])
    ret_matrix = returns[assets]

    mu = ret_matrix.mean().values  # (n_assets,)
    cov = ret_matrix.cov().values  # (n_assets, n_assets)

    # Cholesky decomposition: Sigma = L @ L^T
    L = np.linalg.cholesky(cov)

    # Generate correlated random vectors
    rng = np.random.RandomState(42)
    z = rng.standard_normal((num_simulations, len(assets)))  # (N, n_assets)
    simulated_asset_returns = mu + z @ L.T  # (N, n_assets)

    # Portfolio returns for each simulation
    simulated_port_returns = simulated_asset_returns @ w  # (N,)

    # VaR and ES from simulated distribution
    var_pct = np.percentile(simulated_port_returns, alpha * 100)
    tail = simulated_port_returns[simulated_port_returns <= var_pct]
    es_pct = tail.mean() if len(tail) > 0 else var_pct

    # Scale
    var_scaled = var_pct * scale
    es_scaled = es_pct * scale
    var_dollar = abs(var_scaled) * portfolio_value
    es_dollar = abs(es_scaled) * portfolio_value

    sorted_sim = np.sort(simulated_port_returns)

    return {
        "metrics": {
            "portfolio_var": float(var_scaled),
            "portfolio_es": float(es_scaled),
            "var_dollar": float(var_dollar),
            "es_dollar": float(es_dollar),
            "num_simulations": num_simulations,
        },
        "data": {
            "simulated_returns": sorted_sim[:1000].tolist(),
            "var_line": float(var_scaled),
            "histogram": _make_histogram(sorted_sim),
        },
    }


# ---------------------------------------------------------------------------
# 4. VaR Summary / Comparison
# ---------------------------------------------------------------------------

def compute_var_summary(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Run all three VaR methodologies and return a combined comparison.

    Calls compute_historical_var, compute_parametric_var, and
    compute_monte_carlo_var, then assembles a side-by-side comparison
    suitable for charting.
    """
    hist = compute_historical_var(returns, metadata, config)
    para = compute_parametric_var(returns, metadata, config)
    mc = compute_monte_carlo_var(returns, metadata, config)

    # Build comparison chart data
    models = ["Historical", "Parametric (Normal)", "Parametric (Student-t)", "Monte Carlo"]
    var_values = [
        hist["metrics"]["portfolio_var"],
        para["metrics"]["normal_var"],
        para["metrics"]["t_var"],
        mc["metrics"]["portfolio_var"],
    ]
    es_values = [
        hist["metrics"]["portfolio_es"],
        para["metrics"]["normal_es"],
        para["metrics"]["t_es"],
        mc["metrics"]["portfolio_es"],
    ]

    return {
        "metrics": {
            "historical": hist["metrics"],
            "parametric_normal": {
                "portfolio_var": para["metrics"]["normal_var"],
                "portfolio_es": para["metrics"]["normal_es"],
                "var_dollar": abs(para["metrics"]["normal_var"])
                * config.get("portfolio_value", 10_000_000),
                "es_dollar": abs(para["metrics"]["normal_es"])
                * config.get("portfolio_value", 10_000_000),
                "per_asset": para["metrics"]["per_asset"],
            },
            "parametric_t": {
                "portfolio_var": para["metrics"]["t_var"],
                "portfolio_es": para["metrics"]["t_es"],
                "var_dollar": abs(para["metrics"]["t_var"])
                * config.get("portfolio_value", 10_000_000),
                "es_dollar": abs(para["metrics"]["t_es"])
                * config.get("portfolio_value", 10_000_000),
                "t_df": para["metrics"]["t_df"],
            },
            "monte_carlo": mc["metrics"],
        },
        "data": {
            "comparison_chart": {
                "models": models,
                "var_values": var_values,
                "es_values": es_values,
            },
        },
    }
