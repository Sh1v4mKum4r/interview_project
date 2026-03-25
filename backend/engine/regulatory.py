"""
Regulatory framework module for financial risk analysis.

Implements Basel III capital adequacy, FRTB, LCR, MiFID II transaction
reporting, best execution, position limits, and transparency checks.
"""

import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta
import random
import string


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_config_defaults(config: dict) -> tuple:
    """Extract portfolio_value, confidence_level, and capital from config."""
    weights = config.get("weights", {})
    portfolio_value = config.get("portfolio_value", 10_000_000)
    confidence_level = config.get("confidence_level", 0.99)
    capital = config.get("capital", {})
    cet1 = capital.get("cet1", 1_200_000)
    tier1 = capital.get("tier1", 1_500_000)
    total_cap = capital.get("total", 2_000_000)
    return weights, portfolio_value, confidence_level, cet1, tier1, total_cap


def _status(value: float, green_threshold: float, amber_threshold: float,
            higher_is_better: bool = True) -> str:
    """Return 'pass', 'amber', or 'fail' based on thresholds.

    For higher_is_better=True (ratios that must exceed a minimum):
        value >= amber_threshold  -> 'pass'
        value >= green_threshold  -> 'amber'
        value <  green_threshold  -> 'fail'
    """
    if higher_is_better:
        if value >= amber_threshold:
            return "pass"
        elif value >= green_threshold:
            return "amber"
        else:
            return "fail"
    else:
        if value <= green_threshold:
            return "pass"
        elif value <= amber_threshold:
            return "amber"
        else:
            return "fail"


def _sovereign_risk_weight(rating: str) -> float:
    """Basel III standardized risk weight for sovereign bonds."""
    rating = rating.upper()
    if rating in ("AAA", "AA"):
        return 0.0
    elif rating == "A":
        return 0.20
    elif rating == "BBB":
        return 0.50
    elif rating in ("BB", "B"):
        return 1.00
    else:  # CCC and below
        return 1.50


def _corporate_risk_weight(rating: str) -> float:
    """Basel III standardized risk weight for corporate bonds."""
    rating = rating.upper()
    if rating in ("AAA", "AA"):
        return 0.20
    elif rating == "A":
        return 0.50
    elif rating in ("BBB",):
        return 1.00
    elif rating in ("BB", "B"):
        return 1.00
    else:  # CCC and below
        return 1.50


def _mock_isin() -> str:
    """Generate a mock ISIN (2-letter country + 9 alphanum + 1 check)."""
    country = random.choice(["US", "GB", "DE", "FR", "NL"])
    body = "".join(random.choices(string.ascii_uppercase + string.digits, k=9))
    check = str(random.randint(0, 9))
    return f"{country}{body}{check}"


