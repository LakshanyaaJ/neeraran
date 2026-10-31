import React from 'react';
import { ShieldCheck } from 'lucide-react';

export const ResponsibleAIPage: React.FC = () => {
  const guardrails = [
    {
      title: 'Vulnerable User Protection Rule',
      rule: 'NEVER autonomously restrict or throttle water supply to residential hostels (Cauvery, Krishna, Vaigai), campus health centre, or daycare crèche.',
      status: 'Active Enforced',
      enforcement: 'Hardcoded constraint solver penalty + mandatory human approval gate.',
    },
    {
      title: 'Mandatory Equity Impact Assessment',
      rule: 'Every proposed pressure modulation must certify minimum residual pressure heads (≥ 1.40 bar) at all delicate end-user fixtures prior to plan execution.',
      status: 'Active Enforced',
      enforcement: 'Automated hydraulic simulation audit against pipe elevation topology.',
    },
    {
      title: 'Automated Rollback Guarantees',
      rule: 'Every dispatched valve or pump command carries an autonomous rollback trigger (e.g. if pressure dips below 1.20 bar, open valve to 100% within 8 seconds).',
      status: 'Active Enforced',
      enforcement: 'Embedded SCADA heartbeat safety monitor.',
    },
    {
      title: 'Verifiable Evidence Grounding (Zero Hallucination)',
      rule: 'Every claim, anomaly diagnosis, or plan step must link explicitly to immutable Evidence IDs (EVID-...). Unsubstantiated claims are rejected by the verifier.',
      status: 'Active Enforced',
      enforcement: 'Autonomous verifier audit agent with ground-truth verification.',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-ink-600/10">
        <div>
          <h1 className="text-xl font-bold text-ink-900">
            Responsible AI, Equity Guardrails & Safety Architecture
          </h1>
          <p className="text-xs text-ink-600">
            Principled agent alignment ensuring equity, human authorization, and deterministic fallback reliability.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="glass-pill px-3 py-1 text-xs text-leaf font-medium border-leaf/30 bg-leaf/10">
            Strict Guardrails Active
          </span>
        </div>
      </div>

      <div className="space-y-4">
        {guardrails.map((g, idx) => (
          <div key={idx} className="glass-panel p-5 space-y-2 border-l-4 border-l-leaf">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-leaf stroke-[1.5]" />
                <h3 className="font-semibold text-sm text-ink-900">{g.title}</h3>
              </div>
              <span className="px-2 py-0.5 text-[10px] rounded-pill bg-leaf/10 text-leaf font-medium">
                {g.status}
              </span>
            </div>

            <p className="text-xs text-ink-900 font-medium bg-white/60 dark:bg-sky-950/40 p-3 rounded-btn border border-sky-100 dark:border-white/10">
              {g.rule}
            </p>

            <div className="flex items-center gap-2 text-[11px] text-ink-600">
              <span className="font-semibold">Enforcement:</span>
              <span>{g.enforcement}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
