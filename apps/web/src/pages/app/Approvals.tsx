import React from 'react';
import { ShieldCheck, Check, X, Info } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useAuthStore } from '../../store/auth';

export const ApprovalsPage: React.FC = () => {
  const { role } = useAuthStore();
  const isAdmin = role === 'admin';

  const handleAction = (type: 'approve' | 'reject') => {
    if (!isAdmin) {
      toast.error('Only Estate Admin role can authorize actions in the Approval Queue.');
      return;
    }
    toast.success(type === 'approve' ? 'Action item approved and SCADA dispatched.' : 'Action item rejected.');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-ink-600/10">
        <div>
          <h1 className="text-xl font-bold text-ink-900">
            Human-in-the-Loop Operational Approval Queue
          </h1>
          <p className="text-xs text-ink-600">
            High-consequence pressure modulations, valve isolations, and zone rationing await Admin clearance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className={`glass-pill px-3 py-1 text-xs font-semibold ${
            isAdmin ? 'text-sky-700 dark:text-sky-300' : 'text-amber'
          }`}>
            {isAdmin ? 'Admin Approval Enabled' : 'Viewer: Read-Only Oversight'}
          </span>
        </div>
      </div>

      {!isAdmin && (
        <div className="p-3.5 glass-panel bg-amber/5 border-amber/30 text-xs text-ink-900 flex items-center gap-2.5">
          <Info className="w-4 h-4 text-amber stroke-[1.5] flex-shrink-0" />
          <span>
            You are logged in as <strong>Viewer</strong>. You can inspect pending action items, equity impact checks, and evidence IDs, but approval buttons are disabled. Sign in as <strong>Estate Admin</strong> for operational clearance authority.
          </span>
        </div>
      )}

      {/* Demo Pending Approval Item */}
      <div className="glass-panel p-6 space-y-4 border-l-4 border-l-amber">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-sky-700 dark:text-sky-300 bg-sky-50 dark:bg-sky-950/60 px-2 py-0.5 rounded-btn border border-sky-100 dark:border-white/10">
                REQ-8021
              </span>
              <span className="px-2 py-0.5 text-[10px] bg-coral/10 text-coral font-medium rounded-pill">
                Vulnerable Zone Tag
              </span>
              <span className="px-2 py-0.5 text-[10px] bg-amber/10 text-amber font-medium rounded-pill">
                Awaiting Admin Clearance
              </span>
            </div>

            <h3 className="text-base font-semibold text-ink-900">
              Modulate Pressure on Supply Branch L-2 (Vaigai Girls Hostel Feed)
            </h3>
            <p className="text-xs text-ink-600">
              Reduce line pressure from 2.45 bar to 1.80 bar between 01:00 - 05:00 to curtail nocturnal joint weepage pending morning gasket overhaul.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleAction('reject')}
              disabled={!isAdmin}
              className={`px-3 py-1.5 rounded-btn text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                isAdmin 
                  ? 'bg-white hover:bg-mist text-coral border border-coral/30' 
                  : 'opacity-50 cursor-not-allowed bg-slate-100 text-slate-400'
              }`}
            >
              <X className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>Reject</span>
            </button>

            <button
              onClick={() => handleAction('approve')}
              disabled={!isAdmin}
              className={`px-4 py-1.5 rounded-btn text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm ${
                isAdmin 
                  ? 'bg-sky-500 hover:bg-sky-700 text-white' 
                  : 'opacity-50 cursor-not-allowed bg-slate-300 text-slate-500'
              }`}
            >
              <Check className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>Approve Action</span>
            </button>
          </div>
        </div>

        {/* Equity Impact Audit Box */}
        <div className="p-3 bg-white/70 dark:bg-sky-950/40 rounded-btn border border-sky-100 dark:border-white/10 space-y-1.5 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-leaf">
            <ShieldCheck className="w-4 h-4 stroke-[1.5]" />
            <span>Automated Equity Impact Assessment: Passed</span>
          </div>
          <p className="text-ink-600">
            Minimum dynamic head at top floor sinks remains at 1.45 bar. Vaigai Hostel buffer tank maintains 82 kL (over 18 hrs reserve). Crèche and Clinic are fed via independent Trunk A-1 and remain unaffected.
          </p>
          <div className="pt-1 flex flex-wrap items-center gap-4 text-[11px] text-ink-600">
            <span>Rollback Gate: Trigger if pressure drops below 1.20 bar</span>
            <span className="font-mono text-sky-700 dark:text-sky-300">Evidence: EVID-PRS-4029, EVID-REP-1104</span>
          </div>
        </div>
      </div>
    </div>
  );
};
