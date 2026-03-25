import _createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';
import type { DistributionFittingResult, MomentsResult } from '../types';

const createPlotlyComponent = (_createPlotlyComponent as any).default || _createPlotlyComponent;
const Plot = createPlotlyComponent(Plotly);

interface DistributionChartProps {
  data: DistributionFittingResult | undefined;
  moments: MomentsResult | undefined;
}

export default function DistributionChart({ data, moments }: DistributionChartProps) {
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex items-center justify-center h-80">
        <p className="text-slate-400 text-sm">Loading distribution data...</p>
      </div>
    );
  }

  // Use the first asset available for the portfolio-level view
  const assetKeys = Object.keys(data.data);
  if (assetKeys.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex items-center justify-center h-80">
        <p className="text-slate-400 text-sm">No distribution data available</p>
      </div>
    );
  }

  const firstKey = assetKeys[0];
  const assetData = data.data[firstKey];

  const plotData: Plotly.Data[] = [];

  // Histogram trace
  if (assetData.histogram) {
    const bins = assetData.histogram.bins;
    const counts = assetData.histogram.counts;

    // Convert counts to density for overlay with fitted curves
    const binWidth = bins.length > 1 ? bins[1] - bins[0] : 1;
    const totalArea = counts.reduce((s, c) => s + c, 0) * binWidth;
    const density = counts.map((c) => c / (totalArea || 1));

    plotData.push({
      type: 'bar',
      x: bins.slice(0, counts.length),
      y: density,
      name: 'Returns',
      marker: { color: 'rgba(59, 130, 246, 0.5)', line: { color: 'rgba(59, 130, 246, 0.8)', width: 1 } },
      width: binWidth * 0.9,
      hovertemplate: 'Return: %{x:.4f}<br>Density: %{y:.4f}<extra></extra>',
    });
  }

  // Fitted curve overlays
  const curveColors: Record<string, string> = {
    normal: '#dc2626',
    student_t: '#059669',
    t: '#059669',
  };
  const curveNames: Record<string, string> = {
    normal: 'Normal Fit',
    student_t: 'Student-t Fit',
    t: 'Student-t Fit',
  };

  if (assetData.fitted_curves) {
    for (const [curveName, curve] of Object.entries(assetData.fitted_curves)) {
      plotData.push({
        type: 'scatter',
        mode: 'lines',
        x: curve.x,
        y: curve.y,
        name: curveNames[curveName] || curveName,
        line: {
          color: curveColors[curveName] || '#8b5cf6',
          width: 2,
        },
        hovertemplate: '%{y:.4f}<extra></extra>',
      });
    }
  }

  // Build moment annotations
  const annotations: Partial<Plotly.Annotations>[] = [];
  if (moments) {
    const momentKeys = Object.keys(moments.metrics);
    if (momentKeys.length > 0) {
      const firstMoment = moments.metrics[momentKeys[0]];
      const text = [
        `Mean: ${firstMoment.mean.toFixed(6)}`,
        `Vol: ${Math.sqrt(firstMoment.variance).toFixed(6)}`,
        `Skew: ${firstMoment.skewness.toFixed(4)}`,
        `Kurt: ${firstMoment.kurtosis.toFixed(4)}`,
      ].join('<br>');

      annotations.push({
        xref: 'paper',
        yref: 'paper',
        x: 0.98,
        y: 0.95,
        xanchor: 'right',
        yanchor: 'top',
        text,
        showarrow: false,
        font: { size: 10, color: '#475569', family: 'monospace' },
        bgcolor: 'rgba(248, 250, 252, 0.9)',
        bordercolor: '#cbd5e1',
        borderwidth: 1,
        borderpad: 6,
      });
    }
  }

  const layout: Partial<Plotly.Layout> = {
    title: { text: 'Return Distribution', font: { size: 14, color: '#334155' } },
    margin: { l: 50, r: 30, t: 50, b: 50 },
    xaxis: {
      title: { text: 'Returns' },
      tickfont: { size: 10 },
    },
    yaxis: {
      title: { text: 'Density' },
      tickfont: { size: 10 },
    },
    barmode: 'overlay',
    showlegend: true,
    legend: { x: 0.02, y: 0.95, font: { size: 10 } },
    annotations,
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
