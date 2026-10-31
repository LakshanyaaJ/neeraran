import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  RotateCcw,
  Sliders
} from 'lucide-react';

import { api } from '../../api/client';
import { useAuthStore } from '../../store/auth';

export const ApprovalsPage: React.FC = () => {
  const { role } = useAuthStore();
  const isAdmin = role === 'admin';

  const [reviewNote, setReviewNote] = useState('');
  const [activeActionId, setActiveActionId] = useState<string | null>(null);
  const [isRejecting, setIsRejecting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);

  // Prioritizer weights state (Admin editable)
  const [weights, setWeights] = useState({
    w_loss: 0.30,
    w_pop: 0.20,
    w_vuln: 0.25,
    w_time: 0.15,
    w_cost: 0.10,
  });

  // 1. Fetch Active Cases with Plans
  const { data: cases = [], refetch: refetchCases } = useQuery({
    queryKey: ['approvalsCases'],
    queryFn: () => api.getCases(),
    refetchInterval: 3000,
  });

  // 2. Fetch Active Plan
  const { refetch: refetchPlan } = useQuery({
    queryKey: ['approvalsPlan'],
    queryFn: () => api.getPlan(),
    refetchInterval: 3000,
  });

  // 3. Fetch Audit History of Past Approvals
  const { data: auditLogs = [], refetch: refetchAudit } = useQuery({
    queryKey: ['approvalsAudit'],
    queryFn: () => api.getAudit(),
    refetchInterval: 4000,
  });

  const refetchAll = () => {
    refetchCases();
    refetchPlan();
    refetchAudit();
  };

  const handleDecision = async (approvalId: string, decision: 'approved' | 'rejected') => {
    if (!isAdmin) {
      toast.error('Only Estate Admin role can authorize actions in the Approval Queue.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await api.decideApproval(
        approvalId,
        decision,
        reviewNote || (decision === 'approved' ? 'Approved by Estate Admin' : 'Rejected by Estate Admin')
      );

      if (res.status === 'ok') {
        toast.success(decision === 'approved' ? 'Intervention approved & dispatched to SCADA/CMMS!' : 'Plan rejected and removed from queue.');
        setReviewNote('');
        setActiveActionId(null);
        setIsRejecting(false);
        refetchAll();
      } else {
        toast.error(res.message || 'Action failed');
      }
    } catch (e) {
      toast.error('Failed to submit approval decision');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveWeights = async () => {
    if (!isAdmin) {
      toast.error('Only Estate Admin can update algorithmic prioritizer weights.');
      return;
    }
    try {
      await api.updatePrioritizerWeights(weights);
      toast.success('Prioritizer weights successfully updated & queue re-ranked!');
      setShowConfigModal(false);
      refetchAll();
    } catch (e) {
      toast.error('Failed to update weights');
    }
  };

  // Filter pending approval items defensively
  const safeCases = Array.isArray(cases) ? cases : [];
  const safeAuditLogs = Array.isArray(auditLogs) ? auditLogs : [];
  const pendingCases = safeCases.filter((c: any) => c.plan && (c.plan.needs_approval || c.status === 'actionable'));
  const approvedAudits = safeAuditLogs.filter((a: any) => a.action_type?.includes('APPROVAL') || a.action_type?.includes('IMPACT'));

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-white/60">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-sans font-semibold text-2xl text-[#0F2236] tracking-tight">
              Human-in-the-Loop Operational Clearance Queue
            </h1>
            <span
              className={`text-xs font-mono px-2 py-0.5 rounded-full ${
                isAdmin ? 'bg-[#EAF3FD] text-[#3A8FDA]' : 'bg-[#FFF4E5] text-[#F2A33A]'
              }`}
            >
              {isAdmin ? 'Estate Admin: Authority Active' : 'Viewer: Read-Only Audit'}
            </span>
          </div>
          <p className="text-xs text-[#4A5F75] font-mono mt-1">
            Consequential actions (valve isolations, pressure modulation, pump dispatching) await human sign-off
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={() => setShowConfigModal(true)}
            className="flex items-center gap-2 py-2 px-3.5 rounded-xl text-xs font-medium text-[#0F2236] bg-white border border-gray-200 hover:bg-gray-50 shadow-sm transition-all"
          >
            <Sliders className="w-3.5 h-3.5 text-[#3A8FDA]" />
            Configure Prioritizer Weights
          </button>
        )}
      </div>

      {/* Viewer Read-Only Notice Banner */}
      {!isAdmin && (
        <div className="p-4 rounded-2xl bg-[#FFF4E5] border border-[#F2A33A]/40 flex items-center gap-3 text-xs text-[#0F2236]">
          <AlertTriangle className="w-5 h-5 text-[#F2A33A] shrink-0 stroke-[1.5]" />
          <span>
            You are viewing this queue as <strong>Viewer</strong>. You can inspect proposed steps, equity impact audits, and evidence IDs, but clearance buttons are locked. Sign in as <strong>Estate Admin</strong> for operational clearance authorization.
          </span>
        </div>
      )}

      {/* PENDING APPROVAL QUEUE */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-sans font-semibold text-lg text-[#0F2236]">
            Pending Remediation Plans ({pendingCases.length})
          </h2>
          <span className="text-xs font-mono text-[#4A5F75]">
            Strict Guardrail: Vulnerable residential lines enforce mandatory equity checks
          </span>
        </div>

        {pendingCases.length === 0 ? (
          <div className="p-12 text-center rounded-3xl bg-white/70 border border-white/80 space-y-2">
            <CheckCircle2 className="w-8 h-8 text-[#4CBF86] mx-auto stroke-[1.5]" />
            <h3 className="font-semibold text-sm text-[#0F2236]">Approval Queue Clean</h3>
            <p className="text-xs text-[#4A5F75]">All consequential interventions have been reviewed and dispatched.</p>
          </div>
        ) : (
          pendingCases.map((c: any) => {
            const isVuln = c.plan?.vulnerable_flag || ['BLK-01', 'BLK-02', 'BLK-03', 'BLK-04', 'BLK-05'].includes(c.location);
            const approvalId = `APP-${c.id}`;

            return (
              <div
                key={c.id}
                className="p-6 rounded-3xl bg-white/80 backdrop-blur-xl border border-white/90 shadow-md space-y-5"
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-[#3A8FDA] bg-[#EAF3FD] px-2.5 py-0.5 rounded">
                        {approvalId}
                      </span>
                      <h3 className="font-sans font-semibold text-base text-[#0F2236]">
                        Automated Plan for {c.location} ({c.type.toUpperCase()})
                      </h3>
                      {isVuln && (
                        <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-[#FFF4E5] text-[#F2A33A] border border-[#F2A33A]/30 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> Vulnerable Sector
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#4A5F75] mt-1">
                      Target Entity: <strong className="text-[#0F2236]">{c.location}</strong> • Confidence: <strong className="text-[#0F2236]">{(c.confidence * 100).toFixed(0)}%</strong> • Verifier Groundedness: <strong className="text-[#4CBF86]">{(c.groundedness_score * 100).toFixed(0)}%</strong>
                    </p>
                  </div>

                  {c.plan?.expected_impact && (
                    <div className="flex items-center gap-4 text-xs font-mono bg-[#F2F6FA] px-3.5 py-2 rounded-xl shrink-0">
                      <div>
                        <div className="text-gray-400">Est. Water Saved</div>
                        <div className="font-bold text-[#0F2236]">{Number(c.plan.expected_impact.litres_saved_per_day).toLocaleString()} L/day</div>
                      </div>
                      <div className="h-6 w-px bg-gray-200" />
                      <div>
                        <div className="text-gray-400">Value Saved</div>
                        <div className="font-bold text-[#4CBF86]">₹{Number(c.plan.expected_impact.rupees_saved_per_day).toLocaleString()}/day</div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Mandatory Equity Impact Check (Vulnerable Zones) */}
                {isVuln && (
                  <div className="p-4 rounded-2xl bg-[#FFF8EE] border border-[#F2A33A]/30 text-xs space-y-1">
                    <strong className="text-[#F2A33A] font-semibold flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4" /> Mandatory Equity Impact Audit
                    </strong>
                    <p className="text-[#0F2236] leading-relaxed">
                      {c.plan?.equity_check ||
                        'Target block houses student residences or health facilities. Algorithmic shut-offs are hard-blocked: line pressure can be throttled, but bypass minimum must hold.'}
                    </p>
                  </div>
                )}

                {/* Ordered Plan Steps */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-[#0F2236]">Ordered Plan Steps</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {c.plan?.steps?.map((step: any) => (
                      <div key={step.order} className="p-3.5 rounded-xl bg-white border border-gray-100 shadow-sm space-y-1.5 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-[#EAF3FD] text-[#3A8FDA] font-mono font-bold text-[11px] flex items-center justify-center shrink-0">
                            {step.order}
                          </span>
                          <span className="font-mono font-semibold text-[#0F2236]">{step.tool}</span>
                        </div>
                        <p className="text-[#4A5F75] line-clamp-2">{step.reason}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Rollback Step & Evidence IDs */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-[#4A5F75]">Attached Evidence:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {c.evidence?.map((ev: any) => (
                        <span key={ev.id} className="font-mono text-[11px] bg-[#EAF3FD] text-[#3A8FDA] px-2 py-0.5 rounded">
                          [{ev.id}]
                        </span>
                      ))}
                    </div>
                  </div>

                  {c.plan?.rollback && (
                    <span className="font-mono text-[11px] text-[#4A5F75] flex items-center gap-1">
                      <RotateCcw className="w-3.5 h-3.5" /> Rollback: {c.plan.rollback.tool}
                    </span>
                  )}
                </div>

                {/* Action Authorization Controls (Admin Only) */}
                <div className="pt-3 border-t border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex-1">
                    {isAdmin && activeActionId === c.id && (
                      <input
                        type="text"
                        placeholder="Review note (e.g. 'Confirmed with warden; proceed with bypass')..."
                        value={reviewNote}
                        onChange={(e) => setReviewNote(e.target.value)}
                        className="w-full text-xs px-3.5 py-2 rounded-xl border border-gray-200 focus:outline-none focus:border-[#3A8FDA]"
                      />
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {isAdmin ? (
                      <>
                        {activeActionId !== c.id ? (
                          <>
                            <button
                              onClick={() => {
                                setActiveActionId(c.id);
                                setIsRejecting(true);
                              }}
                              aria-label={`Reject intervention plan for ${c.location}`}
                              className="py-2 px-4 rounded-xl text-xs font-medium text-[#E5594F] bg-[#FFF2F0] hover:bg-[#ffe5e3] focus:outline-none focus:ring-2 focus:ring-rose-500 focus:ring-offset-1 transition-colors"
                            >
                              Reject Plan
                            </button>
                            <button
                              onClick={() => {
                                setActiveActionId(c.id);
                                setIsRejecting(false);
                              }}
                              aria-label={`Authorize and dispatch intervention plan for ${c.location}`}
                              className="py-2 px-5 rounded-xl text-xs font-medium text-white bg-[#3A8FDA] hover:bg-[#1E5FA8] focus:outline-none focus:ring-2 focus:ring-azure-500 focus:ring-offset-1 transition-colors shadow-sm"
                            >
                              Authorize & Dispatch
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              onClick={() => {
                                setActiveActionId(null);
                                setReviewNote('');
                              }}
                              className="py-2 px-3 rounded-xl text-xs font-medium text-gray-500 hover:bg-gray-100"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => handleDecision(approvalId, isRejecting ? 'rejected' : 'approved')}
                              disabled={isSubmitting}
                              className={`py-2 px-5 rounded-xl text-xs font-medium text-white shadow-sm transition-colors ${
                                isRejecting ? 'bg-[#E5594F] hover:bg-[#d04b42]' : 'bg-[#3A8FDA] hover:bg-[#1E5FA8]'
                              }`}
                            >
                              {isSubmitting ? 'Recording...' : isRejecting ? 'Confirm Rejection' : 'Confirm Authorization'}
                            </button>
                          </>
                        )}
                      </>
                    ) : (
                      <span className="text-xs font-mono text-[#4A5F75] bg-[#F2F6FA] px-3 py-1.5 rounded-xl">
                        Awaiting Estate Admin Clearance
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* RECENT CLEARANCE & MEASURED IMPACT HISTORY TABLE */}
      <div className="p-6 rounded-3xl bg-white/80 backdrop-blur-xl border border-white/90 shadow-md space-y-4">
        <div>
          <h3 className="font-sans font-semibold text-base text-[#0F2236]">
            Authorized Interventions & Measured Impact
          </h3>
          <p className="text-xs text-[#4A5F75] mt-0.5">
            Post-execution verification comparing counterfactual estimates against observed telemetry
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-sans">
            <thead>
              <tr className="border-b border-gray-100 text-[#4A5F75] font-mono text-[11px]">
                <th className="py-2.5 px-3">Approval ID</th>
                <th className="py-2.5 px-3">Actor / Reviewer</th>
                <th className="py-2.5 px-3">Action Type</th>
                <th className="py-2.5 px-3">Target Entity</th>
                <th className="py-2.5 px-3">Details & Variance</th>
                <th className="py-2.5 px-3 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {approvedAudits.slice(0, 8).map((log: any) => (
                <tr key={log.id} className="hover:bg-gray-50/50">
                  <td className="py-2.5 px-3 font-mono font-medium text-[#3A8FDA]">{log.target_resource}</td>
                  <td className="py-2.5 px-3 text-[#0F2236] font-medium">{log.actor}</td>
                  <td className="py-2.5 px-3">
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-gray-100 text-gray-700">
                      {log.action_type}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-gray-500">{log.target_resource}</td>
                  <td className="py-2.5 px-3 text-gray-600 line-clamp-1">{log.details}</td>
                  <td className="py-2.5 px-3 text-right font-mono text-gray-400">
                    {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'Recent'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* PRIORITIZER WEIGHTS CONFIGURATION MODAL */}
      <AnimatePresence>
        {showConfigModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowConfigModal(false)}
              className="absolute inset-0 bg-[#0F2236]/30 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="relative w-full max-w-lg bg-white rounded-3xl p-6 shadow-2xl border border-white space-y-5 z-10"
            >
              <div>
                <h3 className="font-sans font-semibold text-lg text-[#0F2236]">Prioritizer Algorithmic Weights</h3>
                <p className="text-xs text-[#4A5F75] mt-0.5">
                  Adjust multi-criteria optimization terms. The sum must reflect operational priorities.
                </p>
              </div>

              <div className="space-y-4 text-xs font-mono">
                <div>
                  <div className="flex justify-between mb-1">
                    <span>Loss Rate Weight (w_loss):</span>
                    <strong className="text-[#3A8FDA]">{(weights.w_loss * 100).toFixed(0)}%</strong>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={weights.w_loss}
                    onChange={(e) => setWeights({ ...weights, w_loss: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span>Population Affected Weight (w_pop):</span>
                    <strong className="text-[#3A8FDA]">{(weights.w_pop * 100).toFixed(0)}%</strong>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={weights.w_pop}
                    onChange={(e) => setWeights({ ...weights, w_pop: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span>Vulnerable Zone Weight (w_vuln):</span>
                    <strong className="text-[#3A8FDA]">{(weights.w_vuln * 100).toFixed(0)}%</strong>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={weights.w_vuln}
                    onChange={(e) => setWeights({ ...weights, w_vuln: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span>Storage Urgency Weight (w_time):</span>
                    <strong className="text-[#3A8FDA]">{(weights.w_time * 100).toFixed(0)}%</strong>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={weights.w_time}
                    onChange={(e) => setWeights({ ...weights, w_time: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
                <button
                  onClick={() => setShowConfigModal(false)}
                  className="py-2 px-4 rounded-xl text-xs font-medium text-gray-500 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveWeights}
                  className="py-2 px-5 rounded-xl text-xs font-medium text-white bg-[#3A8FDA] hover:bg-[#1E5FA8] shadow-sm"
                >
                  Save & Re-rank Queue
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
