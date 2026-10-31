import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { Play, Pause, FastForward, RotateCcw } from 'lucide-react';
import { api } from '../../api/client';
import { useAuthStore } from '../../store/auth';

export const SimulationPage: React.FC = () => {
  const { role } = useAuthStore();
  const isAdmin = role === 'admin';

  const { data: state, refetch } = useQuery({
    queryKey: ['simStateControl'],
    queryFn: () => api.getSimulationState(),
    refetchInterval: 2500,
  });

  const handleSpeed = async (speed: 1 | 5 | 20) => {
    if (!isAdmin) {
      toast.error('Simulation speed control requires Estate Admin role.');
      return;
    }
    await api.setSpeed(speed);
    refetch();
    toast.success(`Speed updated to ${speed}x`);
  };

  const handleTogglePause = async () => {
    if (!isAdmin) {
      toast.error('Simulation pause/play requires Estate Admin role.');
      return;
    }
    const next = !state?.is_paused;
    await api.togglePause(next);
    refetch();
    toast.success(next ? 'Simulation clock paused' : 'Simulation clock running');
  };

  const handleStep = async (mins: number) => {
    if (!isAdmin) {
      toast.error('Stepping simulation requires Estate Admin role.');
      return;
    }
    await api.stepTick(mins);
    refetch();
    toast.success(`Stepped forward +${mins} minutes`);
  };

  const handleReset = async () => {
    if (!isAdmin) {
      toast.error('Resetting simulator requires Estate Admin role.');
      return;
    }
    await api.reset(42);
    refetch();
    toast.success('Reset simulator to seed 42');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-ink-600/10">
        <div>
          <h1 className="text-xl font-bold text-ink-900">
            Physical Digital Twin Simulation Controller
          </h1>
          <p className="text-xs text-ink-600">
            Deterministic state engine executing at 10Hz with diurnal hydraulic dynamics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="sim-badge-sticky px-2.5 py-1 text-xs rounded font-medium">
            Seed 42 • Repeatable Demos
          </div>
        </div>
      </div>

      {/* Control Panel Bento */}
      <div className="glass-panel p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-ink-600/10 pb-4">
          <div className="space-y-0.5">
            <span className="text-xs text-ink-600 font-medium">Simulation Clock Status</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-ink-900">
                Tick #{state?.tick ?? 0}
              </span>
              <span className="text-xs font-mono text-sky-700 dark:text-sky-300">
                ({state?.sim_time_iso ? new Date(state.sim_time_iso).toLocaleTimeString() : '07:15:00 AM'})
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 text-xs font-semibold rounded-pill ${
              state?.is_paused ? 'bg-amber/10 text-amber' : 'bg-leaf/10 text-leaf'
            }`}>
              {state?.is_paused ? 'Paused' : 'Active Live'}
            </span>
            <span className="px-2.5 py-1 text-xs font-semibold rounded-pill bg-sky-50 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 border border-sky-100 dark:border-white/10 font-mono">
              {state?.speed ?? 1}x Speed
            </span>
          </div>
        </div>

        {/* Speed Buttons */}
        <div className="space-y-2">
          <span className="text-xs font-semibold text-ink-900">Clock Multiplier</span>
          <div className="flex items-center gap-2">
            {([1, 5, 20] as const).map((spd) => (
              <button
                key={spd}
                onClick={() => handleSpeed(spd)}
                className={`px-4 py-2 text-xs font-semibold rounded-btn transition-colors ${
                  state?.speed === spd
                    ? 'bg-sky-500 text-white shadow-sm'
                    : 'bg-white/70 dark:bg-sky-950/40 hover:bg-white text-ink-900 border border-sky-100 dark:border-white/10'
                }`}
              >
                {spd}x Acceleration
              </button>
            ))}
          </div>
        </div>

        {/* Step & Action Controls */}
        <div className="space-y-2 pt-2">
          <span className="text-xs font-semibold text-ink-900">Step Clock & Re-sync</span>
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={handleTogglePause}
              className="px-4 py-2 bg-white dark:bg-sky-950/60 hover:bg-sky-50 text-ink-900 text-xs font-semibold rounded-btn border border-sky-100 dark:border-white/10 flex items-center gap-2 shadow-sm"
            >
              {state?.is_paused ? <Play className="w-3.5 h-3.5 stroke-[1.5]" /> : <Pause className="w-3.5 h-3.5 stroke-[1.5]" />}
              <span>{state?.is_paused ? 'Resume Clock' : 'Pause Clock'}</span>
            </button>

            <button
              onClick={() => handleStep(1)}
              className="px-3.5 py-2 bg-sky-50 dark:bg-sky-950/60 hover:bg-sky-100 text-sky-700 dark:text-sky-300 text-xs font-semibold rounded-btn border border-sky-100 dark:border-white/10 flex items-center gap-1.5"
            >
              <FastForward className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>+1 min</span>
            </button>

            <button
              onClick={() => handleStep(5)}
              className="px-3.5 py-2 bg-sky-50 dark:bg-sky-950/60 hover:bg-sky-100 text-sky-700 dark:text-sky-300 text-xs font-semibold rounded-btn border border-sky-100 dark:border-white/10 flex items-center gap-1.5"
            >
              <FastForward className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>+5 min</span>
            </button>

            <button
              onClick={() => handleStep(15)}
              className="px-3.5 py-2 bg-sky-50 dark:bg-sky-950/60 hover:bg-sky-100 text-sky-700 dark:text-sky-300 text-xs font-semibold rounded-btn border border-sky-100 dark:border-white/10 flex items-center gap-1.5"
            >
              <FastForward className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>+15 min</span>
            </button>

            <button
              onClick={handleReset}
              className="px-4 py-2 bg-white dark:bg-sky-950/60 hover:bg-mist text-ink-600 text-xs font-medium rounded-btn border border-slate-200 dark:border-white/10 flex items-center gap-2"
              title="Reset to seed 42"
            >
              <RotateCcw className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>Reset Seed (42)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
