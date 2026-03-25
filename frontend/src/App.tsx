import { useState, useEffect, useCallback } from 'react';
import {
  QueryClient,
  QueryClientProvider,
  useMutation,
} from '@tanstack/react-query';
import { runAnalysis, downloadReport } from './api/client';
import type { AnalysisRequest, AnalysisResults } from './types';
import ParameterPanel from './components/ParameterPanel';
import FileUpload from './components/FileUpload';
import DashboardGrid from './components/DashboardGrid';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

const DEFAULT_PARAMS: AnalysisRequest = {
  asset_classes: ['equity', 'fixed_income', 'commodity', 'fx', 'derivative'],
  risk_model: 'historical',
  time_horizon: '1D',
  confidence_level: 0.95,
  regulatory_regimes: ['basel3'],
  data_source: 'synthetic',
};

function AppInner() {
  const [params, setParams] = useState<AnalysisRequest>(DEFAULT_PARAMS);
  const [results, setResults] = useState<AnalysisResults | undefined>(undefined);
  const [statusMessage, setStatusMessage] = useState('Ready');
  const [hasRun, setHasRun] = useState(false);

  const analysisMutation = useMutation({
    mutationFn: runAnalysis,
    onMutate: () => {
      setStatusMessage('Running analysis...');
    },
    onSuccess: (data) => {
      setResults(data);
      setStatusMessage(
        `Analysis complete - ${new Date().toLocaleTimeString()}`,
      );
    },
    onError: (error: Error) => {
      setStatusMessage(`Error: ${error.message}`);
    },
  });

  const downloadMutation = useMutation({
    mutationFn: downloadReport,
    onMutate: () => {
      setStatusMessage('Generating Excel report...');
    },
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `risk_report_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setStatusMessage('Report downloaded');
    },
    onError: (error: Error) => {
      setStatusMessage(`Download error: ${error.message}`);
    },
  });

  const handleRunAnalysis = useCallback(() => {
    analysisMutation.mutate(params);
  }, [analysisMutation, params]);

  const handleDownload = useCallback(() => {
    downloadMutation.mutate(params);
  }, [downloadMutation, params]);

  const handleUploadSuccess = useCallback(
    (uploadId: string) => {
      const updated: AnalysisRequest = {
        ...params,
        data_source: 'uploaded',
        upload_id: uploadId,
      };
      setParams(updated);
      setStatusMessage('File uploaded - ready to analyze');
    },
    [params],
  );

  // Auto-run on first load
  useEffect(() => {
    if (!hasRun) {
      setHasRun(true);
      analysisMutation.mutate(params);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* Top Bar */}
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <svg
              className="w-5 h-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          </div>
          <h1 className="text-lg font-bold text-slate-800">
            Regulatory Risk Analysis System
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            disabled={downloadMutation.isPending || !results}
            className="px-4 py-2 text-sm font-medium bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            {downloadMutation.isPending ? 'Generating...' : 'Download Excel'}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-72 shrink-0 bg-white border-r border-slate-200 overflow-y-auto p-5 space-y-6">
          <ParameterPanel
            params={params}
            onParamsChange={setParams}
            onRunAnalysis={handleRunAnalysis}
            isLoading={analysisMutation.isPending}
          />
          <div className="border-t border-slate-200 pt-4">
            <FileUpload onUploadSuccess={handleUploadSuccess} />
          </div>
        </aside>

        {/* Dashboard Area */}
        <main className="flex-1 overflow-y-auto p-6">
          <DashboardGrid results={results} />
        </main>
      </div>

      {/* Status Bar */}
      <footer className="bg-white border-t border-slate-200 px-6 py-2 flex items-center justify-between shrink-0 text-xs text-slate-500">
        <div className="flex items-center gap-2">
          {analysisMutation.isPending && (
            <svg
              className="animate-spin h-3 w-3 text-blue-600"
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
          )}
          <span>{statusMessage}</span>
        </div>
        <span>
          {params.risk_model} | {params.time_horizon} |{' '}
          {params.confidence_level === 0.95 ? '95%' : '99%'} |{' '}
          {params.data_source === 'uploaded' ? 'Custom Data' : 'Synthetic Data'}
        </span>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  );
}
