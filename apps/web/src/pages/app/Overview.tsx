import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { 
  Droplet, 
  Layers, 
  Activity, 
  CloudSun, 
  ShieldCheck, 
  Play, 
  Pause, 
  FastForward, 
  RotateCcw, 
  Bug 
} from 'lucide-react';
import { api } from '../../api/client';
import { useAuthStore } from '../../store/auth';

export const Overview: React.FC = () => {
  const { role } = useAuthStore();
  const [shouldCrash, setShouldCrash] = useState(false);

  // If user triggers test crash to verify ErrorBoundary acceptance
  if (shouldCrash) {
    throw new Error('Test intentional render error to verify ErrorBoundary safety mechanism.');
  }

  const { data: state, isLoading, refetch } = useQuery({
    queryKey: ['simStateOverview'],
    queryFn: () => api.getSimulationState(),
    refetchInterval: 3000,
  });

  const handleStep = async () => {
    toast.promise(api.stepTick(5.0), {
      loading: 'Stepping digital twin clock by 5 mins...',
      success: () => {
        refetch();
        return 'Advanced 5 simulation minutes';
      },
      error: 'Failed to step simulation',
    });
  };

  const handleTogglePause = async () => {
    if (!state) return;
    const nextPaused = !state.is_paused;
    await api.togglePause(nextPaused);
    refetch();
    toast.success(nextPaused ? 'Simulation paused' : 'Simulation resumed');
  };

  const handleReset = async () => {
    await api.reset(42);
    refetch();
    toast.success('Digital twin reset to seed 42');
  };

  return (
    <div className="space-y-6">
      {/* Top Banner with Role Context */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-ink-600/10">
        <div>
          <h1 className="text-xl font-bold text-ink-900">
            Water Resilience Operational Overview
          </h1>
          <p className="text-xs text-ink-600">
            Current Session: <span className="font-semibold text-sky-700 dark:text-sky-300">{role === 'admin' ? 'Estate Admin (Full Ops & Approvals)' : 'Viewer (Observer Mode)'}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Verification tool: Intentionally trigger ErrorBoundary to test acceptance */}
          <button
            onClick={() => setShouldCrash(true)}
            className="px-2.5 py-1 text-[11px] text-coral hover:bg-coral/10 rounded-btn border border-coral/20 flex items-center gap-1 transition-colors"
            title="Trigger test exception to verify ErrorBoundary card"
          >
            <Bug className="w-3 h-3 stroke-[1.5]" />
            <span>Test ErrorBoundary</span>
          </button>

          <div className="sim-badge-sticky px-2.5 py-1 text-xs rounded font-medium">
            Simulated campus data • Seed 42
          </div>
        </div>
      </div>

      {/* KPI Cards Bento Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1 */}
        <div className="glass-panel p-5 space-y-2">
          <div className="flex items-center justify-between text-ink-600">
            <span className="text-xs font-medium">Main Raw Water Sump</span>
            <Droplet className="w-4 h-4 text-sky-500 stroke-[1.5]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-ink-900">
              {isLoading ? '...' : (state?.sump?.current_level_kl ?? 390.0)}
            </span>
            <span className="text-xs text-ink-600">kL / 500 kL</span>
          </div>
          <div className="w-full bg-sky-100 dark:bg-sky-950/60 rounded-full h-1.5 overflow-hidden">
            <div 
              className="bg-sky-500 h-1.5 rounded-full transition-all duration-500" 
              style={{ width: `${state?.sump?.pct_full ?? 78}%` }}
            />
          </div>
          <div className="text-[11px] text-ink-600 flex justify-between">
            <span>Inflow: {state?.sump?.raw_inflow_lpm ?? 450} L/min</span>
            <span className="text-aqua font-medium">{state?.sump?.pct_full ?? 78}% capacity</span>
          </div>
        </div>

        {/* KPI 2 */}
        <div className="glass-panel p-5 space-y-2">
          <div className="flex items-center justify-between text-ink-600">
            <span className="text-xs font-medium">Total Campus Storage</span>
            <Layers className="w-4 h-4 text-leaf stroke-[1.5]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-ink-900">
              {isLoading ? '...' : (state?.net_storage_kl ?? 646.5)}
            </span>
            <span className="text-xs text-ink-600">kL</span>
          </div>
          <div className="text-xs text-leaf font-medium flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 stroke-[1.5]" />
            <span>{state?.storage_reserve_hours ?? 11.1} hours reserve headroom</span>
          </div>
          <div className="text-[11px] text-ink-600">
            Across 4 Overhead Tanks + Sump
          </div>
        </div>

        {/* KPI 3 */}
        <div className="glass-panel p-5 space-y-2">
          <div className="flex items-center justify-between text-ink-600">
            <span className="text-xs font-medium">Campus Instantaneous Demand</span>
            <Activity className="w-4 h-4 text-amber stroke-[1.5]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-ink-900">
              {isLoading ? '...' : (state?.total_consumption_lpm ?? 973.0)}
            </span>
            <span className="text-xs text-ink-600">L/min</span>
          </div>
          <div className="text-xs text-ink-600">
            Active consumers: 20 blocks (~10,000 population)
          </div>
          <div className="text-[11px] text-aqua">
            Diurnal curve: {state?.sim_day_name ?? 'Monday'} {state?.hour_of_day ? `${Math.floor(state.hour_of_day)}:${Math.floor((state.hour_of_day % 1) * 60).toString().padStart(2, '0')}` : '07:15'}
          </div>
        </div>

        {/* KPI 4 */}
        <div className="glass-panel p-5 space-y-2">
          <div className="flex items-center justify-between text-ink-600">
            <span className="text-xs font-medium">Weather & Harvesting</span>
            <CloudSun className="w-4 h-4 text-sky-700 stroke-[1.5]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-ink-900">
              {state?.weather?.temp_c ?? 28.4}°C
            </span>
            <span className="text-xs text-ink-600">{state?.weather?.condition ?? 'Clear Sky'}</span>
          </div>
          <div className="text-xs text-ink-600">
            Humidity: {state?.weather?.humidity_pct ?? 65}% | Rain: {state?.weather?.rainfall_mm ?? 0} mm
          </div>
          <div className="text-[11px] text-sky-700 dark:text-sky-300 font-medium">
            Forecast rain chance: {state?.weather?.forecast_rain_prob_pct ?? 10}%
          </div>
        </div>
      </div>

      {/* Simulation Playback & Scrub Strip */}
      <div className="glass-panel p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-ink-600">Simulation Clock:</span>
          <span className="font-mono text-xs font-bold text-ink-900 bg-sky-50 dark:bg-sky-950/60 px-2.5 py-1 rounded-btn border border-sky-100 dark:border-white/10">
            Tick #{state?.tick ?? 0} ({state?.sim_time_iso ? new Date(state.sim_time_iso).toLocaleTimeString() : '07:15:00 AM'})
          </span>
          <span className="text-xs text-ink-600">Speed: {state?.speed ?? 1}x</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleTogglePause}
            className="px-3 py-1.5 bg-white dark:bg-sky-950/60 hover:bg-sky-50 text-ink-900 text-xs font-medium rounded-btn border border-sky-100 dark:border-white/10 transition-colors flex items-center gap-1.5 shadow-sm"
          >
            {state?.is_paused ? <Play className="w-3.5 h-3.5 stroke-[1.5]" /> : <Pause className="w-3.5 h-3.5 stroke-[1.5]" />}
            <span>{state?.is_paused ? 'Resume' : 'Pause'}</span>
          </button>

          <button
            onClick={handleStep}
            className="px-3 py-1.5 bg-sky-500 hover:bg-sky-700 text-white text-xs font-medium rounded-btn transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <FastForward className="w-3.5 h-3.5 stroke-[1.5]" />
            <span>Step +5 min</span>
          </button>

          <button
            onClick={handleReset}
            className="px-3 py-1.5 bg-white dark:bg-sky-950/60 hover:bg-mist text-ink-600 text-xs font-medium rounded-btn border border-slate-200 dark:border-white/10 transition-colors flex items-center gap-1.5"
            title="Reset to seed 42"
          >
            <RotateCcw className="w-3.5 h-3.5 stroke-[1.5]" />
            <span>Reset (Seed 42)</span>
          </button>
        </div>
      </div>

      {/* Seven Stage Autonomous Resilience Loop Visualizer */}
      <div className="glass-panel p-6 space-y-4">
        <div>
          <h3 className="text-sm font-bold text-ink-900">
            Autonomous Operational Resilience Loop
          </h3>
          <p className="text-xs text-ink-600">
            Every screen answers: what to do next, where, and why.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 text-xs">
          {[
            { step: '1', title: 'Monitor', desc: 'Flow meters & pressure sensors' },
            { step: '2', title: 'Detect', desc: 'IsolationForest leak isolation' },
            { step: '3', title: 'Predict', desc: 'Holt-Winters 24h demand profile' },
            { step: '4', title: 'Prioritize', desc: 'Vulnerable zone impact checks' },
            { step: '5', title: 'Optimize', desc: 'Linear programming allocation' },
            { step: '6', title: 'Intervene', desc: 'SCADA commands & CMMS tickets' },
            { step: '7', title: 'Measure', desc: 'Ground truth live validation' },
          ].map((stage) => (
            <div key={stage.step} className="p-3 bg-white/60 dark:bg-sky-950/30 rounded-btn border border-sky-100 dark:border-white/10 space-y-1">
              <div className="flex items-center gap-1 text-[11px] font-mono text-sky-700 dark:text-sky-300 font-semibold">
                <span>Stage {stage.step}</span>
              </div>
              <div className="font-semibold text-ink-900">{stage.title}</div>
              <p className="text-[11px] text-ink-600">{stage.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
