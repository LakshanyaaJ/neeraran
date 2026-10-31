import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { WaterRiseTransition } from './components/transitions/WaterRiseTransition';
import { AuthGuard } from './components/auth/AuthGuard';
import { AppLayout } from './components/layout/AppLayout';

// Pages
import { Landing } from './pages/Landing';
import { Login } from './pages/Login';
import { Overview } from './pages/app/Overview';
import { MapPage } from './pages/app/Map';
import { AgentsPage } from './pages/app/Agents';
import { ApprovalsPage } from './pages/app/Approvals';
import { SimulationPage } from './pages/app/Simulation';
import { EvaluationPage } from './pages/app/Evaluation';
import { ResponsibleAIPage } from './pages/app/ResponsibleAI';

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
          </WaterRiseTransition>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
