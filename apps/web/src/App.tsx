import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { WaterRiseTransition } from './components/transitions/WaterRiseTransition';
import { AuthGuard } from './components/auth/AuthGuard';
import { AppLayout } from './components/layout/AppLayout';

// Code-splitting / Lazy loading heavy pages for sub-1.5s initial load & MapLibre isolation
const Landing = lazy(() => import('./pages/Landing').then((m) => ({ default: m.Landing })));
const Login = lazy(() => import('./pages/Login').then((m) => ({ default: m.Login })));
const Overview = lazy(() => import('./pages/app/Overview').then((m) => ({ default: m.Overview })));
const MapPage = lazy(() => import('./pages/app/Map').then((m) => ({ default: m.MapPage })));
const AgentsPage = lazy(() => import('./pages/app/Agents').then((m) => ({ default: m.AgentsPage })));
const ApprovalsPage = lazy(() => import('./pages/app/Approvals').then((m) => ({ default: m.ApprovalsPage })));
const SimulationPage = lazy(() => import('./pages/app/Simulation').then((m) => ({ default: m.SimulationPage })));
const EvaluationPage = lazy(() => import('./pages/app/Evaluation').then((m) => ({ default: m.EvaluationPage })));
const ResponsibleAIPage = lazy(() => import('./pages/app/ResponsibleAI').then((m) => ({ default: m.ResponsibleAIPage })));

const PageLoadingFallback: React.FC = () => (
  <div className="w-full min-h-[400px] flex flex-col items-center justify-center p-8 space-y-3">
    <div className="w-6 h-6 border-2 border-azure-600 border-t-transparent rounded-full animate-spin" />
    <span className="text-xs font-mono text-ink-500">Loading digital twin view...</span>
  </div>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary fallbackTitle="Application Boot Exception">
        <BrowserRouter>
          {/* Custom Styled Toasts Matching NEERARAN Tokens */}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 3500,
              style: {
                background: 'var(--glass-bg)',
                backdropFilter: 'blur(16px)',
                WebkitBackdropFilter: 'blur(16px)',
                border: '1px solid var(--glass-border)',
                color: 'var(--text-primary)',
                boxShadow: 'var(--shadow-glass)',
                borderRadius: 'var(--radius-card)',
                fontSize: '12px',
                fontWeight: 500,
                padding: '10px 16px',
              },
              success: {
                iconTheme: {
                  primary: '#4CBF86',
                  secondary: '#FFFFFF',
                },
              },
              error: {
                iconTheme: {
                  primary: '#E5594F',
                  secondary: '#FFFFFF',
                },
              },
            }}
          />

          {/* Router Level Water-Rise Transition with prefers-reduced-motion fallback */}
          <WaterRiseTransition>
            <Suspense fallback={<PageLoadingFallback />}>
              <Routes>
                {/* Public Routes */}
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<Login />} />

                {/* Protected App Routes (Requires Role in AuthGuard) */}
                <Route
                  path="/app"
                  element={
                    <AuthGuard>
                      <AppLayout />
                    </AuthGuard>
                  }
                >
                  <Route index element={<Navigate to="/app/overview" replace />} />
                  <Route path="overview" element={<Overview />} />
                  <Route path="map" element={<MapPage />} />
                  <Route path="agents" element={<AgentsPage />} />
                  <Route path="approvals" element={<ApprovalsPage />} />
                  <Route path="simulation" element={<SimulationPage />} />
                  <Route path="evaluation" element={<EvaluationPage />} />
                  <Route path="responsible-ai" element={<ResponsibleAIPage />} />
                </Route>

                {/* Catch-all redirect */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </WaterRiseTransition>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
