import React, { useState } from 'react';
import { motion, useInView, useReducedMotion } from 'framer-motion';
import { useRef } from 'react';
import { ShieldCheck, Check, X, FileText, Undo2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

export const HumanInCharge: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: true, margin: '-60px' });
  const shouldReduceMotion = useReducedMotion();

  const [decision, setDecision] = useState<'pending' | 'approved' | 'rejected'>('pending');

  const handleApprove = () => {
    setDecision('approved');
    toast.success('Approved: SCADA command dispatched with automated rollback heartbeat.');
  };

  const handleReject = () => {
    setDecision('rejected');
    toast('Action rejected: Plan archived to audit log with reasoning.', {
      icon: '🛡️',
    });
  };

  return (
    <section id="guardrails" ref={containerRef} className="py-24 px-4 sm:px-6 max-w-6xl mx-auto space-y-12 text-left">
      <div className="space-y-3 max-w-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 glass-pill text-xs font-semibold text-leaf border-leaf/30 bg-leaf/10">
          <span>Human-in-the-Loop Guardrail</span>
        </div>
        <h2 className="text-3xl sm:text-4xl font-light text-ink-900 tracking-tight">
          You stay <span className="font-bold text-ink-900">in charge</span>.
        </h2>
        <p className="text-sm sm:text-base text-ink-600">
          The AI proposes, structures, and verifies. You hold the master key. Consequential adjustments never execute blindly.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        {/* Left: Mock Animated Approval Card Sliding In */}
        <motion.div
          initial={{ opacity: 0, x: shouldReduceMotion ? 0 : -40 }}
          animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: -40 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="lg:col-span-7 glass-panel p-6 sm:p-8 space-y-5 border-l-4 border-l-sky-500 bg-white/80 dark:bg-sky-950/40 border border-white/90 dark:border-white/10 shadow-glass"
        >
          {/* Card Meta */}
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-sky-700 dark:text-sky-300 bg-sky-50 dark:bg-sky-950/60 px-2 py-0.5 rounded-btn border border-sky-100 dark:border-white/10">
                REQ-8021
              </span>
              <span className="px-2 py-0.5 text-[10px] bg-coral/10 text-coral font-medium rounded-pill">
                Vulnerable Zone
              </span>
            </div>

            <span className="text-[11px] font-mono text-ink-600">Generated at 02:49 AM</span>
          </div>

          {/* Action Description */}
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-ink-900">
              Modulate Pressure on Supply Branch L-2 (Vaigai Girls Hostel Feed)
            </h3>
            <p className="text-xs text-ink-600">
              Curtails nocturnal joint weepage from 2.45 bar to 1.80 bar during low-occupancy window (01:00 - 05:00).
            </p>
          </div>

          {/* Evidence List */}
          <div className="space-y-2 pt-1">
            <span className="text-[11px] font-semibold text-ink-600 uppercase tracking-wider block">
              Grounded Evidence IDs (Audited by Verifier)
            </span>
            <div className="flex flex-wrap gap-2 text-[11px] font-mono">
              <span className="px-2.5 py-1 bg-white dark:bg-sky-900/40 rounded border border-sky-100 dark:border-white/10 text-ink-900 flex items-center gap-1">
                <FileText className="w-3 h-3 text-sky-500 stroke-[1.5]" />
                EVID-PRS-4029: Residual -0.75 bar
              </span>
              <span className="px-2.5 py-1 bg-white dark:bg-sky-900/40 rounded border border-sky-100 dark:border-white/10 text-ink-900 flex items-center gap-1">
                <FileText className="w-3 h-3 text-amber stroke-[1.5]" />
                EVID-MET-1004: +48.6 L/min bleed
              </span>
              <span className="px-2.5 py-1 bg-white dark:bg-sky-900/40 rounded border border-sky-100 dark:border-white/10 text-ink-900 flex items-center gap-1">
                <Undo2 className="w-3 h-3 text-leaf stroke-[1.5]" />
                Rollback Gate: Trip if &lt; 1.20 bar
              </span>
            </div>
          </div>

          {/* Interactive Decision Action */}
          <div className="pt-3 border-t border-ink-600/10 flex items-center justify-between gap-3">
            {decision === 'pending' ? (
              <>
                <span className="text-xs text-ink-600">Click to authorize simulation dispatch:</span>
                <div className="flex items-center gap-2">
                  <motion.button
                    whileHover={{ scale: 1.02, y: -1 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleReject}
                    className="px-3.5 py-1.5 rounded-btn text-xs font-semibold text-coral bg-white hover:bg-mist border border-coral/30 flex items-center gap-1 transition-colors"
                  >
                    <X className="w-3.5 h-3.5 stroke-[1.5]" />
                    <span>Reject</span>
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.02, y: -1 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleApprove}
                    className="px-4 py-1.5 rounded-btn text-xs font-semibold text-white bg-sky-500 hover:bg-sky-700 shadow-sm flex items-center gap-1.5 transition-colors"
                  >
                    <Check className="w-3.5 h-3.5 stroke-[1.5]" />
                    <span>Approve Action</span>
                  </motion.button>
                </div>
              </>
            ) : decision === 'approved' ? (
              <div className="w-full py-2 px-3 bg-leaf/10 border border-leaf/30 rounded-btn text-xs font-semibold text-leaf flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Check className="w-4 h-4" />
                  Authorized by Estate Admin • SCADA Dispatched
                </span>
                <button
                  onClick={() => setDecision('pending')}
                  className="underline text-[11px] text-ink-600 hover:text-ink-900 font-normal"
                >
                  Reset demo
                </button>
              </div>
            ) : (
              <div className="w-full py-2 px-3 bg-coral/10 border border-coral/30 rounded-btn text-xs font-semibold text-coral flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <X className="w-4 h-4" />
                  Rejected • Archived in SQLite Audit Log
                </span>
                <button
                  onClick={() => setDecision('pending')}
                  className="underline text-[11px] text-ink-600 hover:text-ink-900 font-normal"
                >
                  Reset demo
                </button>
              </div>
            )}
          </div>
        </motion.div>

        {/* Right: Plain sentence on vulnerable users rule */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-6 glass-panel space-y-3 border-l-4 border-l-leaf">
            <div className="flex items-center gap-2 text-ink-900 font-semibold text-sm">
              <ShieldCheck className="w-5 h-5 text-leaf stroke-[1.5]" />
              <span>Vulnerable Users Safety Hard-Lock</span>
            </div>
            <p className="text-xs sm:text-sm text-ink-600 leading-relaxed font-normal">
              Hostels, the health clinic, and the daycare crèche are hard-locked against autonomous throttling: every change requires explicit Admin clearance, passes an equity impact check, and carries an instant rollback trigger.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 text-left">
            <div className="p-3 bg-white/60 dark:bg-sky-950/30 rounded-btn border border-sky-100 dark:border-white/5 space-y-1">
              <span className="text-[10px] text-ink-600 uppercase font-mono">Rollback Latency</span>
              <div className="text-sm font-bold text-ink-900 font-mono">&lt; 8 seconds</div>
              <span className="text-[10px] text-leaf">Autonomous trigger</span>
            </div>
            <div className="p-3 bg-white/60 dark:bg-sky-950/30 rounded-btn border border-sky-100 dark:border-white/5 space-y-1">
              <span className="text-[10px] text-ink-600 uppercase font-mono">Equity Audit</span>
              <div className="text-sm font-bold text-ink-900 font-mono">100% Pass</div>
              <span className="text-[10px] text-leaf">Zero violations logged</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
