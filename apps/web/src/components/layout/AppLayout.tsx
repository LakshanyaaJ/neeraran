import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Navbar } from './Navbar';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { TabTransition } from '../transitions/WaterRiseTransition';

export const AppLayout: React.FC = () => {
  const location = useLocation();

  return (
    <div className="relative min-h-screen flex flex-col font-sans selection:bg-sky-100 selection:text-sky-700">
      {/* Drifting subtle cloud layer background */}
      <div className="drifting-cloud-bg">
        <div className="cloud-layer" />
      </div>

      {/* Centred Pill Navbar Header */}
      <Navbar />

      {/* Main Content View with Tab Crossfade Transition */}
      <main className="relative z-10 flex-1 max-w-[1440px] w-full mx-auto px-4 sm:px-6 py-4">
        <ErrorBoundary fallbackTitle="View Rendering Error">
          <TabTransition tabKey={location.pathname}>
            <Outlet />
          </TabTransition>
        </ErrorBoundary>
      </main>

      {/* Minimal Footer */}
      <footer className="relative z-10 py-3 text-center text-xs text-ink-600 border-t border-ink-600/10">
        <div className="max-w-[1440px] mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-tamil font-bold text-sky-700 dark:text-sky-300">நீர்</span>
            <span className="font-sans font-semibold text-ink-900">Aran</span>
            <span>•</span>
            <span>Every drop accounted for.</span>
          </div>
          <div className="text-[11px] text-ink-600">
            TCS Tech Day Challenge 12 • Educational Campus Digital Twin
          </div>
        </div>
      </footer>
    </div>
  );
};

