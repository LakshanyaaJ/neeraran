import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, AlertTriangle, RotateCcw } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { api } from '../../api/client';
import { useAuthStore } from '../../store/auth';

interface CaseDrawerProps {
  caseData: any | null;
  onClose: () => void;
  onRefresh?: () => void;
}

export const CaseDrawer: React.FC<CaseDrawerProps> = ({ caseData, onClose, onRefresh }) => {
  const { role } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'now' | 'why' | 'plan' | 'history'>('now');
  const [isActing, setIsActing] = useState(false);
  const [rejectNote, setRejectNote] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);

  if (!caseData) return null;

  const handleApprove = async () => {
    if (role !== 'admin') {
      toast.error('Only Estate Admin can authorize interventions.');
      return;
    }
    setIsActing(true);
    try {
      const res = await api.decideApproval(caseData.id, 'approved', 'Authorized by Estate Admin from case drawer.');
      if (res.status === 'ok') {
        toast.success(`Intervention for ${caseData.id} approved! Dispatched to CMMS.`);
        if (onRefresh) onRefresh();
        onClose();
      } else {
        toast.error(res.message || 'Approval failed');
      }
    } catch (e) {
      toast.error('Approval failed to dispatch');
    } finally {
      setIsActing(false);
    }
  };

  const handleReject = async () => {
    if (role !== 'admin') {
      toast.error('Only Estate Admin can reject interventions.');
      return;
    }
    setIsActing(true);
    try {
      const res = await api.decideApproval(caseData.id, 'rejected', rejectNote || 'Rejected by Estate Admin.');
      if (res.status === 'ok') {
        toast.success(`Plan for ${caseData.id} rejected and removed from queue.`);
        if (onRefresh) onRefresh();
        onClose();
      } else {
        toast.error(res.message || 'Rejection failed');
      }
    } catch (e) {
      toast.error('Rejection failed');
    } finally {
      setIsActing(false);
    }
  };

  const isLeak = caseData.type === 'leak';
  const isVuln = caseData.plan?.vulnerable_flag || ['BLK-01', 'BLK-02', 'BLK-03', 'BLK-04', 'BLK-05'].includes(caseData.location);

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-hidden">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-[#0F2236]/30 backdrop-blur-sm transition-opacity"
        />

        <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            className="w-screen max-w-xl bg-white shadow-2xl flex flex-col border-l border-white/60"
          >
            {/* Drawer Header */}
            <div className="px-6 py-5 border-b border-[#F2F6FA] flex items-center justify-between bg-[#F2F6FA]/50">
              <div className="flex items-center gap-3">
                <span
                  className={`inline-block w-2.5 h-2.5 rounded-full ${
                    isLeak ? 'bg-[#E5594F] animate-pulse' : 'bg-[#F2A33A]'
                  }`}
                />
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-sans font-semibold text-lg text-[#0F2236]">
                      {caseData.id}
                    </h3>
                    <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-white text-[#4A5F75] border border-gray-200">
                      {caseData.location}
                    </span>
                  </div>
                  <p className="text-xs text-[#4A5F75] mt-0.5">
                    Confidence {(caseData.confidence * 100).toFixed(0)}% • Groundedness {(caseData.groundedness_score * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 text-[#4A5F75] hover:text-[#0F2236] rounded-lg hover:bg-white/80 transition-colors"
              >
                <X className="w-5 h-5 stroke-[1.5]" />
              </button>
            </div>

            {/* Segmented Tabs: Now, Why, Plan, History */}
            <div className="flex border-b border-[#F2F6FA] px-6 bg-white">
              {(['now', 'why', 'plan', 'history'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`py-3 px-4 text-sm font-sans font-medium transition-colors border-b-2 capitalize ${
                    activeTab === tab
                      ? 'border-[#3A8FDA] text-[#3A8FDA]'
                      : 'border-transparent text-[#4A5F75] hover:text-[#0F2236]'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Drawer Content Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Tab 1: NOW */}
              {activeTab === 'now' && (
                <div className="space-y-5">
                  <div className="bg-[#F2F6FA] rounded-2xl p-4 border border-white">
                    <span className="text-xs font-mono text-[#4A5F75]">Live Status Snapshot</span>
                    <div className="grid grid-cols-2 gap-4 mt-3">
                      <div>
                        <div className="text-xs text-[#4A5F75]">Target Entity</div>
                        <div className="text-base font-semibold text-[#0F2236] mt-0.5">{caseData.location}</div>
                      </div>
                      <div>
                        <div className="text-xs text-[#4A5F75]">Classification</div>
                        <div className="text-base font-semibold capitalize text-[#0F2236] mt-0.5">{caseData.type}</div>
                      </div>
                      <div>
                        <div className="text-xs text-[#4A5F75]">Status</div>
                        <div className="text-base font-semibold capitalize text-[#0F2236] mt-0.5">{caseData.status}</div>
                      </div>
                      <div>
                        <div className="text-xs text-[#4A5F75]">Verifier Audit</div>
                        <div className="text-base font-semibold text-[#4CBF86] mt-0.5">
                          {(caseData.groundedness_score * 100).toFixed(0)}% grounded
                        </div>
                      </div>
                    </div>
                  </div>

                  {caseData.top_candidate_segments && caseData.top_candidate_segments.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-[#0F2236] uppercase tracking-wider">Top Candidate Segments (Localizer)</h4>
                      <div className="space-y-2">
                        {caseData.top_candidate_segments.map((seg: any, idx: number) => (
                          <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-white border border-gray-100 shadow-sm">
                            <span className="font-mono text-sm text-[#0F2236] font-medium">{seg.segment_id}</span>
                            <span className="text-xs font-mono text-[#3A8FDA] bg-[#EAF3FD] px-2 py-0.5 rounded-md">
                              {(seg.probability * 100).toFixed(1)}% likelihood
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {caseData.priority_breakdown && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-[#0F2236] uppercase tracking-wider">Prioritizer Multi-Criteria Terms</h4>
                      <div className="p-4 rounded-xl bg-white border border-gray-100 shadow-sm space-y-2 text-xs">
                        <div className="flex justify-between">
                          <span className="text-[#4A5F75]">Loss Rate Score (30%)</span>
                          <span className="font-mono">{caseData.priority_breakdown.loss_rate_score} pts</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#4A5F75]">Population Impact (20%)</span>
                          <span className="font-mono">{caseData.priority_breakdown.people_score} pts</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#4A5F75]">Vulnerable Zone Weight (25%)</span>
                          <span className="font-mono">{caseData.priority_breakdown.vulnerable_score} pts</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#4A5F75]">Storage Urgency (15%)</span>
                          <span className="font-mono">{caseData.priority_breakdown.urgency_reserve_score} pts</span>
                        </div>
                        <div className="pt-2 border-t border-gray-100 flex justify-between font-semibold text-[#0F2236]">
                          <span>Composite Score</span>
                          <span className="font-mono text-sm text-[#3A8FDA]">{caseData.priority_breakdown.total_score}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: WHY (Reasoning with verified Evidence IDs) */}
              {activeTab === 'why' && (
                <div className="space-y-5">
                  <div className="bg-[#EAF3FD]/60 rounded-2xl p-4 border border-[#8FC0EE]/30">
                    <h4 className="text-xs font-semibold text-[#1E5FA8] uppercase tracking-wider mb-2">
                      Autonomous Verifier Reasoning
                    </h4>
                    <p className="text-sm text-[#0F2236] leading-relaxed">
                      {caseData.why_text || 'Synthesizing evidence across hydraulic streams...'}
                    </p>
                  </div>

                  <div className="space-y-3">
                    <h4 className="text-xs font-semibold text-[#0F2236] uppercase tracking-wider">
                      Underlying Evidence Artifacts ({caseData.evidence?.length || 0})
                    </h4>
                    <div className="space-y-2.5">
                      {caseData.evidence?.map((ev: any) => (
                        <div key={ev.id} className="p-3.5 rounded-xl bg-white border border-gray-100 shadow-sm space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-xs font-semibold text-[#3A8FDA] bg-[#EAF3FD] px-2 py-0.5 rounded">
                              [{ev.id}]
                            </span>
                            <span className="text-xs font-mono text-[#4A5F75]">{ev.source}</span>
                          </div>
                          <p className="text-xs text-[#0F2236] font-medium">{ev.note}</p>
                          <div className="flex gap-4 text-xs font-mono text-[#4A5F75] pt-1">
                            <span>Observed: <strong className="text-[#0F2236]">{ev.value} {ev.unit}</strong></span>
                            <span>Baseline: <strong className="text-[#4A5F75]">{ev.baseline} {ev.unit}</strong></span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: PLAN (Multi-step action plan & equity check) */}
              {activeTab === 'plan' && (
                <div className="space-y-5">
                  {isVuln && (
                    <div className="bg-[#FFF4E5] border border-[#F2A33A]/40 rounded-2xl p-4 flex gap-3">
                      <AlertTriangle className="w-5 h-5 text-[#F2A33A] shrink-0 stroke-[1.5]" />
                      <div className="text-xs text-[#0F2236]">
                        <strong className="block font-semibold mb-0.5 text-[#F2A33A]">Vulnerable Zone Guardrail Active</strong>
                        Action touches student residences or health facilities. Algorithmic supply cut-offs are hard-blocked; human Estate Admin authorization required.
                      </div>
                    </div>
                  )}

                  {caseData.plan?.expected_impact && (
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 bg-[#F2F6FA] rounded-xl">
                        <span className="text-xs text-[#4A5F75]">Water Saved</span>
                        <div className="text-base font-semibold font-mono text-[#0F2236] mt-0.5">
                          {Number(caseData.plan.expected_impact.litres_saved_per_day).toLocaleString()} L/day
                        </div>
                      </div>
                      <div className="p-3 bg-[#F2F6FA] rounded-xl">
                        <span className="text-xs text-[#4A5F75]">Value Saved</span>
                        <div className="text-base font-semibold font-mono text-[#4CBF86] mt-0.5">
                          ₹{Number(caseData.plan.expected_impact.rupees_saved_per_day).toLocaleString()} /day
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-[#0F2236] uppercase tracking-wider">Ordered Plan Steps</h4>
                    <div className="space-y-2">
                      {caseData.plan?.steps?.map((step: any) => (
                        <div key={step.order} className="flex gap-3 p-3.5 rounded-xl bg-white border border-gray-100 shadow-sm">
                          <span className="w-6 h-6 rounded-full bg-[#EAF3FD] text-[#3A8FDA] font-mono text-xs font-semibold flex items-center justify-center shrink-0">
                            {step.order}
                          </span>
                          <div className="space-y-1 text-xs">
                            <div className="font-semibold text-[#0F2236] font-mono">{step.tool}</div>
                            <p className="text-[#4A5F75]">{step.reason}</p>
                            <pre className="text-[11px] font-mono bg-gray-50 p-1.5 rounded text-gray-600 overflow-x-auto">
                              {JSON.stringify(step.args)}
                            </pre>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {caseData.plan?.rollback && (
                    <div className="p-3.5 bg-gray-50 rounded-xl border border-gray-200 text-xs">
                      <span className="font-semibold text-[#4A5F75] flex items-center gap-1.5 mb-1">
                        <RotateCcw className="w-3.5 h-3.5" /> Rollback Recipe
                      </span>
                      <p className="text-[#0F2236]">{caseData.plan.rollback.description}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 4: HISTORY */}
              {activeTab === 'history' && (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-[#0F2236] uppercase tracking-wider">Past Maintenance & Verified Ground Truth</h4>
                  <div className="space-y-2 text-xs">
                    <div className="p-3 rounded-xl bg-white border border-gray-100 shadow-sm">
                      <div className="flex justify-between font-mono text-gray-500 mb-1">
                        <span>Day 14 (3 months ago)</span>
                        <span>₹4,200</span>
                      </div>
                      <p className="text-[#0F2236]">Flange weepage on supply trunk. Gasket replaced by Team Alpha.</p>
                    </div>
                    <div className="p-3 rounded-xl bg-white border border-gray-100 shadow-sm">
                      <div className="flex justify-between font-mono text-gray-500 mb-1">
                        <span>Day 45 (45 days ago)</span>
                        <span>₹18,000</span>
                      </div>
                      <p className="text-[#0F2236]">Ground settlement burst on distribution main. High-pressure repair clamp sleeve installed.</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Drawer Actions Footer */}
            <div className="px-6 py-4 border-t border-[#F2F6FA] bg-white">
              {role === 'admin' ? (
                <div className="space-y-3">
                  {showRejectInput && (
                    <input
                      type="text"
                      placeholder="Reason for rejection (logged to audit trail)..."
                      value={rejectNote}
                      onChange={(e) => setRejectNote(e.target.value)}
                      className="w-full text-xs px-3 py-2 rounded-xl border border-gray-200 focus:outline-none focus:border-[#3A8FDA]"
                    />
                  )}
                  <div className="flex gap-3">
                    {showRejectInput ? (
                      <button
                        onClick={handleReject}
                        disabled={isActing}
                        className="flex-1 py-2.5 px-4 rounded-xl text-xs font-medium text-white bg-[#E5594F] hover:bg-[#d04b42] transition-colors"
                      >
                        Confirm Rejection
                      </button>
                    ) : (
                      <button
                        onClick={() => setShowRejectInput(true)}
                        disabled={isActing}
                        className="py-2.5 px-4 rounded-xl text-xs font-medium text-[#E5594F] bg-[#FFF2F0] hover:bg-[#ffe5e3] transition-colors"
                      >
                        Reject
                      </button>
                    )}
                    <button
                      onClick={handleApprove}
                      disabled={isActing}
                      className="flex-1 py-2.5 px-4 rounded-xl text-xs font-medium text-white bg-[#3A8FDA] hover:bg-[#1E5FA8] transition-colors shadow-sm"
                    >
                      {isActing ? 'Authorizing...' : 'Approve & Dispatch Plan'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="py-2 px-3 bg-[#F2F6FA] rounded-xl text-center text-xs text-[#4A5F75] font-medium">
                  Awaiting Estate Admin Authorization • View-Only Mode
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  );
};