def _mock_lei() -> str:
    """Generate a mock LEI (20-character alphanumeric)."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=20))


# ---------------------------------------------------------------------------
# 1. Basel III
# ---------------------------------------------------------------------------

def compute_basel3(returns: pd.DataFrame, metadata: dict, config: dict) -> dict:
    """
    Compute Basel III regulatory metrics.

    Returns a results dict with 'data' (for charts) and 'metrics' (for summary).
    """
    weights, portfolio_value, confidence_level, cet1, tier1, total_cap = (
        _get_config_defaults(config)
    )

    asset_classes = metadata.get("asset_classes", {})
    ratings = metadata.get("ratings", {})
    derivatives_meta = metadata.get("derivatives", {})

    # ------------------------------------------------------------------
    # Risk-Weighted Assets (Standardized Approach)
    # ------------------------------------------------------------------
    rwa_breakdown: dict[str, float] = {}
    total_rwa = 0.0
    total_exposure = 0.0

    for asset, weight in weights.items():
        exposure = portfolio_value * weight
        total_exposure += exposure
        ac = asset_classes.get(asset, "equity")
        rating = ratings.get(asset, "BBB")

        if ac == "equity":
            rw = 1.00
        elif ac == "fixed_income":
            # Determine if sovereign or corporate.  Sovereign names typically
            # contain keywords; for generality we treat assets with AAA/AA
            # sovereign-style.  A simple heuristic: if the name contains
            # common sovereign keywords we treat it as sovereign; otherwise
            # corporate.
            name_lower = asset.lower()
            is_sovereign = any(
                kw in name_lower
                for kw in ["treasury", "govt", "government", "sovereign",
                            "gilt", "bund", "oat", "jgb", "t-bill", "tbill"]
            )
            if is_sovereign:
                rw = _sovereign_risk_weight(rating)
            else:
                rw = _corporate_risk_weight(rating)
        elif ac == "commodity":
            rw = 1.00
        elif ac == "fx":
            # FX: 8% of notional (net open position)
            rw = 0.08
        elif ac == "derivative":
            # Current Exposure Method
            deriv_info = derivatives_meta.get(asset, {})
            # Market value proxy: use delta * exposure as replacement cost
            delta = deriv_info.get("delta", 0.5)
            market_value = delta * exposure
            replacement_cost = max(market_value, 0)

            # PFE add-on factor by underlying type
            # We determine underlying type from derivative metadata or name
            deriv_type = deriv_info.get("underlying_class", "")
            if not deriv_type:
                # Infer from name
                name_lower = asset.lower()
                if any(k in name_lower for k in ["fx", "currency", "eur", "usd", "gbp", "jpy"]):
                    deriv_type = "fx"
                elif any(k in name_lower for k in ["commodity", "oil", "gold", "wheat"]):
                    deriv_type = "commodity"
                else:
                    deriv_type = "equity"

            add_on_factors = {"equity": 0.08, "fx": 0.04, "commodity": 0.10}
            add_on_factor = add_on_factors.get(deriv_type, 0.08)
            pfe = exposure * add_on_factor

            ead = replacement_cost + pfe
            # Derivatives get 100% risk weight on the computed EAD
            rw_amount = ead
            rwa_breakdown[ac] = rwa_breakdown.get(ac, 0.0) + rw_amount
            total_rwa += rw_amount
            continue  # skip the common path below
        else:
            rw = 1.00

        rw_amount = exposure * rw
        rwa_breakdown[ac] = rwa_breakdown.get(ac, 0.0) + rw_amount
        total_rwa += rw_amount

    # Guard against zero RWA
    if total_rwa == 0:
        total_rwa = 1.0

    # ------------------------------------------------------------------
    # Capital Adequacy Ratios
    # ------------------------------------------------------------------
    cet1_ratio = cet1 / total_rwa
    tier1_ratio = tier1 / total_rwa
    total_capital_ratio = total_cap / total_rwa

    cet1_status = _status(cet1_ratio, 0.045, 0.07)
    tier1_status = _status(tier1_ratio, 0.06, 0.085)
    total_capital_status = _status(total_capital_ratio, 0.08, 0.105)

    # ------------------------------------------------------------------
    # Leverage Ratio
    # ------------------------------------------------------------------
    if total_exposure == 0:
        total_exposure = 1.0
    leverage_ratio = tier1 / total_exposure
    leverage_status = _status(leverage_ratio, 0.03, 0.04)

    # ------------------------------------------------------------------
    # LCR (simplified)
    # ------------------------------------------------------------------
    hqla = 0.0
    for asset, weight in weights.items():
        ac = asset_classes.get(asset, "equity")
        rating = ratings.get(asset, "BBB")
        exposure = portfolio_value * weight

        if ac == "fixed_income":
            name_lower = asset.lower()
            is_sovereign = any(
                kw in name_lower
                for kw in ["treasury", "govt", "government", "sovereign",
                            "gilt", "bund", "oat", "jgb", "t-bill", "tbill"]
            )
            if is_sovereign:
                # Level 1 HQLA — 0% haircut
                hqla += exposure * 1.0
            elif rating.upper() in ("AAA", "AA"):
                # Level 2A HQLA — 15% haircut
                hqla += exposure * 0.85
            elif rating.upper() in ("A", "BBB"):
                # Level 2B HQLA — 50% haircut
                hqla += exposure * 0.50

    net_cash_outflow = 0.05 * portfolio_value
    if net_cash_outflow == 0:
        net_cash_outflow = 1.0
    lcr = hqla / net_cash_outflow
    lcr_status = _status(lcr, 1.00, 1.20)

    # ------------------------------------------------------------------
    # FRTB — Expected Shortfall at 97.5% confidence
    # ------------------------------------------------------------------
    if returns.empty:
        frtb_es = 0.0
    else:
        portfolio_returns = (returns * pd.Series(weights)).sum(axis=1)
        portfolio_returns = portfolio_returns.dropna()
        if len(portfolio_returns) == 0:
            frtb_es = 0.0
        else:
            es_quantile = 0.025  # 97.5% confidence -> 2.5% tail
            threshold = np.percentile(portfolio_returns, es_quantile * 100)
            tail = portfolio_returns[portfolio_returns <= threshold]
            if len(tail) == 0:
                frtb_es = abs(threshold) * portfolio_value
            else:
                frtb_es = abs(tail.mean()) * portfolio_value

    # ------------------------------------------------------------------
    # Build output
    # ------------------------------------------------------------------
    classes_list = sorted(rwa_breakdown.keys())
    values_list = [rwa_breakdown[c] for c in classes_list]

    ratio_names = ["CET1", "Tier 1", "Total Capital", "Leverage", "LCR"]
    ratio_values = [cet1_ratio, tier1_ratio, total_capital_ratio,
                    leverage_ratio, lcr]
    ratio_thresholds = [0.045, 0.06, 0.08, 0.03, 1.00]
    ratio_statuses = [cet1_status, tier1_status, total_capital_status,
                      leverage_status, lcr_status]

    metrics = {
        "rwa": total_rwa,
        "rwa_breakdown": rwa_breakdown,
        "cet1_ratio": cet1_ratio,
        "cet1_status": cet1_status,
        "tier1_ratio": tier1_ratio,
        "tier1_status": tier1_status,
        "total_capital_ratio": total_capital_ratio,
        "total_capital_status": total_capital_status,
        "leverage_ratio": leverage_ratio,
        "leverage_status": leverage_status,
        "lcr": lcr,
        "lcr_status": lcr_status,
        "frtb_es": frtb_es,
    }

    data = {
        "rwa_by_class": {
            "classes": classes_list,
            "values": values_list,
        },
        "capital_ratios": {
            "ratios": ratio_names,
            "values": ratio_values,
            "thresholds": ratio_thresholds,
            "statuses": ratio_statuses,
        },
    }

    return {"metrics": metrics, "data": data}


# ---------------------------------------------------------------------------
# 2. MiFID II
# ---------------------------------------------------------------------------

def compute_mifid2(returns: pd.DataFrame, metadata: dict, config: dict) -> dict:
    """
    Compute MiFID II regulatory metrics.

    Returns a results dict with 'data' (for charts) and 'metrics' (for summary).
    """
    weights, portfolio_value, confidence_level, _, _, _ = (
        _get_config_defaults(config)
    )

    asset_classes = metadata.get("asset_classes", {})
    assets = list(weights.keys())

    # ------------------------------------------------------------------
    # Transaction Reporting (mock RTS 25) — 20 sample transactions
    # ------------------------------------------------------------------
    venues = ["XLON", "XPAR", "XAMS", "XFRA"]
    transactions = []
    base_time = datetime(2026, 3, 31, 9, 0, 0)

    for i in range(20):
        asset = assets[i % len(assets)] if assets else "UNKNOWN"
        weight = weights.get(asset, 0.0)
        exposure = portfolio_value * weight

        # Derive a mock price and quantity
        if asset in returns.columns and len(returns[asset].dropna()) > 0:
            vol = returns[asset].std()
        else:
            vol = 0.01

        base_price = 100.0 * (1 + weight)  # simple proxy
        price = round(base_price * (1 + np.random.normal(0, vol)), 4)
        if price <= 0:
            price = base_price
        quantity = max(1, int(exposure / price)) if price > 0 else 1

        txn = {
            "instrument_isin": _mock_isin(),
            "asset": asset,
            "price": round(price, 4),
            "quantity": quantity,
            "venue_mic": random.choice(venues),
            "timestamp": (base_time + timedelta(minutes=i * 23)).isoformat(),
            "buyer_lei": _mock_lei(),
            "seller_lei": _mock_lei(),
        }
        transactions.append(txn)

    # ------------------------------------------------------------------
    # Best Execution
    # ------------------------------------------------------------------
    best_execution: dict[str, dict] = {}
    best_execution_flags = 0

    for asset in assets:
        # Compute VWAP proxy from generated transactions for this asset
        asset_txns = [t for t in transactions if t["asset"] == asset]
        if asset_txns:
            prices = [t["price"] for t in asset_txns]
            quantities = [t["quantity"] for t in asset_txns]
            total_value = sum(p * q for p, q in zip(prices, quantities))
            total_qty = sum(quantities)
            vwap = total_value / total_qty if total_qty > 0 else prices[0]
            last_price = prices[-1]
        else:
            # Fallback: use returns-based proxy
            if asset in returns.columns and len(returns[asset].dropna()) > 0:
                mean_ret = returns[asset].mean()
                vwap = 100.0 * (1 + mean_ret)
                last_price = 100.0 * (1 + returns[asset].iloc[-1])
            else:
                vwap = 100.0
                last_price = 100.0

        # Standard deviation of transaction prices or returns
        if asset in returns.columns and len(returns[asset].dropna()) > 1:
            price_std = returns[asset].std() * 100.0  # scale to price level
        else:
            price_std = 1.0

        if price_std == 0:
            price_std = 1.0

        deviation = abs(last_price - vwap)
        deviation_sigma = deviation / price_std
        flagged = deviation_sigma > 1.0

        if flagged:
            best_execution_flags += 1

        best_execution[asset] = {
            "vwap": round(vwap, 4),
            "last_price": round(last_price, 4),
            "deviation_sigma": round(deviation_sigma, 4),
            "flagged": flagged,
        }

    # ------------------------------------------------------------------
    # Position Limits (commodity derivatives only)
    # ------------------------------------------------------------------
    position_limits: dict[str, dict] = {}
    position_limit_breaches: list[str] = []

    for asset in assets:
        ac = asset_classes.get(asset, "equity")
        if ac == "commodity":
            w = weights.get(asset, 0.0)
            breached = w > 0.15
            position_limits[asset] = {
                "weight": round(w, 4),
                "threshold": 0.15,
                "breached": breached,
            }
            if breached:
                position_limit_breaches.append(asset)

    # ------------------------------------------------------------------
    # Transparency Reports
    # ------------------------------------------------------------------
    pre_trade: dict[str, dict] = {}
    post_trade: dict[str, dict] = {}

    for asset in assets:
        weight = weights.get(asset, 0.0)
        exposure = portfolio_value * weight

        if asset in returns.columns and len(returns[asset].dropna()) > 1:
            vol = returns[asset].std()
        else:
            vol = 0.01

        base_price = 100.0 * (1 + weight)
        bid_ask_spread = round(2 * vol * base_price, 4)

        pre_trade[asset] = {"bid_ask_spread": bid_ask_spread}

        # Post-trade: last generated transaction for this asset
        asset_txns = [t for t in transactions if t["asset"] == asset]
        if asset_txns:
            last_txn = asset_txns[-1]
            post_trade[asset] = {
                "trade_size": float(last_txn["quantity"]),
                "price": float(last_txn["price"]),
            }
        else:
            post_trade[asset] = {
                "trade_size": 0.0,
                "price": base_price,
            }

    # Count transparency issues: assets with very wide spreads (> 5% of price)
    transparency_issues = 0
    for asset, pt in pre_trade.items():
        base_price = 100.0 * (1 + weights.get(asset, 0.0))
        if base_price > 0 and pt["bid_ask_spread"] / base_price > 0.05:
            transparency_issues += 1

    # ------------------------------------------------------------------
    # Build output
    # ------------------------------------------------------------------
    metrics = {
        "transaction_count": len(transactions),
        "best_execution_flags": best_execution_flags,
        "position_limit_breaches": position_limit_breaches,
        "transparency_issues": transparency_issues,
    }

    data = {
        "transactions": transactions,
        "best_execution": best_execution,
        "position_limits": position_limits,
        "transparency": {
            "pre_trade": pre_trade,
            "post_trade": post_trade,
        },
    }

    return {"metrics": metrics, "data": data}


# ---------------------------------------------------------------------------
# 3. Regulatory Summary
# ---------------------------------------------------------------------------

def compute_regulatory_summary(
    returns: pd.DataFrame,
    metadata: dict,
    config: dict,
) -> dict:
    """
    Unified regulatory report combining Basel III and MiFID II.

    Returns a results dict with 'data' (for charts) and 'metrics' (for summary).
    """
    basel3_result = compute_basel3(returns, metadata, config)
    mifid2_result = compute_mifid2(returns, metadata, config)

    b3m = basel3_result["metrics"]
    m2m = mifid2_result["metrics"]

    # ------------------------------------------------------------------
    # Overall compliance status
    # ------------------------------------------------------------------
    all_statuses = [
        b3m["cet1_status"],
        b3m["tier1_status"],
        b3m["total_capital_status"],
        b3m["leverage_status"],
        b3m["lcr_status"],
    ]

    has_fail = any(s == "fail" for s in all_statuses)
    has_amber = any(s == "amber" for s in all_statuses)

    # MiFID II breaches also count as failures
    if m2m["position_limit_breaches"]:
        has_fail = True
    if m2m["best_execution_flags"] > 0:
        has_amber = True

    if has_fail:
        overall_status = "breach"
    elif has_amber:
        overall_status = "warning"
    else:
        overall_status = "compliant"

    # ------------------------------------------------------------------
    # Summary table
    # ------------------------------------------------------------------
    summary_table = [
        {
            "metric": "CET1 Ratio",
            "value": b3m["cet1_ratio"],
            "threshold": 0.045,
            "status": b3m["cet1_status"],
        },
        {
            "metric": "Tier 1 Ratio",
            "value": b3m["tier1_ratio"],
            "threshold": 0.06,
            "status": b3m["tier1_status"],
        },
        {
            "metric": "Total Capital Ratio",
            "value": b3m["total_capital_ratio"],
            "threshold": 0.08,
            "status": b3m["total_capital_status"],
        },
        {
            "metric": "Leverage Ratio",
            "value": b3m["leverage_ratio"],
            "threshold": 0.03,
            "status": b3m["leverage_status"],
        },
        {
            "metric": "LCR",
            "value": b3m["lcr"],
            "threshold": 1.00,
            "status": b3m["lcr_status"],
        },
        {
            "metric": "FRTB Expected Shortfall",
            "value": b3m["frtb_es"],
            "threshold": 0.0,  # informational
            "status": "info",
        },
        {
            "metric": "Best Execution Flags",
            "value": float(m2m["best_execution_flags"]),
            "threshold": 0.0,
            "status": "pass" if m2m["best_execution_flags"] == 0 else "amber",
        },
        {
            "metric": "Position Limit Breaches",
            "value": float(len(m2m["position_limit_breaches"])),
            "threshold": 0.0,
            "status": "pass" if not m2m["position_limit_breaches"] else "fail",
        },
        {
            "metric": "Transparency Issues",
            "value": float(m2m["transparency_issues"]),
            "threshold": 0.0,
            "status": "pass" if m2m["transparency_issues"] == 0 else "amber",
        },
    ]

    # ------------------------------------------------------------------
    # Build output
    # ------------------------------------------------------------------
    metrics = {
        "overall_status": overall_status,
        "basel3": b3m,
        "mifid2": m2m,
    }

    data = {
        "basel3": basel3_result["data"],
        "mifid2": mifid2_result["data"],
        "summary_table": summary_table,
    }

    return {"metrics": metrics, "data": data}
