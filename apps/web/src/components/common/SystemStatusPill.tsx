import React from 'react';
import { useSystemStatusStore } from '../../api/client';
import { Database, WifiOff, ShieldCheck } from 'lucide-react';

export const SystemStatusPill: React.FC = () => {
  const { status, isUsingFallback, isDemoSafeMode, lastUpdated, toggleDemoSafeMode } = useSystemStatusStore();

  if (status === 'demo_safe' || isDemoSafeMode) {
    return (
      <button
        onClick={toggleDemoSafeMode}
        className="glass-pill px-3 py-1 flex items-center gap-1.5 text-xs font-semibold text-azure-700 border-azure-400/40 bg-azure-50/90 shadow-sm cursor-pointer hover:bg-azure-100 transition-colors"
        title="Demo Safe Mode Active (Press Shift+D or click to switch to live)"
      >
        <ShieldCheck className="w-3.5 h-3.5 text-azure-600 stroke-[2]" />
        <span>Demo safe mode</span>
      </button>
    );
  }

  if (status === 'live') {
    return (
      <div
        className="glass-pill px-3 py-1 flex items-center gap-2 text-xs font-medium text-ink-900 border-emerald-500/30 bg-white/70 shadow-sm"
        title={`Live simulation connection. Last sync: ${lastUpdated}. Press Shift+D for Demo Safe Mode.`}
      >
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-emerald-700 font-semibold">Live</span>
        <span className="text-ink-600 font-mono text-[11px] hidden sm:inline">{lastUpdated}</span>
      </div>
    );
  }

  if (status === 'degraded' || isUsingFallback) {
    return (
      <div
        className="glass-pill px-3 py-1 flex items-center gap-2 text-xs font-medium text-amber-700 border-amber-400/40 bg-amber-50/80 shadow-sm"
        title="Operating on local bundled digital twin snapshot."
      >
        <Database className="w-3.5 h-3.5 stroke-[1.5]" />
        <span>Degraded (Snapshot)</span>
      </div>
    );
  }

  return (
    <div
      className="glass-pill px-3 py-1 flex items-center gap-2 text-xs font-medium text-rose-700 border-rose-400/40 bg-rose-50/80 shadow-sm"
      title="Backend unreachable. Press Shift+D for Demo Safe Mode."
    >
      <WifiOff className="w-3.5 h-3.5 stroke-[1.5]" />
      <span>Offline</span>
    </div>
  );
};
