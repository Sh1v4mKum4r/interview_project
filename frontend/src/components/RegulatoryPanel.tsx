import type { RegulatoryResult } from '../types';

interface RegulatoryPanelProps {
  data: RegulatoryResult | undefined;
}

type StatusColor = 'green' | 'amber' | 'red';

function statusToColor(status: string): StatusColor {
  const lower = status.toLowerCase();
  if (lower === 'green' || lower === 'pass' || lower === 'compliant' || lower === 'adequate') return 'green';
  if (lower === 'amber' || lower === 'warning' || lower === 'watch') return 'amber';
  return 'red';
}

function StatusDot({ color }: { color: StatusColor }) {
  const colors: Record<StatusColor, string> = {
    green: 'bg-emerald-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500',
  };
  return (
    <span
      className={`inline-block w-3 h-3 rounded-full ${colors[color]}`}
      title={color}
    />
  );
}

function formatValue(val: number | string): string {
  if (typeof val === 'string') return val;
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(2)}M`;
  if (val >= 1_000) return `$${(val / 1_000).toFixed(1)}K`;
  if (val < 1 && val > 0) return `${(val * 100).toFixed(2)}%`;
  return val.toFixed(2);
}

interface MetricRow {
  name: string;
  value: number | string;
  threshold: string;
  status: StatusColor;
}

export default function RegulatoryPanel({ data }: RegulatoryPanelProps) {
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4">
          Regulatory Compliance
        </h3>
        <p className="text-slate-400 text-sm">Loading regulatory data...</p>
      </div>
    );
  }

  const { basel3, mifid2 } = data.metrics;

  const baselRows: MetricRow[] = [
    {
      name: 'CET1 Ratio',
      value: basel3.cet1_ratio,
      threshold: '>= 4.5%',
      status: statusToColor(basel3.cet1_status),
    },
    {
      name: 'Tier 1 Ratio',
      value: basel3.tier1_ratio,
      threshold: '>= 6.0%',
      status: statusToColor(basel3.tier1_status),
    },
    {
      name: 'Total Capital Ratio',
      value: basel3.total_capital_ratio,
      threshold: '>= 8.0%',
      status: statusToColor(basel3.total_capital_status),
    },
    {
      name: 'Leverage Ratio',
      value: basel3.leverage_ratio,
      threshold: '>= 3.0%',
      status: statusToColor(basel3.leverage_status),
    },
    {
      name: 'LCR',
      value: basel3.lcr,
      threshold: '>= 100%',
      status: statusToColor(basel3.lcr_status),
    },
  ];

  const overallColor = statusToColor(data.metrics.overall_status);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
          Regulatory Compliance
        </h3>
        <div className="flex items-center gap-2">
          <StatusDot color={overallColor} />
          <span className="text-sm font-medium text-slate-600 capitalize">
            {data.metrics.overall_status}
          </span>
        </div>
      </div>

      {/* Basel III Table */}
      <div className="mb-6">
        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Basel III
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 pr-4 font-medium text-slate-600">Metric</th>
                <th className="text-right py-2 px-4 font-medium text-slate-600">Value</th>
                <th className="text-right py-2 px-4 font-medium text-slate-600">Threshold</th>
                <th className="text-center py-2 pl-4 font-medium text-slate-600">Status</th>
              </tr>
            </thead>
            <tbody>
              {baselRows.map((row) => (
                <tr key={row.name} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 pr-4 text-slate-700">{row.name}</td>
                  <td className="py-2 px-4 text-right font-mono text-slate-800">
                    {formatValue(row.value)}
                  </td>
                  <td className="py-2 px-4 text-right text-slate-500">{row.threshold}</td>
                  <td className="py-2 pl-4 text-center">
                    <StatusDot color={row.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-2 text-xs text-slate-500">
          RWA: {formatValue(basel3.rwa)} &middot; FRTB ES: {formatValue(basel3.frtb_es)}
        </div>
      </div>

      {/* MiFID II Summary */}
      <div>
        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          MiFID II
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-slate-50 rounded-lg p-3">
            <p className="text-lg font-bold text-slate-800">{mifid2.transaction_count}</p>
            <p className="text-xs text-slate-500">Transactions</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-3">
            <p className={`text-lg font-bold ${mifid2.best_execution_flags > 0 ? 'text-amber-600' : 'text-slate-800'}`}>
              {mifid2.best_execution_flags}
            </p>
            <p className="text-xs text-slate-500">Execution Flags</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-3">
            <p className={`text-lg font-bold ${mifid2.position_limit_breaches.length > 0 ? 'text-red-600' : 'text-slate-800'}`}>
              {mifid2.position_limit_breaches.length}
            </p>
            <p className="text-xs text-slate-500">Position Breaches</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-3">
            <p className={`text-lg font-bold ${mifid2.transparency_issues > 0 ? 'text-amber-600' : 'text-slate-800'}`}>
              {mifid2.transparency_issues}
            </p>
            <p className="text-xs text-slate-500">Transparency Issues</p>
          </div>
        </div>
        {mifid2.position_limit_breaches.length > 0 && (
          <div className="mt-2 text-xs text-red-600">
            Breaches: {mifid2.position_limit_breaches.join(', ')}
          </div>
        )}
      </div>
    </div>
  );
}
