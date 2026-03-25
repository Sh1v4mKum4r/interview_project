"""
Advanced quantitative techniques for financial risk analysis.

Implements Taylor series (delta-gamma) approximation, Laplace transform-based
aggregate loss modelling, and Extreme Value Theory with Generalized Pareto
Distribution fitting.
"""

import numpy as np
import pandas as pd
from scipy.stats import genpareto, poisson, expon, norm, t as student_t


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _portfolio_returns(returns: pd.DataFrame, config: dict) -> np.ndarray:
    """Compute weighted portfolio returns from asset-level returns."""
    weights = config.get("weights", {})
    if not weights:
        # Equal-weight fallback
        cols = returns.columns.tolist()
        w = np.ones(len(cols)) / len(cols)
        return returns.values @ w

    # Align weights to DataFrame columns
    w = np.array([weights.get(col, 0.0) for col in returns.columns])
    total = w.sum()
    if total == 0:
        w = np.ones(len(returns.columns)) / len(returns.columns)
    else:
        w = w / total
    return returns.values @ w


def _underlying_name(derivative_name: str) -> str:
    """Extract the underlying asset name from a derivative name.

    Convention: ``AAPL_CALL`` -> ``AAPL``, ``MSFT_PUT_2024`` -> ``MSFT``.
    We split on ``_`` and take the first token.
    """
    return derivative_name.split("_")[0]


def _cornish_fisher_z(alpha: float, skew: float, excess_kurt: float) -> float:
    """Return the Cornish-Fisher adjusted quantile for a given confidence level.

    Parameters
    ----------
    alpha : float
        Confidence level (e.g. 0.95 or 0.99).
    skew : float
        Skewness of the distribution.
    excess_kurt : float
        Excess kurtosis of the distribution.
    """
    z = norm.ppf(alpha)
    z_cf = (
        z
        + (z ** 2 - 1) * skew / 6
        + (z ** 3 - 3 * z) * excess_kurt / 24
        - (2 * z ** 3 - 5 * z) * (skew ** 2) / 36
    )
    return z_cf


# ---------------------------------------------------------------------------
# 1. Taylor Series (Delta-Gamma) Approximation
# ---------------------------------------------------------------------------

