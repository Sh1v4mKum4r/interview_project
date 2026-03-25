import type { AnalysisRequest } from '../types';

const ASSET_CLASSES = [
  { value: 'equity', label: 'Equity' },
  { value: 'fixed_income', label: 'Fixed Income' },
  { value: 'commodity', label: 'Commodity' },
  { value: 'fx', label: 'FX' },
  { value: 'derivative', label: 'Derivative' },
];

const RISK_MODELS: { value: AnalysisRequest['risk_model']; label: string }[] = [
  { value: 'historical', label: 'Historical' },
  { value: 'parametric', label: 'Parametric' },
  { value: 'monte_carlo', label: 'Monte Carlo' },
];

const TIME_HORIZONS: AnalysisRequest['time_horizon'][] = ['1D', '10D', '1M', '1Y'];

const CONFIDENCE_LEVELS: { value: AnalysisRequest['confidence_level']; label: string }[] = [
  { value: 0.95, label: '95%' },
  { value: 0.99, label: '99%' },
];

const REGULATORY_REGIMES = [
  { value: 'basel3', label: 'Basel III' },
  { value: 'mifid2', label: 'MiFID II' },
];

interface ParameterPanelProps {
  params: AnalysisRequest;
  onParamsChange: (params: AnalysisRequest) => void;
  onRunAnalysis: () => void;
  isLoading: boolean;
}

export default function ParameterPanel({
  params,
  onParamsChange,
  onRunAnalysis,
  isLoading,
}: ParameterPanelProps) {
  const toggleAssetClass = (value: string) => {
    const current = params.asset_classes;
    const next = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
    if (next.length > 0) {
      onParamsChange({ ...params, asset_classes: next });
    }
  };

  const toggleRegime = (value: string) => {
    const current = params.regulatory_regimes;
    const next = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
    onParamsChange({ ...params, regulatory_regimes: next });
  };

  return (
    <div className="space-y-6">
      {/* Asset Classes */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-2">
          Asset Classes
        </h3>
        <div className="space-y-1.5">
          {ASSET_CLASSES.map((ac) => (
            <label
              key={ac.value}
              className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer hover:text-slate-900"
            >
              <input
                type="checkbox"
                checked={params.asset_classes.includes(ac.value)}
                onChange={() => toggleAssetClass(ac.value)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              {ac.label}
            </label>
          ))}
        </div>
      </div>

      {/* Risk Model */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-2">
          Risk Model
        </h3>
        <div className="space-y-1.5">
          {RISK_MODELS.map((rm) => (
            <label
              key={rm.value}
              className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer hover:text-slate-900"
            >
              <input
                type="radio"
                name="risk_model"
                checked={params.risk_model === rm.value}
                onChange={() => onParamsChange({ ...params, risk_model: rm.value })}
                className="border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              {rm.label}
            </label>
          ))}
        </div>
      </div>

      {/* Time Horizon */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-2">
          Time Horizon
        </h3>
        <div className="flex gap-1">
          {TIME_HORIZONS.map((th) => (
            <button
              key={th}
              onClick={() => onParamsChange({ ...params, time_horizon: th })}
              className={`flex-1 px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                params.time_horizon === th
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {th}
            </button>
          ))}
        </div>
      </div>

      {/* Confidence Level */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-2">
          Confidence Level
        </h3>
        <div className="space-y-1.5">
          {CONFIDENCE_LEVELS.map((cl) => (
            <label
              key={cl.value}
              className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer hover:text-slate-900"
            >
              <input
                type="radio"
                name="confidence_level"
                checked={params.confidence_level === cl.value}
                onChange={() => onParamsChange({ ...params, confidence_level: cl.value })}
                className="border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              {cl.label}
            </label>
          ))}
        </div>
      </div>

      {/* Regulatory Regime */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-2">
          Regulatory Regime
        </h3>
        <div className="space-y-1.5">
          {REGULATORY_REGIMES.map((rr) => (
            <label
              key={rr.value}
              className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer hover:text-slate-900"
            >
              <input
                type="checkbox"
                checked={params.regulatory_regimes.includes(rr.value)}
                onChange={() => toggleRegime(rr.value)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              {rr.label}
            </label>
          ))}
        </div>
      </div>

      {/* Run Analysis Button */}
      <button
        onClick={onRunAnalysis}
        disabled={isLoading}
        className="w-full py-2.5 px-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <svg
              className="animate-spin h-4 w-4 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Running...
          </>
        ) : (
          'Run Analysis'
        )}
      </button>
    </div>
  );
}
