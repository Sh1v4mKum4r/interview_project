import axios from 'axios';
import type { AnalysisRequest, AnalysisResults, UploadResponse, ConfigOptions } from '../types';

const api = axios.create({
  baseURL: 'http://localhost:6969/api',
  timeout: 120000,
});

export async function runAnalysis(params: AnalysisRequest): Promise<AnalysisResults> {
  const { data } = await api.post<AnalysisResults>('/analyze', params);
  return data;
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post<UploadResponse>('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function downloadReport(params: AnalysisRequest): Promise<Blob> {
  const { data } = await api.post('/report/excel', {
    analysis_config: params,
    capital_config: { cet1: 1200000, tier1: 1500000, total: 2000000 },
  }, {
    responseType: 'blob',
  });
  return data;
}

export async function getConfigOptions(): Promise<ConfigOptions> {
  const { data } = await api.get<ConfigOptions>('/config/options');
  return data;
}

export async function getDefaultDataInfo(): Promise<Record<string, unknown>> {
  const { data } = await api.get('/data/default');
  return data;
}
