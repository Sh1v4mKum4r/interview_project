import type { AdvancedResult } from '../types';

interface AdvancedPanelProps {
  data: AdvancedResult | undefined;
}

function formatValue(val: any): string {
  if (val === undefined || val === null) return 'N/A';
  if (typeof val !== 'number') return String(val);
  if (Math.abs(val) >= 1_000_000) return `$${(val / 1_000_000).toFixed(2)}M`;
  if (Math.abs(val) >= 1_000) return `$${(val / 1_000).toFixed(1)}K`;
  if (Math.abs(val) < 0.0001 && val !== 0) return val.toExponential(2);
  return val.toFixed(4);
}

export default function AdvancedPanel({ data }: AdvancedPanelProps) {
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4">
          Advanced Quantitative Techniques
        </h3>
        <p className="text-slate-400 text-sm">Loading advanced metrics...</p>
      </div>
    );
  }

  const { taylor_series, laplace_transforms, evt_gpd } = data.metrics as any;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-6">
        Advanced Quantitative Techniques
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Taylor Series / Delta-Gamma */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-indigo-500"></div>
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Taylor Series (Delta-Gamma)
            </h4>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-end border-b border-slate-50 pb-1">
              <span className="text-xs text-slate-500">Delta-only VaR</span>
              <span className="text-sm font-mono font-medium text-slate-800">
                {formatValue(taylor_series.delta_only_var)}
              </span>
            </div>
            <div className="flex justify-between items-end border-b border-slate-50 pb-1">
              <span className="text-xs text-slate-500">Delta-Gamma VaR</span>
              <span className="text-sm font-mono font-medium text-slate-800">
                {formatValue(taylor_series.delta_gamma_var)}
              </span>
            </div>
            <div className="flex justify-between items-end border-b border-slate-50 pb-1">
              <span className="text-xs text-slate-500">Gamma Correction</span>
              <span className="text-sm font-mono font-medium text-indigo-600">
                {formatValue(taylor_series.gamma_correction)}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 leading-tight mt-2">
              Second-order approximation capturing convexity in derivative P&L distributions.
            </p>
          </div>
        </div>

        {/* Laplace Transforms / Aggregate Loss */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Laplace (Aggregate Loss)
            </h4>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-end border-b border-slate-50 pb-1">
              <span className="text-xs text-slate-500">Expected Loss (E[S])</span>
              <span className="text-sm font-mono font-medium text-slate-800">
                {formatValue(laplace_transforms.expected_loss)}
              </span>
            </div>
            <div className="flex justify-between items-end border-b border-slate-50 pb-1">
              <span className="text-xs text-slate-500">Aggregate VaR (99%)</span>
              <span className="text-sm font-mono font-medium text-slate-800">
                {formatValue(laplace_transforms.aggregate_var_99)}
              </span>
            </div>
            <div className="flex justify-between items-end border-b border-slate-50 pb-1">
              <span className="text-xs text-slate-500">Aggregate ES (99%)</span>
              <span className="text-sm font-mono font-medium text-emerald-600">
                {formatValue(laplace_transforms.aggregate_es_99)}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 leading-tight mt-2">
              Compound Poisson process with exponential severity for credit/operational risk.
            </p>
          </div>
        </div>

        {/* Extreme Value Theory / GPD */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-rose-500"></div>
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              EVT (Tail Modelling)
            </h4>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-end border-b border-slate-50 pb-1">
              <span className="text-xs text-slate-500">GPD Shape (ξ)</span>
              <span className="text-sm font-mono font-medium text-slate-800">
                {formatValue(evt_gpd.gpd_shape_xi)}
              </span>
            </div>
            <div className="flex justify-between items-end border-b border-slate-50 pb-1">
              <span className="text-xs text-slate-500">Tail VaR (99%)</span>
              <span className="text-sm font-mono font-medium text-slate-800">
                {formatValue(evt_gpd.tail_var_99)}
              </span>
            </div>
            <div className="flex justify-between items-end border-b border-slate-50 pb-1">
              <span className="text-xs text-slate-500">Tail ES (99%)</span>
              <span className="text-sm font-mono font-medium text-rose-600">
                {formatValue(evt_gpd.tail_es_99)}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 leading-tight mt-2">
              Peaks-over-threshold method using Generalized Pareto Distribution for fat tails.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
