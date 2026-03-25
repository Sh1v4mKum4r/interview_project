"""
Synthetic financial data generator for multi-asset portfolio risk analysis.

Generates realistic correlated returns across equities, fixed income,
commodities, FX, and derivatives using appropriate stochastic models
for each asset class.
"""

import numpy as np
import pandas as pd
from scipy.stats import norm


# ---------------------------------------------------------------------------
# Asset universe definitions
# ---------------------------------------------------------------------------

EQUITY_TICKERS = ["AAPL", "MSFT", "GOOGL", "JPM", "GS", "BAC", "JNJ", "PFE", "XOM", "CVX"]

EQUITY_SECTORS = {
    "AAPL": "tech", "MSFT": "tech", "GOOGL": "tech",
    "JPM": "finance", "GS": "finance", "BAC": "finance",
    "JNJ": "healthcare", "PFE": "healthcare",
    "XOM": "energy", "CVX": "energy",
}

# Annualised volatility mid-points per sector (daily = annual / sqrt(252))
_SECTOR_VOL = {
    "tech": 0.30,
    "finance": 0.25,
    "healthcare": 0.20,
    "energy": 0.35,
}

# Per-ticker annual vol drawn from sector band
_EQUITY_ANNUAL_VOL = {
    "AAPL": 0.28, "MSFT": 0.26, "GOOGL": 0.33,
    "JPM": 0.23, "GS": 0.28, "BAC": 0.25,
    "JNJ": 0.17, "PFE": 0.23,
    "XOM": 0.32, "CVX": 0.38,
}

BOND_TICKERS = ["GOV_2Y", "GOV_10Y", "GOV_30Y", "CORP_5Y_A", "CORP_10Y_BBB"]

BOND_DURATIONS = {
    "GOV_2Y": 1.9,
    "GOV_10Y": 8.5,
    "GOV_30Y": 20.0,
    "CORP_5Y_A": 4.5,
    "CORP_10Y_BBB": 7.8,
}

BOND_RATINGS = {
    "GOV_2Y": "AAA",
    "GOV_10Y": "AAA",
    "GOV_30Y": "AAA",
    "CORP_5Y_A": "A",
    "CORP_10Y_BBB": "BBB",
}

COMMODITY_TICKERS = ["GOLD", "OIL", "NATGAS"]

# Ornstein-Uhlenbeck parameters {ticker: (theta, mu, sigma)}
_OU_PARAMS = {
    "GOLD":   (0.5, 0.0, 0.15),
    "OIL":    (0.3, 0.0, 0.35),
    "NATGAS": (0.4, 0.0, 0.45),
}

FX_TICKERS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF"]

# Annualised vol for each FX pair
_FX_ANNUAL_VOL = {
    "EURUSD": 0.09,
    "GBPUSD": 0.10,
    "USDJPY": 0.11,
    "USDCHF": 0.08,
}

DERIVATIVE_SPECS = {
    "AAPL_CALL": {
        "type": "call",
        "underlying": "AAPL",
        "strike": 150,
        "expiry": "2026-06-30",
    },
    "MSFT_PUT": {
        "type": "put",
        "underlying": "MSFT",
        "strike": 400,
        "expiry": "2026-09-30",
    },
    "XOM_CALL": {
        "type": "call",
        "underlying": "XOM",
        "strike": 110,
        "expiry": "2026-12-31",
    },
}


# ---------------------------------------------------------------------------
# Black-Scholes helpers
# ---------------------------------------------------------------------------

def _bs_d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Compute Black-Scholes d1."""
    return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))


def _bs_d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Compute Black-Scholes d2."""
    return _bs_d1(S, K, T, r, sigma) - sigma * np.sqrt(T)


def _bs_price(S: float, K: float, T: float, r: float, sigma: float,
              option_type: str) -> float:
    """Black-Scholes European option price."""
    d1 = _bs_d1(S, K, T, r, sigma)
    d2 = _bs_d2(S, K, T, r, sigma)
    if option_type == "call":
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def _bs_greeks(S: float, K: float, T: float, r: float, sigma: float,
               option_type: str) -> dict:
    """Compute delta, gamma, vega for a European option."""
    d1 = _bs_d1(S, K, T, r, sigma)
    d2 = _bs_d2(S, K, T, r, sigma)

    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # per 1% vol move

    if option_type == "call":
        delta = norm.cdf(d1)
    else:
        delta = norm.cdf(d1) - 1.0

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 4),
        "vega": round(vega, 4),
    }


