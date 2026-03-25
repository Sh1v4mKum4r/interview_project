# Regulatory Framework Documentation

## 1. Basel III/IV

### What it is
Basel III is the international regulatory framework for banks, developed by the Basel Committee on Banking Supervision. It establishes minimum requirements for capital adequacy, leverage, and liquidity to ensure banks can absorb losses during financial stress. Basel IV (formally "Basel III: Finalised Reforms") tightened these rules further, particularly around risk-weighted assets and the shift from VaR to Expected Shortfall.

### Why it matters
After the 2008 financial crisis, regulators recognized that banks held insufficient capital against their risk exposures. Basel III requires banks to hold more—and higher quality—capital. Every financial institution must demonstrate compliance, and the metrics we compute (CET1, leverage, LCR) are reported to regulators quarterly.

### The math

#### Risk-Weighted Assets (Standardized Approach)

RWA represents the total exposure adjusted for risk. Higher-risk assets require more capital backing.

```
RWA = Σᵢ (Exposure_i × Risk_Weight_i)
```

Where Exposure_i = portfolio_value × weight_i, and risk weights are:

| Asset Class | Rating | Risk Weight |
|---|---|---|
| Equities | Any | 100% |
| Sovereign Bonds | AAA to AA | 0% |
| Sovereign Bonds | A | 20% |
| Sovereign Bonds | BBB | 50% |
| Sovereign Bonds | BB to B | 100% |
| Sovereign Bonds | Below B | 150% |
| Corporate Bonds | AAA to AA | 20% |
| Corporate Bonds | A | 50% |
| Corporate Bonds | BBB | 100% |
| Corporate Bonds | Below BBB | 150% |
| FX | Any | 8% of net open position |
| Derivatives | Any | Current Exposure Method |

**Derivatives — Current Exposure Method (CEM)**:
```
EAD = max(Market_Value, 0) + Notional × Add_on_Factor
```
Add-on factors: Equity = 8%, FX = 4%, Commodity = 10%

#### Capital Adequacy Ratios

```
CET1 Ratio = CET1 Capital / RWA       ≥ 4.5%  (minimum)
Tier 1 Ratio = Tier 1 Capital / RWA   ≥ 6.0%
Total Capital Ratio = Total Capital / RWA ≥ 8.0%
```

CET1 (Common Equity Tier 1) is the highest quality capital — common shares and retained earnings. Tier 1 adds Additional Tier 1 instruments (contingent convertible bonds). Total capital adds Tier 2 instruments (subordinated debt).

With conservation buffers, effective minimums are:
- CET1: 4.5% + 2.5% buffer = 7.0%
- Tier 1: 6.0% + 2.5% = 8.5%
- Total: 8.0% + 2.5% = 10.5%

#### Leverage Ratio
```
Leverage Ratio = Tier 1 Capital / Total Exposure ≥ 3%
```
Unlike capital ratios, this is NOT risk-weighted — it's a simple backstop against excessive leverage regardless of risk weighting.

#### Liquidity Coverage Ratio (LCR)
```
LCR = HQLA / Net Cash Outflows (30 days) ≥ 100%
```

High-Quality Liquid Assets (HQLA):
- **Level 1**: Cash, central bank reserves, sovereign bonds (0% haircut)
- **Level 2A**: Corporate bonds rated AA+ (15% haircut)
- **Level 2B**: Corporate bonds rated A to BBB (50% haircut)

Simplified net cash outflow = 5% of total portfolio value

#### FRTB (Fundamental Review of the Trading Book)

Basel IV's key market risk change: replace VaR with Expected Shortfall at 97.5% confidence.

```
ES₉₇.₅% = E[L | L > VaR₉₇.₅%] = Average loss in worst 2.5% of scenarios
```

Rationale: VaR tells you the minimum loss in the tail, but not how bad it gets. ES captures the full tail risk.

### Implementation
File: `backend/engine/regulatory.py`, function `compute_basel3()`
- RWA computed per asset class using standardized weights
- Capital ratios computed against configurable capital amounts
- Status thresholds: "pass" (above buffer), "amber" (above minimum but below buffer), "fail" (below minimum)
- LCR with simplified HQLA classification
- FRTB ES at 97.5% from portfolio returns

### Interpretation guide
- **CET1 Ratio 17%**: Well-capitalized — 4x the minimum. Buffer against losses.
- **Leverage Ratio 3.2% (amber)**: Just above minimum. Exposure is high relative to capital.
- **LCR 134%**: Sufficient liquidity for 30-day stress. Above 100% means the firm can meet obligations.
- **RWA breakdown**: Shows which asset classes consume the most regulatory capital.

### Demo talking points
- "Basel III ensures banks hold enough capital to absorb losses. Our CET1 ratio of 17% is well above the 4.5% minimum, but the amber leverage ratio at 3.2% shows the system correctly identifies that total exposure is high relative to Tier 1 capital."
- "Risk-weighted assets give different treatments to different assets. Sovereign bonds can have 0% weight (AAA-rated government debt is considered risk-free), while equities carry 100%. This drives which assets are 'capital-expensive.'"
- "The shift from VaR to Expected Shortfall under FRTB means regulators now care about the average loss in the tail, not just the entry point. This is a more complete picture of tail risk."

---

## 2. MiFID II

### What it is
MiFID II (Markets in Financial Instruments Directive II) is the European Union's regulatory framework for securities markets. It focuses on transparency, investor protection, and market structure. Key requirements include transaction reporting, best execution obligations, position limits on commodity derivatives, and pre/post-trade transparency.

### Why it matters
MiFID II applies to any firm trading European securities. Non-compliance carries significant fines. The framework promotes market integrity by requiring that transactions are reported, execution quality is monitored, and markets are transparent.

### Key Requirements

#### Transaction Reporting (RTS 25)
Every transaction must be reported to the relevant National Competent Authority with:
- Instrument identifier (ISIN)
- Price and quantity
- Execution venue (MIC code)
- Timestamp
- Buyer and seller identifiers (LEI codes)

#### Best Execution
Firms must take "all sufficient steps" to obtain the best possible result for clients. This requires:
- Monitoring execution quality across venues
- Comparing execution prices against benchmarks (VWAP, midpoint, etc.)
- Flagging deviations that exceed acceptable thresholds

We flag deviations > 1 standard deviation from VWAP.

#### Position Limits
Commodity derivative positions must not exceed regulatory limits designed to prevent market manipulation and ensure orderly price formation. We use a simplified threshold of 15% portfolio weight per commodity.

#### Pre/Post-Trade Transparency
- **Pre-trade**: Publish bid/ask quotes (estimated as 2 × volatility × price)
- **Post-trade**: Publish trade details (size, price) after execution

### Implementation
File: `backend/engine/regulatory.py`, function `compute_mifid2()`
- Generates 20 mock transactions with realistic fields
- VWAP-based best execution analysis
- Commodity position limit checks
- Pre/post-trade transparency report generation

### Demo talking points
- "MiFID II ensures market transparency and fair dealing. Our system generates the transaction reports that must be filed with regulators."
- "Best execution monitoring compares actual execution prices against VWAP benchmarks. Flags indicate where the firm may not have achieved optimal pricing."
- "Position limits on commodity derivatives prevent firms from taking outsized positions that could distort market prices."