def compute_taylor_series(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Delta-Gamma approximation for derivative portfolio risk.

    Returns a results dict with ``'data'`` (for charts) and ``'metrics'``
    (for summary).
    """
    confidence_level = config.get("confidence_level", 0.95)
    portfolio_value = config.get("portfolio_value", 10_000_000)
    derivatives = metadata.get("derivatives", {})

    per_derivative: dict = {}
    all_delta_pnl: list[np.ndarray] = []
    all_delta_gamma_pnl: list[np.ndarray] = []

    portfolio_delta_total = 0.0
    portfolio_gamma_total = 0.0

    for name, info in derivatives.items():
        underlying = _underlying_name(name)
        delta = info.get("delta", 0.0)
        gamma = info.get("gamma", 0.0)

        # Locate underlying returns in the DataFrame
        if underlying in returns.columns:
            underlying_returns = returns[underlying].values
        else:
            # Try case-insensitive match
            matched = [c for c in returns.columns if c.upper() == underlying.upper()]
            if matched:
                underlying_returns = returns[matched[0]].values
            else:
                # Skip this derivative if no matching column
                per_derivative[name] = {
                    "delta_var": 0.0,
                    "delta_gamma_var": 0.0,
                    "delta": delta,
                    "gamma": gamma,
                }
                continue

        # Compute underlying price series (initial price = 100, cumulative returns)
        cumulative = (1 + underlying_returns).cumprod()
        underlying_prices = 100.0 * cumulative
        last_price = underlying_prices[-1] if len(underlying_prices) > 0 else 100.0

        # Price changes: dS = S * r for each period
        dS = last_price * underlying_returns

        # P&L approximations
        delta_pnl = delta * dS
        delta_gamma_pnl = delta * dS + 0.5 * gamma * dS ** 2

        # Individual VaR (absolute value of loss at confidence level)
        delta_var_i = float(np.percentile(-delta_pnl, confidence_level * 100))
        delta_gamma_var_i = float(np.percentile(-delta_gamma_pnl, confidence_level * 100))

        per_derivative[name] = {
            "delta_var": delta_var_i,
            "delta_gamma_var": delta_gamma_var_i,
            "delta": delta,
            "gamma": gamma,
        }

        all_delta_pnl.append(delta_pnl)
        all_delta_gamma_pnl.append(delta_gamma_pnl)

        portfolio_delta_total += delta
        portfolio_gamma_total += gamma

    # Portfolio-level aggregation
    if all_delta_pnl:
        portfolio_delta_pnl = np.sum(all_delta_pnl, axis=0)
        portfolio_dg_pnl = np.sum(all_delta_gamma_pnl, axis=0)
    else:
        # No derivatives matched — use zeros matching return length
        n = len(returns)
        portfolio_delta_pnl = np.zeros(n)
        portfolio_dg_pnl = np.zeros(n)

    # Use portfolio-level returns for Cornish-Fisher approach
    port_ret = _portfolio_returns(returns, config)
    sigma = float(np.std(port_ret, ddof=1)) if len(port_ret) > 1 else 0.0

    # Cornish-Fisher expansion for delta-gamma VaR
    skew_dg = float(pd.Series(portfolio_dg_pnl).skew()) if len(portfolio_dg_pnl) > 2 else 0.0
    kurt_dg = float(pd.Series(portfolio_dg_pnl).kurtosis()) if len(portfolio_dg_pnl) > 3 else 0.0
    # Handle NaN from skew/kurtosis calculations
    if np.isnan(skew_dg):
        skew_dg = 0.0
    if np.isnan(kurt_dg):
        kurt_dg = 0.0

    z_cf = _cornish_fisher_z(confidence_level, skew_dg, kurt_dg)

    dg_std = float(np.std(portfolio_dg_pnl, ddof=1)) if len(portfolio_dg_pnl) > 1 else 0.0
    delta_std = float(np.std(portfolio_delta_pnl, ddof=1)) if len(portfolio_delta_pnl) > 1 else 0.0

    # Parametric VaR using Cornish-Fisher
    delta_gamma_var = float(z_cf * dg_std) if dg_std > 0 else 0.0
    delta_only_var = float(norm.ppf(confidence_level) * delta_std) if delta_std > 0 else 0.0
    gamma_correction = delta_gamma_var - delta_only_var

    # P&L distribution for charting
    hist_counts, hist_edges = np.histogram(portfolio_dg_pnl, bins=50)
    bin_centres = 0.5 * (hist_edges[:-1] + hist_edges[1:])

    # Per-derivative chart arrays
    deriv_names = list(per_derivative.keys())
    delta_var_values = [per_derivative[n]["delta_var"] for n in deriv_names]
    delta_gamma_var_values = [per_derivative[n]["delta_gamma_var"] for n in deriv_names]

    return {
        "metrics": {
            "delta_only_var": delta_only_var,
            "delta_gamma_var": delta_gamma_var,
            "gamma_correction": gamma_correction,
            "per_derivative": per_derivative,
        },
        "data": {
            "derivatives": deriv_names,
            "delta_var_values": delta_var_values,
            "delta_gamma_var_values": delta_gamma_var_values,
            "pnl_distribution": {
                "bins": bin_centres.tolist(),
                "counts": hist_counts.tolist(),
            },
        },
    }


# ---------------------------------------------------------------------------
# 2. Laplace Transforms — Aggregate Loss Distribution
# ---------------------------------------------------------------------------

def compute_laplace_transforms(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Aggregate loss distribution using moment generating functions.

    Models credit losses via a compound Poisson process with exponentially
    distributed severity, then obtains VaR / ES from the simulated aggregate
    loss distribution.
    """
    confidence_level = config.get("confidence_level", 0.95)
    portfolio_value = config.get("portfolio_value", 10_000_000)

    # Model parameters
    frequency_lambda = 5.0  # expected loss events per year
    severity_mean = portfolio_value * 0.01  # 1 % of portfolio

    # Analytical expected loss: E[S] = lambda * E[X]
    expected_loss = frequency_lambda * severity_mean

    # ----- Simulation of compound Poisson aggregate losses -----
    n_simulations = 10_000
    rng = np.random.default_rng(42)

    aggregate_losses = np.zeros(n_simulations)
    for i in range(n_simulations):
        n_events = rng.poisson(frequency_lambda)
        if n_events > 0:
            severities = rng.exponential(scale=severity_mean, size=n_events)
            aggregate_losses[i] = severities.sum()

    # VaR and ES from simulation
    aggregate_var_95 = float(np.percentile(aggregate_losses, 95))
    aggregate_var_99 = float(np.percentile(aggregate_losses, 99))

    # Expected Shortfall: mean of losses exceeding VaR
    losses_above_95 = aggregate_losses[aggregate_losses >= aggregate_var_95]
    losses_above_99 = aggregate_losses[aggregate_losses >= aggregate_var_99]
    aggregate_es_95 = float(losses_above_95.mean()) if len(losses_above_95) > 0 else aggregate_var_95
    aggregate_es_99 = float(losses_above_99.mean()) if len(losses_above_99) > 0 else aggregate_var_99

    # ----- MGF curve for charting -----
    # MGF of compound Poisson with exponential severity:
    #   M_S(t) = exp(lambda * (M_X(t) - 1))
    #   M_X(t) = 1 / (1 - t * mean_severity)   for t < 1/mean_severity
    t_max = 0.9 / severity_mean  # stay below singularity
    t_values = np.linspace(0, t_max, 200)
    mgf_values = np.exp(
        frequency_lambda * (1.0 / (1.0 - t_values * severity_mean) - 1.0)
    )

    # Distribution histogram
    hist_counts, hist_edges = np.histogram(aggregate_losses, bins=50)
    bin_centres = 0.5 * (hist_edges[:-1] + hist_edges[1:])

    return {
        "metrics": {
            "expected_loss": expected_loss,
            "aggregate_var_95": aggregate_var_95,
            "aggregate_var_99": aggregate_var_99,
            "aggregate_es_95": aggregate_es_95,
            "aggregate_es_99": aggregate_es_99,
            "frequency_lambda": frequency_lambda,
            "severity_mean": severity_mean,
        },
        "data": {
            "aggregate_loss_distribution": {
                "bins": bin_centres.tolist(),
                "counts": hist_counts.tolist(),
            },
            "var_lines": {
                "var_95": aggregate_var_95,
                "var_99": aggregate_var_99,
            },
            "mgf_curve": {
                "t_values": t_values.tolist(),
                "mgf_values": mgf_values.tolist(),
            },
        },
    }


# ---------------------------------------------------------------------------
# 3. Extreme Value Theory — Peaks-Over-Threshold with GPD
# ---------------------------------------------------------------------------

def compute_evt_gpd(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Extreme Value Theory using Peaks-Over-Threshold with Generalized Pareto
    Distribution fitting.
    """
    confidence_level = config.get("confidence_level", 0.95)
    portfolio_value = config.get("portfolio_value", 10_000_000)

    # Portfolio returns
    port_ret = _portfolio_returns(returns, config)

    # Work with losses (positive values represent losses)
    losses = -port_ret

    # Threshold at the 90th percentile of losses
    threshold = float(np.percentile(losses, 90))

    # Exceedances above the threshold
    exceedances = losses[losses > threshold] - threshold
    n_total = len(losses)
    n_exceedances = len(exceedances)

    # Fit GPD to the exceedances
    if n_exceedances > 2:
        # scipy genpareto parameterisation: shape c, loc, scale
        # We fix loc=0 since exceedances are already shifted
        shape_xi, loc_fit, scale_beta = genpareto.fit(exceedances, floc=0)
    else:
        shape_xi = 0.0
        loc_fit = 0.0
        scale_beta = float(np.std(exceedances)) if n_exceedances > 0 else 1.0

    # ----- Tail VaR using the semi-parametric formula -----
    # VaR_alpha = u + (beta / xi) * ((n / N_u * (1 - alpha))^(-xi) - 1)
    def _gpd_var(alpha: float) -> float:
        if abs(shape_xi) < 1e-10:
            # Limiting case xi -> 0: exponential tail
            return threshold + scale_beta * np.log(n_total / n_exceedances * (1 - alpha))
        ratio = (n_total / n_exceedances * (1 - alpha))
        return threshold + (scale_beta / shape_xi) * (ratio ** (-shape_xi) - 1)

    # ES_alpha = VaR_alpha / (1 - xi) + (beta - xi * u) / (1 - xi)
    def _gpd_es(alpha: float) -> float:
        var_alpha = _gpd_var(alpha)
        if abs(1 - shape_xi) < 1e-10:
            # Degenerate case
            return var_alpha
        return var_alpha / (1 - shape_xi) + (scale_beta - shape_xi * threshold) / (1 - shape_xi)

    tail_var_95 = float(_gpd_var(0.95))
    tail_var_99 = float(_gpd_var(0.99))
    tail_es_95 = float(_gpd_es(0.95))
    tail_es_99 = float(_gpd_es(0.99))

    # ----- Normal assumption VaR for comparison -----
    mu = float(np.mean(losses))
    sigma = float(np.std(losses, ddof=1)) if n_total > 1 else 1.0
    normal_var_95 = float(mu + sigma * norm.ppf(0.95))
    normal_var_99 = float(mu + sigma * norm.ppf(0.99))
    normal_es_95 = float(mu + sigma * norm.pdf(norm.ppf(0.95)) / (1 - 0.95))
    normal_es_99 = float(mu + sigma * norm.pdf(norm.ppf(0.99)) / (1 - 0.99))

    # ----- Data for charts -----
    # Fitted GPD PDF over exceedance range
    if n_exceedances > 0:
        x_range = np.linspace(0, float(exceedances.max()) * 1.2, 200)
        y_fitted = genpareto.pdf(x_range, shape_xi, loc=0, scale=scale_beta)
    else:
        x_range = np.linspace(0, 1, 200)
        y_fitted = np.zeros(200)

    # QQ-plot: empirical quantiles vs theoretical GPD quantiles
    if n_exceedances > 2:
        sorted_exc = np.sort(exceedances)
        empirical_quantiles = sorted_exc.tolist()
        # Theoretical quantiles from the fitted GPD
        probs = (np.arange(1, n_exceedances + 1) - 0.5) / n_exceedances
        theoretical_quantiles = genpareto.ppf(probs, shape_xi, loc=0, scale=scale_beta).tolist()
    else:
        empirical_quantiles = []
        theoretical_quantiles = []

    return {
        "metrics": {
            "gpd_shape_xi": float(shape_xi),
            "gpd_scale_beta": float(scale_beta),
            "threshold": threshold,
            "n_exceedances": int(n_exceedances),
            "tail_var_95": tail_var_95,
            "tail_var_99": tail_var_99,
            "tail_es_95": tail_es_95,
            "tail_es_99": tail_es_99,
            "normal_var_95": normal_var_95,
            "normal_var_99": normal_var_99,
        },
        "data": {
            "exceedances": exceedances.tolist() if n_exceedances > 0 else [],
            "fitted_gpd": {
                "x": x_range.tolist(),
                "y": y_fitted.tolist(),
            },
            "qq_plot": {
                "theoretical": theoretical_quantiles,
                "empirical": empirical_quantiles,
            },
            "tail_comparison": {
                "methods": ["GPD", "Normal"],
                "var_95": [tail_var_95, normal_var_95],
                "var_99": [tail_var_99, normal_var_99],
                "es_95": [tail_es_95, normal_es_95],
                "es_99": [tail_es_99, normal_es_99],
            },
        },
    }


# ---------------------------------------------------------------------------
# 4. Advanced Summary — Aggregate All Three Analyses
# ---------------------------------------------------------------------------

def compute_advanced_summary(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """Run all advanced analyses and return combined results."""
    taylor = compute_taylor_series(returns, metadata, config)
    laplace = compute_laplace_transforms(returns, metadata, config)
    evt = compute_evt_gpd(returns, metadata, config)

    return {
        "metrics": {
            "taylor_series": taylor["metrics"],
            "laplace_transforms": laplace["metrics"],
            "evt_gpd": evt["metrics"],
        },
        "data": {
            "taylor_series": taylor["data"],
            "laplace_transforms": laplace["data"],
            "evt_gpd": evt["data"],
        },
    }
