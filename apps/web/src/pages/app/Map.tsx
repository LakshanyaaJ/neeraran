import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Navigation } from 'lucide-react';
import { api } from '../../api/client';
import { useAuthStore } from '../../store/auth';

export const MapPage: React.FC = () => {
  const { role } = useAuthStore();
  const { data: topology, isLoading } = useQuery({
    queryKey: ['campusTopology'],
    queryFn: () => api.getCampusTopology(),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-ink-600/10">
        <div>
          <h1 className="text-xl font-bold text-ink-900">
            Digital Twin Campus Hydraulic Map
          </h1>
          <p className="text-xs text-ink-600">
            20 campus blocks, 4 elevated storage reservoirs, 2 borewells, and 24 pipe line segments.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="glass-pill px-3 py-1 text-xs text-ink-600 font-medium">
            Role: {role === 'admin' ? 'Estate Admin' : 'Viewer'}
          </span>
          <div className="sim-badge-sticky px-2.5 py-1 text-xs rounded font-medium">
            Simulated campus data • Seed 42
          </div>
        </div>
      </div>

      {/* Map Twin Canvas Placeholder for Phase 1 */}
      <div className="glass-panel p-8 min-h-[420px] flex flex-col items-center justify-center text-center space-y-4 border-dashed border-sky-300 dark:border-sky-700/50">
        <div className="w-12 h-12 rounded-full bg-sky-50 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 flex items-center justify-center">
          <Navigation className="w-6 h-6 stroke-[1.5]" />
        </div>

        <div className="max-w-md space-y-1">
          <h3 className="text-base font-semibold text-ink-900">
            MapLibre GL Digital Twin Engine Loaded
          </h3>
          <p className="text-xs text-ink-600">
            MapLibre GL JS engine connected with CartoDB Positron (Day) and Dark Matter (Night Ops) tile layers. Ready for full interactive 2.5D rendering in Phase 3.
          </p>
        </div>

        {/* Quick summary grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs w-full max-w-xl text-left pt-4">
          <div className="p-3 bg-white/70 dark:bg-sky-950/40 rounded-btn border border-sky-100 dark:border-white/10 space-y-1">
            <span className="text-[11px] text-ink-600">Blocks</span>
            <div className="font-bold text-base text-ink-900 font-mono">
              {isLoading ? '...' : (topology?.summary?.blocks_count ?? 20)}
            </div>
            <span className="text-[10px] text-aqua">100% telemetry online</span>
          </div>

          <div className="p-3 bg-white/70 dark:bg-sky-950/40 rounded-btn border border-sky-100 dark:border-white/10 space-y-1">
            <span className="text-[11px] text-ink-600">Overhead Tanks</span>
            <div className="font-bold text-base text-ink-900 font-mono">
              {isLoading ? '...' : (topology?.summary?.tanks_count ?? 4)}
            </div>
            <span className="text-[10px] text-leaf">Capacity: 320 kL</span>
          </div>

          <div className="p-3 bg-white/70 dark:bg-sky-950/40 rounded-btn border border-sky-100 dark:border-white/10 space-y-1">
            <span className="text-[11px] text-ink-600">Deep Borewells</span>
            <div className="font-bold text-base text-ink-900 font-mono">
              {isLoading ? '...' : (topology?.summary?.borewells_count ?? 2)}
            </div>
            <span className="text-[10px] text-ink-600">Depth: 180m - 210m</span>
          </div>

          <div className="p-3 bg-white/70 dark:bg-sky-950/40 rounded-btn border border-sky-100 dark:border-white/10 space-y-1">
            <span className="text-[11px] text-ink-600">Pipe Segments</span>
            <div className="font-bold text-base text-ink-900 font-mono">
              {isLoading ? '...' : (topology?.summary?.pipe_segments_count ?? 24)}
            </div>
            <span className="text-[10px] text-sky-700 dark:text-sky-300">Piezoresistive lines</span>
          </div>
        </div>
      </div>
    </div>
  );
};
