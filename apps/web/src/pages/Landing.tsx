import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck, Activity, Droplet } from 'lucide-react';
import { Logo } from '../components/common/Logo';
import { useAuthStore } from '../store/auth';

export const Landing: React.FC = () => {
  const { role } = useAuthStore();

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden bg-mist">
      {/* Drifting cloud layer background */}
      <div className="drifting-cloud-bg">
        <div className="cloud-layer" />
      </div>

      {/* Thin minimal top nav */}
      <nav className="relative z-10 px-6 py-4 flex items-center justify-between max-w-6xl w-full mx-auto">
        <Logo size="md" />

        <div className="flex items-center gap-3">
          <Link
            to={role ? '/app/overview' : '/login'}
            className="px-4 py-2 bg-sky-500 hover:bg-sky-700 text-white text-xs font-semibold rounded-btn transition-colors shadow-sm flex items-center gap-1.5"
          >
            <span>{role ? 'Enter Dashboard' : 'Demo Gate'}</span>
            <ArrowRight className="w-3.5 h-3.5 stroke-[1.5]" />
          </Link>
        </div>
      </nav>

      {/* Hero Section (XinoTask preview placeholder) */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center text-center px-4 py-16 max-w-4xl mx-auto space-y-8">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 glass-pill text-xs text-sky-700 dark:text-sky-300 font-medium border-sky-100 dark:border-white/10 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-aqua animate-pulse" />
          <span>TCS Tech Day Challenge 12 • AI for Water Resilience</span>
        </div>

        <div className="space-y-4">
          <h1 className="text-4xl sm:text-6xl font-light text-ink-900 tracking-tight">
            The autonomous <span className="font-bold text-sky-700 dark:text-sky-300">water fortress</span> for resilient campuses.
          </h1>
          <p className="text-base sm:text-lg text-ink-600 max-w-2xl mx-auto font-normal">
            Continuous loop: Monitor, Detect, Predict, Prioritize, Optimize, Intervene, and Measure across 20 campus facilities with strict vulnerable zone guardrails.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
          <Link
            to="/login"
            className="px-6 py-3 bg-sky-500 hover:bg-sky-700 text-white text-sm font-semibold rounded-btn transition-colors shadow-md flex items-center gap-2"
          >
            <span>Launch Digital Twin Demo</span>
            <ArrowRight className="w-4 h-4 stroke-[1.5]" />
          </Link>

          <Link
            to="/app/overview"
            className="px-6 py-3 bg-white/70 hover:bg-white text-ink-900 text-sm font-semibold rounded-btn border border-sky-100 dark:border-white/10 transition-colors shadow-sm"
          >
            Explore Overview
          </Link>
        </div>

        {/* Feature Pills */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-8 w-full max-w-2xl text-left">
          <div className="glass-panel p-4 space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-ink-900">
              <Droplet className="w-4 h-4 text-sky-500 stroke-[1.5]" />
              <span>Digital Twin Engine</span>
            </div>
            <p className="text-xs text-ink-600">
              20 campus blocks, 4 tanks, 2 borewells, and 1 central sump modelled dynamically.
            </p>
          </div>

          <div className="glass-panel p-4 space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-ink-900">
              <ShieldCheck className="w-4 h-4 text-leaf stroke-[1.5]" />
              <span>Equity Guardrails</span>
            </div>
            <p className="text-xs text-ink-600">
              Hostels, health centre, and crèche are shielded with strict rollback steps.
            </p>
          </div>

          <div className="glass-panel p-4 space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-ink-900">
              <Activity className="w-4 h-4 text-amber stroke-[1.5]" />
              <span>7 Jury Capabilities</span>
            </div>
            <p className="text-xs text-ink-600">
              Reason across sources, multi-step plans, verifier agent, and tool actions.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};
