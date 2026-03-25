import _createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';
import type { ClusteringResult } from '../types';

const createPlotlyComponent = (_createPlotlyComponent as any).default || _createPlotlyComponent;
const Plot = createPlotlyComponent(Plotly);

interface ClusterMapProps {
  data: ClusteringResult | undefined;
}

const CLUSTER_COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#10b981', // emerald
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
];

export default function ClusterMap({ data }: ClusterMapProps) {
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex items-center justify-center h-80">
        <p className="text-slate-400 text-sm">Loading cluster data...</p>
      </div>
    );
  }

  const { scatter } = data.data;
  const nClusters = data.metrics.n_clusters;
  const plotData: Plotly.Data[] = [];

  // Create one scatter trace per cluster
  for (let c = 0; c < nClusters; c++) {
    const indices = scatter.clusters
      .map((cluster, idx) => (cluster === c ? idx : -1))
      .filter((idx) => idx !== -1);

    if (indices.length === 0) continue;

    plotData.push({
      type: 'scatter',
      mode: 'markers',
      x: indices.map((i) => scatter.x[i]),
      y: indices.map((i) => scatter.y[i]),
      text: indices.map((i) => scatter.labels[i]),
      name: `Cluster ${c + 1}`,
      marker: {
        size: 10,
        color: CLUSTER_COLORS[c % CLUSTER_COLORS.length],
        opacity: 0.8,
      },
      hovertemplate: '%{text}<br>x: %{x:.4f}<br>y: %{y:.4f}<extra></extra>',
    });
  }

  // Centroids trace
  if (scatter.centroids_x && scatter.centroids_y) {
    plotData.push({
      type: 'scatter',
      mode: 'markers',
      x: scatter.centroids_x,
      y: scatter.centroids_y,
      name: 'Centroids',
      marker: {
        size: 16,
        color: '#1e293b',
        symbol: 'x',
        line: { width: 2, color: '#1e293b' },
      },
      hovertemplate: 'Centroid<br>x: %{x:.4f}<br>y: %{y:.4f}<extra></extra>',
    });
  }

  const layout: Partial<Plotly.Layout> = {
    title: { text: 'Asset Clusters (PCA Projection)', font: { size: 14, color: '#334155' } },
    margin: { l: 50, r: 30, t: 50, b: 50 },
    xaxis: {
      title: { text: 'Component 1' },
      tickfont: { size: 10 },
    },
    yaxis: {
      title: { text: 'Component 2' },
      tickfont: { size: 10 },
    },
    showlegend: true,
    legend: { font: { size: 10 } },
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