# ---------------------------------------------------------------------------
# Correlation / covariance construction
# ---------------------------------------------------------------------------

def _build_equity_correlation(tickers: list) -> np.ndarray:
    """
    Build a realistic equity correlation matrix.

    Intra-sector ρ ≈ 0.6-0.8, cross-sector ρ ≈ 0.2-0.4.
    """
    n = len(tickers)
    corr = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            si = EQUITY_SECTORS[tickers[i]]
            sj = EQUITY_SECTORS[tickers[j]]
            if si == sj:
                rho = 0.70  # intra-sector mid-point
            else:
                rho = 0.30  # cross-sector mid-point
            corr[i, j] = rho
            corr[j, i] = rho
    return corr


def _build_equity_covariance(tickers: list) -> np.ndarray:
    """Daily covariance matrix for equities."""
    daily_vols = np.array([_EQUITY_ANNUAL_VOL[t] / np.sqrt(252) for t in tickers])
    corr = _build_equity_correlation(tickers)
    cov = np.outer(daily_vols, daily_vols) * corr
    return cov


# ---------------------------------------------------------------------------
# Per-asset-class generators
# ---------------------------------------------------------------------------

def _generate_equity_returns(dates: pd.DatetimeIndex,
                             rng: np.random.RandomState) -> pd.DataFrame:
    """Multivariate normal daily log-returns for equities."""
    n_days = len(dates)
    cov = _build_equity_covariance(EQUITY_TICKERS)
    mean = np.zeros(len(EQUITY_TICKERS))
    samples = rng.multivariate_normal(mean, cov, size=n_days)
    return pd.DataFrame(samples, index=dates, columns=EQUITY_TICKERS)


def _generate_bond_returns(dates: pd.DatetimeIndex,
                           rng: np.random.RandomState) -> pd.DataFrame:
    """
    Generate bond price returns from simulated yield changes.

    Yield changes are correlated across maturities and converted to price
    returns via duration approximation: ΔP/P ≈ -D · Δy.
    """
    n_days = len(dates)
    n_bonds = len(BOND_TICKERS)

    # Daily yield vol (annualised ~0.8-1.2% for govs, slightly higher for corp)
    daily_yield_vol = {
        "GOV_2Y": 0.006 / np.sqrt(252),
        "GOV_10Y": 0.008 / np.sqrt(252),
        "GOV_30Y": 0.010 / np.sqrt(252),
        "CORP_5Y_A": 0.009 / np.sqrt(252),
        "CORP_10Y_BBB": 0.012 / np.sqrt(252),
    }

    # Correlation among yield changes (high for similar maturities)
    corr = np.array([
        [1.00, 0.85, 0.70, 0.75, 0.65],  # GOV_2Y
        [0.85, 1.00, 0.90, 0.80, 0.75],  # GOV_10Y
        [0.70, 0.90, 1.00, 0.70, 0.70],  # GOV_30Y
        [0.75, 0.80, 0.70, 1.00, 0.85],  # CORP_5Y_A
        [0.65, 0.75, 0.70, 0.85, 1.00],  # CORP_10Y_BBB
    ])

    vols = np.array([daily_yield_vol[t] for t in BOND_TICKERS])
    cov = np.outer(vols, vols) * corr
    mean = np.zeros(n_bonds)

    yield_changes = rng.multivariate_normal(mean, cov, size=n_days)

    # Convert to price returns via duration
    durations = np.array([BOND_DURATIONS[t] for t in BOND_TICKERS])
    price_returns = -durations[np.newaxis, :] * yield_changes

    return pd.DataFrame(price_returns, index=dates, columns=BOND_TICKERS)


def _generate_commodity_returns(dates: pd.DatetimeIndex,
                                rng: np.random.RandomState) -> pd.DataFrame:
    """
    Ornstein-Uhlenbeck mean-reverting process for commodities.

    dX = theta * (mu - X) * dt + sigma * dW
    Returns are the discrete increments of the log-price process.
    """
    n_days = len(dates)
    dt = 1.0 / 252.0
    returns_dict = {}

    for ticker in COMMODITY_TICKERS:
        theta, mu, sigma = _OU_PARAMS[ticker]
        x = 0.0  # start at long-run mean
        daily_returns = []
        for _ in range(n_days):
            dw = rng.normal(0, np.sqrt(dt))
            dx = theta * (mu - x) * dt + sigma * dw
            daily_returns.append(dx)
            x += dx
        returns_dict[ticker] = daily_returns

    return pd.DataFrame(returns_dict, index=dates)


