import type { RiskSummaryResult, ExposureResult } from '../types';

interface RiskSummaryCardProps {
  risk: RiskSummaryResult | undefined;
  exposure: ExposureResult | undefined;
}

function formatDollar(value: number | undefined): string {
  if (value === undefined || value === null) return '\u2014';
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(2)}`;
}

function formatPercent(value: number | undefined): string {
  if (value === undefined || value === null) return '\u2014';
  return `${(value * 100).toFixed(2)}%`;
}

function formatRatio(value: number | undefined): string {
  if (value === undefined || value === null) return '\u2014';
  return value.toFixed(3);
}

interface MetricCardProps {
  label: string;
  value: string;
  accent: string;
}

function MetricCard({ label, value, accent }: MetricCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col items-center justify-center">
      <div className={`w-1 h-8 rounded-full mb-3 ${accent}`} />
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-sm text-slate-500 mt-1">{label}</p>
    </div>
  );
}

export default function RiskSummaryCard({ risk, exposure }: RiskSummaryCardProps) {
  // Pick the first available model for the primary metrics
  const metrics = risk?.metrics;
  const primary =
    metrics?.historical ??
    metrics?.parametric_normal ??
    metrics?.parametric_t ??
    metrics?.monte_carlo;

  const varDollar = primary?.var_dollar;
  const esDollar = primary?.es_dollar;
  const portfolioVol = exposure?.metrics?.portfolio_volatility;

  // Compute a rough Sharpe from exposure data if possible
  // Sharpe = E[R] / sigma, but we only have vol. Use VaR as proxy indicator.
  const sharpe =
    portfolioVol !== undefined && portfolioVol > 0 && primary?.portfolio_var !== undefined
      ? primary.portfolio_var / portfolioVol
      : undefined;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <MetricCard
        label="Value at Risk"
        value={formatDollar(varDollar)}
        accent="bg-red-500"
      />
      <MetricCard
        label="Expected Shortfall"
        value={formatDollar(esDollar)}
        accent="bg-orange-500"
      />
      <MetricCard
        label="Portfolio Volatility"
        value={formatPercent(portfolioVol)}
        accent="bg-blue-500"
      />
      <MetricCard
        label="Sharpe Ratio"
        value={formatRatio(sharpe)}
        accent="bg-emerald-500"
      />
    </div>
  );
}
