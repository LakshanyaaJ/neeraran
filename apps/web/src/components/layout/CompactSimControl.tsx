import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Play, Pause, SkipForward } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { api } from '../../api/client';
import { useAuthStore } from '../../store/auth';

export const CompactSimControl: React.FC = () => {
  const { role } = useAuthStore();
  const isAdmin = role === 'admin';

  const { data: state, refetch } = useQuery({
    queryKey: ['compactSimState'],
    queryFn: () => api.getState(),
    refetchInterval: 3000,
  });

  const isPaused = state?.is_paused ?? false;
  const speed = state?.speed ?? 1;

  const handleTogglePlay = async () => {
    if (!isAdmin) {
      toast.error('Only Estate Admin can control the simulator clock.');
      return;
    }
    try {
      await api.controlSim(!isPaused, speed);
      refetch();
      toast.success(isPaused ? 'Simulation running' : 'Simulation paused');
    } catch {
      toast.error('Failed to update simulation');
    }
  };

  const handleSetSpeed = async (newSpeed: number) => {
    if (!isAdmin) {
      toast.error('Only Estate Admin can change simulation speed.');
      return;
    }
    try {
      await api.controlSim(!isPaused, newSpeed);
      refetch();
      toast.success(`Simulation speed set to ${newSpeed}x`);
    } catch {
      toast.error('Failed to set speed');
    }
  };

  const handleNextEvent = async () => {
    if (!isAdmin) {
      toast.error('Only Estate Admin can skip to next event.');
      return;
    }
    try {
      const nextTick = (state?.tick || 0) + 12; // Skip 1 hour
      await api.controlSim(!isPaused, speed, nextTick);
      refetch();
      toast.success('Jumped to next scheduled event (+1h)');
    } catch {
      toast.error('Failed to jump event');
    }
  };

  return (
    <div className="hidden xl:flex items-center gap-1.5 p-1 rounded-full bg-white/75 backdrop-blur-md border border-white/85 shadow-sm text-xs font-mono text-[#0F2236]">
      {/* Play/Pause */}
      <button
        onClick={handleTogglePlay}
        className={`p-1.5 rounded-full transition-colors ${
          !isPaused ? 'bg-[#3A8FDA] text-white' : 'hover:bg-gray-100 text-gray-700'
        }`}
        title={isPaused ? 'Play' : 'Pause'}
      >
        {isPaused ? <Play className="w-3 h-3 fill-current" /> : <Pause className="w-3 h-3 fill-current" />}
      </button>

      {/* Speed Multiplier */}
      <div className="flex items-center gap-0.5 px-1">
        {[1, 5, 20].map((s) => (
          <button
            key={s}
            onClick={() => handleSetSpeed(s)}
            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold transition-colors ${
              speed === s ? 'bg-[#3A8FDA] text-white' : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            {s}x
          </button>
        ))}
      </div>

      {/* Jump to Next Event */}
      <button
        onClick={handleNextEvent}
        className="p-1 hover:bg-gray-100 rounded-full text-gray-600 transition-colors"
        title="Jump to next event"
      >
        <SkipForward className="w-3 h-3 stroke-[1.5]" />
      </button>

      {/* Sim Time Display */}
      <div className="pl-1 pr-2 border-l border-gray-200 text-[11px] text-[#4A5F75]">
        {state?.sim_time ? new Date(state.sim_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '08:00'}
      </div>
    </div>
  );
};
