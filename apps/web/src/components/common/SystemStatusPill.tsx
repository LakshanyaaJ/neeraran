import React from 'react';
import { useSystemStatusStore } from '../../api/client';
import { Database, WifiOff } from 'lucide-react';

export const SystemStatusPill: React.FC = () => {
  const { status, isUsingFallback, lastUpdated } = useSystemStatusStore();

  if (status === 'live') {
    return (
      <div
        className="glass-pill px-3 py-1 flex items-center gap-2 text-xs font-medium text-ink-900 border-leaf/40 bg-white/70 shadow-sm"
        title={`Live simulation connection. Last sync: ${lastUpdated}`}
      >
        <span className="w-2 h-2 rounded-full bg-leaf animate-pulse" />
        <span className="text-leaf font-semibold">Live</span>
        <span className="text-ink-600 font-mono text-[11px] hidden sm:inline">{lastUpdated}</span>
      </div>
    );
  }

  if (status === 'degraded' || isUsingFallback) {
    return (
      <div
        className="glass-pill px-3 py-1 flex items-center gap-2 text-xs font-medium text-amber border-amber/40 bg-amber/10 shadow-sm"
        title="Operating on local bundled digital twin snapshot."
      >
        <Database className="w-3.5 h-3.5 stroke-[1.5]" />
        <span>Degraded (Snapshot)</span>
      </div>
    );
  }

  return (
    <div
      className="glass-pill px-3 py-1 flex items-center gap-2 text-xs font-medium text-coral border-coral/40 bg-coral/10 shadow-sm"
      title="Backend unreachable."
    >
      <WifiOff className="w-3.5 h-3.5 stroke-[1.5]" />
      <span>Offline</span>
    </div>
  );
};
