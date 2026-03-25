export interface AnalysisRequest {
  asset_classes: string[];
  risk_model: 'historical' | 'parametric' | 'monte_carlo';
  time_horizon: '1D' | '10D' | '1M' | '1Y';
  confidence_level: 0.95 | 0.99;
  regulatory_regimes: string[];
  data_source: 'synthetic' | 'uploaded';
  upload_id?: string;
}

export interface AnalysisResults {
  moments?: MomentsResult;
  correlation?: CorrelationResult;
  distribution_fitting?: DistributionFittingResult;
  factor_model?: FactorModelResult;
  risk?: RiskSummaryResult;
  pca?: PCAResult;
  clustering?: ClusteringResult;
  regression?: RegressionResult;
  exposure?: ExposureResult;
  regulatory?: RegulatoryResult;
  advanced?: AdvancedResult;
  [key: string]: unknown;
}

export interface MomentsResult {
  metrics: Record<string, { mean: number; variance: number; skewness: number; kurtosis: number }>;
  data: { assets: string[]; mean: number[]; variance: number[]; skewness: number[]; kurtosis: number[] };
}

export interface CorrelationResult {
  metrics: { matrix: number[][] };
  data: { labels: string[]; matrix: number[][] };
}

export interface DistributionFittingResult {
  metrics: Record<string, { best_fit: string; params: Record<string, unknown>; aic: Record<string, number> }>;
  data: Record<string, {
    histogram: { bins: number[]; counts: number[] };
    fitted_curves: Record<string, { x: number[]; y: number[] }>;
  }>;
}

export interface FactorModelResult {
  metrics: Record<string, { alpha: number; betas: number[]; r_squared: number; residual_vol: number }>;
  data: { factor_loadings: number[][]; assets: string[]; factors: string[] };
}

export interface RiskSummaryResult {
  metrics: {
    historical: VaRMetrics;
    parametric_normal: VaRMetrics;
    parametric_t: VaRMetrics;
    monte_carlo: VaRMetrics;
  };
  data: {
    comparison_chart: { models: string[]; var_values: number[]; es_values: number[] };
  };
}

export interface VaRMetrics {
  portfolio_var: number;
  portfolio_es: number;
  var_dollar: number;
  es_dollar: number;
  per_asset?: Record<string, { var: number; es: number }>;
}

export interface PCAResult {
  metrics: {
    n_components: number;
    eigenvalues: number[];
    variance_explained: number[];
    cumulative_variance: number[];
    top_3_components_explain: number;
  };
  data: {
    eigenvalues: number[];
    variance_explained: number[];
    cumulative_variance: number[];
    component_loadings: Record<string, Record<string, number>>;
    labels: string[];
  };
}

export interface ClusteringResult {
  metrics: {
    n_clusters: number;
    assignments: Record<string, number>;
    centroids: number[][];
    inertia: number;
  };
  data: {
    scatter: {
      x: number[];
      y: number[];
      labels: string[];
      clusters: number[];
      centroids_x: number[];
      centroids_y: number[];
    };
    elbow: { k_values: number[]; inertias: number[] };
  };
}

export interface RegressionResult {
  metrics: Record<string, {
    alpha: number;
    beta_mkt: number;
    beta_smb: number;
    beta_hml: number;
    r_squared: number;
    adj_r_squared: number;
    t_stats: Record<string, number>;
    p_values: Record<string, number>;
  }>;
  data: {
    factor_names: string[];
    assets: string[];
    coefficients: number[][];
    r_squared: number[];
  };
}

export interface ExposureResult {
  metrics: {
    weight_by_class: Record<string, number>;
    risk_contribution_by_class: Record<string, number>;
    risk_contribution_by_asset: Record<string, number>;
    portfolio_volatility: number;
  };
  data: {
    classes: string[];
    weights: number[];
    risk_contributions: number[];
    assets: string[];
    asset_risk_contributions: number[];
  };
}

export interface RegulatoryResult {
  metrics: {
    overall_status: string;
    basel3: {
      rwa: number;
      rwa_breakdown: Record<string, number>;
      cet1_ratio: number;
      cet1_status: string;
      tier1_ratio: number;
      tier1_status: string;
      total_capital_ratio: number;
      total_capital_status: string;
      leverage_ratio: number;
      leverage_status: string;
      lcr: number;
      lcr_status: string;
      frtb_es: number;
    };
    mifid2: {
      transaction_count: number;
      best_execution_flags: number;
      position_limit_breaches: string[];
      transparency_issues: number;
    };
  };
  data: Record<string, unknown>;
}

export interface AdvancedResult {
  metrics: {
    taylor_series: Record<string, unknown>;
    laplace_transforms: Record<string, unknown>;
    evt_gpd: Record<string, unknown>;
  };
  data: {
    taylor_series: Record<string, unknown>;
    laplace_transforms: Record<string, unknown>;
    evt_gpd: Record<string, unknown>;
  };
}

export interface UploadResponse {
  upload_id: string;
  filename: string;
  num_assets: number;
  num_days: number;
  asset_classes: Record<string, string>;
  message: string;
}

export interface ConfigOptions {
  asset_classes: string[];
  risk_models: string[];
  time_horizons: string[];
  confidence_levels: number[];
  regulatory_regimes: string[];
}
