import _createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';
import type { CorrelationResult } from '../types';

// Handle potential .default wrapper from Vite/ESM interop
const createPlotlyComponent = (_createPlotlyComponent as any).default || _createPlotlyComponent;
const Plot = createPlotlyComponent(Plotly);

interface CorrelationHeatmapProps {
  data: CorrelationResult | undefined;
}

export default function CorrelationHeatmap({ data }: CorrelationHeatmapProps) {
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex items-center justify-center h-80">
        <p className="text-slate-400 text-sm">Loading correlation matrix...</p>
      </div>
    );
  }

  const labels = data.data.labels;
  const matrix = data.data.matrix;

  // Build hover text with exact values
  const hoverText: string[][] = matrix.map((row, i) =>
    row.map((val, j) => `${labels[i]} / ${labels[j]}<br>Correlation: ${val.toFixed(4)}`),
  );

  const plotData: Plotly.Data[] = [
    {
      type: 'heatmap',
      z: matrix,
      x: labels,
      y: labels,
      colorscale: [
        [0, '#2563eb'],     // blue (negative)
        [0.5, '#ffffff'],   // white (zero)
        [1, '#dc2626'],     // red (positive)
      ],
      zmin: -1,
      zmax: 1,
      hoverinfo: 'text' as const,
      text: hoverText as unknown as string[],
      colorbar: {
        title: { text: 'Correlation', side: 'right' as const },
        thickness: 15,
        len: 0.9,
      },
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    title: { text: 'Asset Correlation Matrix', font: { size: 14, color: '#334155' } },
    margin: { l: 100, r: 40, t: 50, b: 100 },
    xaxis: {
      tickangle: -45,
      tickfont: { size: 10 },
    },
    yaxis: {
      tickfont: { size: 10 },
      autorange: 'reversed' as const,
    },
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