def _generate_fx_returns(dates: pd.DatetimeIndex,
                         rng: np.random.RandomState) -> pd.DataFrame:
    """Correlated FX returns with low equity correlation."""
    n_days = len(dates)
    n_fx = len(FX_TICKERS)

    daily_vols = np.array([_FX_ANNUAL_VOL[t] / np.sqrt(252) for t in FX_TICKERS])

    # FX inter-pair correlations
    corr = np.array([
        [1.00, 0.60, -0.30, -0.50],  # EURUSD
        [0.60, 1.00, -0.20, -0.40],  # GBPUSD
        [-0.30, -0.20, 1.00, 0.40],  # USDJPY
        [-0.50, -0.40, 0.40, 1.00],  # USDCHF
    ])

    cov = np.outer(daily_vols, daily_vols) * corr
    mean = np.zeros(n_fx)
    samples = rng.multivariate_normal(mean, cov, size=n_days)

    return pd.DataFrame(samples, index=dates, columns=FX_TICKERS)


def _generate_derivative_returns(equity_returns: pd.DataFrame,
                                 equity_prices: pd.DataFrame,
                                 rng: np.random.RandomState) -> tuple:
    """
    Generate derivative returns via delta approximation of the underlying.

    Also compute Black-Scholes Greeks at the initial underlying price.

    Returns:
        (returns_df, derivatives_metadata)
    """
    r = 0.05  # risk-free rate assumption
    end_date = equity_prices.index[-1]
    derivatives_meta = {}
    returns_dict = {}

    for deriv_ticker, spec in DERIVATIVE_SPECS.items():
        underlying = spec["underlying"]
        strike = spec["strike"]
        expiry_date = pd.Timestamp(spec["expiry"])
        option_type = spec["type"]

        S0 = equity_prices[underlying].iloc[0]
        T0 = max((expiry_date - equity_prices.index[0]).days / 365.0, 0.01)
        sigma = _EQUITY_ANNUAL_VOL[underlying]

        # Compute Greeks at initial point
        greeks = _bs_greeks(S0, strike, T0, r, sigma, option_type)

        derivatives_meta[deriv_ticker] = {
            "type": option_type,
            "strike": strike,
            "expiry": spec["expiry"],
            "delta": greeks["delta"],
            "gamma": greeks["gamma"],
            "vega": greeks["vega"],
        }

        # Delta approximation: option return ≈ delta * (dS/S) * (S/V)
        # For simplicity, use delta * underlying_return as the option log-return
        # scaled by leverage factor (S / option_price)
        option_price = _bs_price(S0, strike, T0, r, sigma, option_type)
        leverage = S0 / max(option_price, 0.01)

        underlying_returns = equity_returns[underlying].values
        option_returns = greeks["delta"] * underlying_returns * leverage
        returns_dict[deriv_ticker] = option_returns

    dates = equity_returns.index
    returns_df = pd.DataFrame(returns_dict, index=dates)
    return returns_df, derivatives_meta


# ---------------------------------------------------------------------------
# Price reconstruction
# ---------------------------------------------------------------------------

# Reference starting prices (approximate real-world levels)
_STARTING_PRICES = {
    "AAPL": 175.0, "MSFT": 420.0, "GOOGL": 155.0,
    "JPM": 195.0, "GS": 450.0, "BAC": 38.0,
    "JNJ": 155.0, "PFE": 28.0,
    "XOM": 110.0, "CVX": 155.0,
    "GOV_2Y": 100.0, "GOV_10Y": 100.0, "GOV_30Y": 100.0,
    "CORP_5Y_A": 100.0, "CORP_10Y_BBB": 100.0,
    "GOLD": 2050.0, "OIL": 78.0, "NATGAS": 3.20,
    "EURUSD": 1.085, "GBPUSD": 1.270, "USDJPY": 150.5, "USDCHF": 0.880,
}


