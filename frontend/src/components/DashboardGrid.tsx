import type { AnalysisResults } from '../types';
import RiskSummaryCard from './RiskSummaryCard';
import CorrelationHeatmap from './CorrelationHeatmap';
import DistributionChart from './DistributionChart';
import PCAChart from './PCAChart';
import ClusterMap from './ClusterMap';
import RegulatoryPanel from './RegulatoryPanel';
import AdvancedPanel from './AdvancedPanel';

interface DashboardGridProps {
  results: AnalysisResults | undefined;
}

export default function DashboardGrid({ results }: DashboardGridProps) {
  return (
    <div className="space-y-4">
      {/* Risk Summary - full width */}
      <RiskSummaryCard risk={results?.risk} exposure={results?.exposure} />

      {/* Correlation + Distribution - side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CorrelationHeatmap data={results?.correlation} />
        <DistributionChart
          data={results?.distribution_fitting}
          moments={results?.moments}
        />
      </div>

      {/* PCA + Clusters - side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <PCAChart data={results?.pca} />
        <ClusterMap data={results?.clustering} />
      </div>

      {/* Advanced Techniques - full width */}
      <AdvancedPanel data={results?.advanced} />

      {/* Regulatory Panel - full width */}
      <RegulatoryPanel data={results?.regulatory} />
    </div>
  );
}
