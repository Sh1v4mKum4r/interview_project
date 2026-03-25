import _createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';
import type { PCAResult } from '../types';

const createPlotlyComponent = (_createPlotlyComponent as any).default || _createPlotlyComponent;
const Plot = createPlotlyComponent(Plotly);

interface PCAChartProps {
  data: PCAResult | undefined;
}

export default function PCAChart({ data }: PCAChartProps) {
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex items-center justify-center h-80">
        <p className="text-slate-400 text-sm">Loading PCA data...</p>
      </div>
    );
  }

  const varianceExplained = data.data.variance_explained ?? data.metrics.variance_explained;
  const cumulativeVariance = data.data.cumulative_variance ?? data.metrics.cumulative_variance;

  const componentLabels = varianceExplained.map((_, i) => `PC${i + 1}`);

  const plotData: Plotly.Data[] = [
    {
      type: 'bar',
      x: componentLabels,
      y: varianceExplained.map((v) => v * 100),
      name: 'Variance Explained',
      marker: { color: 'rgba(59, 130, 246, 0.7)' },
      hovertemplate: '%{x}: %{y:.2f}%<extra></extra>',
      yaxis: 'y',
    },
    {
      type: 'scatter',
      mode: 'lines+markers',
      x: componentLabels,
      y: cumulativeVariance.map((v) => v * 100),
      name: 'Cumulative',
      line: { color: '#dc2626', width: 2 },
      marker: { size: 6, color: '#dc2626' },
      hovertemplate: '%{x}: %{y:.2f}%<extra></extra>',
      yaxis: 'y',
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    title: { text: 'PCA Scree Plot', font: { size: 14, color: '#334155' } },
    margin: { l: 50, r: 30, t: 50, b: 50 },
    xaxis: {
      title: { text: 'Principal Component' },
      tickfont: { size: 10 },
    },
    yaxis: {
      title: { text: 'Variance Explained (%)' },
      tickfont: { size: 10 },
      range: [0, 105],
    },
    showlegend: true,
    legend: { x: 0.6, y: 0.4, font: { size: 10 } },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
      <Plot
        data={plotData}
        layout={layout}
        config={{ responsive: true, displayModeBar: false }}
        useResizeHandler
        style={{ width: '100%', height: '400px' }}
      />
    </div>
  );
}