def _returns_to_prices(returns: pd.DataFrame) -> pd.DataFrame:
    """Convert log-returns to price levels using reference starting prices."""
    prices = pd.DataFrame(index=returns.index, columns=returns.columns, dtype=float)
    for col in returns.columns:
        s0 = _STARTING_PRICES.get(col, 100.0)
        cum_log_ret = returns[col].cumsum()
        prices[col] = s0 * np.exp(cum_log_ret)
    return prices


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_synthetic_data(num_days: int = 252, seed: int = 42) -> dict:
    """
    Generate synthetic multi-asset portfolio data for risk analysis.

    Parameters
    ----------
    num_days : int
        Number of trading days to simulate (default 252, ~1 year).
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict with keys:
        - "returns": pd.DataFrame of daily log-returns (dates x assets)
        - "prices": pd.DataFrame of price levels (dates x assets)
        - "metadata": dict with asset_classes, sectors, ratings, derivatives
    """
    rng = np.random.RandomState(seed)

    # Business-day date range ending 2026-03-31
    end_date = pd.Timestamp("2026-03-31")
    dates = pd.bdate_range(end=end_date, periods=num_days, freq="B")

    # --- Generate returns per asset class ---
    equity_ret = _generate_equity_returns(dates, rng)
    bond_ret = _generate_bond_returns(dates, rng)
    commodity_ret = _generate_commodity_returns(dates, rng)
    fx_ret = _generate_fx_returns(dates, rng)

    # Combine non-derivative returns to build price series first
    base_returns = pd.concat([equity_ret, bond_ret, commodity_ret, fx_ret], axis=1)
    base_prices = _returns_to_prices(base_returns)

    # Derivatives need underlying prices
    deriv_ret, deriv_meta = _generate_derivative_returns(
        equity_ret, base_prices, rng
    )

    # Combine all returns and prices
    all_returns = pd.concat([base_returns, deriv_ret], axis=1)

    # For derivative prices, compute from starting option price + cumulative returns
    r = 0.05
    deriv_prices = pd.DataFrame(index=dates, dtype=float)
    for deriv_ticker, spec in DERIVATIVE_SPECS.items():
        underlying = spec["underlying"]
        S0 = base_prices[underlying].iloc[0]
        T0 = max((pd.Timestamp(spec["expiry"]) - dates[0]).days / 365.0, 0.01)
        sigma = _EQUITY_ANNUAL_VOL[underlying]
        option_price_0 = _bs_price(S0, spec["strike"], T0, r, sigma, spec["type"])
        cum_log_ret = deriv_ret[deriv_ticker].cumsum()
        deriv_prices[deriv_ticker] = option_price_0 * np.exp(cum_log_ret)

    all_prices = pd.concat([base_prices, deriv_prices], axis=1)

    # --- Build metadata ---
    asset_classes = {}
    for t in EQUITY_TICKERS:
        asset_classes[t] = "equity"
    for t in BOND_TICKERS:
        asset_classes[t] = "fixed_income"
    for t in COMMODITY_TICKERS:
        asset_classes[t] = "commodity"
    for t in FX_TICKERS:
        asset_classes[t] = "fx"
    for t in DERIVATIVE_SPECS:
        asset_classes[t] = "derivative"

    sectors = dict(EQUITY_SECTORS)

    ratings = dict(BOND_RATINGS)

    metadata = {
        "asset_classes": asset_classes,
        "sectors": sectors,
        "ratings": ratings,
        "derivatives": deriv_meta,
    }

    return {
        "returns": all_returns,
        "prices": all_prices,
        "metadata": metadata,
    }


def generate_portfolio_weights(metadata: dict) -> dict:
    """
    Generate equal weights across all non-derivative assets, normalised to sum to 1.

    Parameters
    ----------
    metadata : dict
        The metadata dict from generate_synthetic_data output.

    Returns
    -------
    dict
        Mapping of asset ticker to portfolio weight.
    """
    non_deriv_assets = [
        asset for asset, ac in metadata["asset_classes"].items()
        if ac != "derivative"
    ]
    n = len(non_deriv_assets)
    weight = 1.0 / n if n > 0 else 0.0
    return {asset: weight for asset in non_deriv_assets}


# ---------------------------------------------------------------------------
# CLI entry point for quick sanity checks
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    data = generate_synthetic_data()
    print("Returns shape:", data["returns"].shape)
    print("Prices shape:", data["prices"].shape)
    print("\nAsset classes:", data["metadata"]["asset_classes"])
    print("\nSectors:", data["metadata"]["sectors"])
    print("\nRatings:", data["metadata"]["ratings"])
    print("\nDerivatives:")
    for k, v in data["metadata"]["derivatives"].items():
        print(f"  {k}: {v}")

    weights = generate_portfolio_weights(data["metadata"])
    print(f"\nPortfolio weights ({len(weights)} assets, sum={sum(weights.values()):.4f}):")
    for asset, w in weights.items():
        print(f"  {asset}: {w:.4f}")

    print("\nSample returns (first 5 days, first 5 assets):")
    print(data["returns"].iloc[:5, :5].to_string())
    print("\nSample prices (first 5 days, first 5 assets):")
    print(data["prices"].iloc[:5, :5].to_string())
