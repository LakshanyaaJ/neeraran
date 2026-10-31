import React from 'react';
import { Bot } from 'lucide-react';

export const AgentsPage: React.FC = () => {
  const agentsList = [
    {
      id: 'AGENT-ANOMALY',
      name: 'Anomaly & Leak Detector',
      model: 'IsolationForest + Piezoresistive Residuals',
      status: 'Active',
      purpose: 'Identifies nocturnal weepage and sudden bursts across pipe junctions.',
      evidenceCount: '4 Evidence IDs logged',
    },
    {
      id: 'AGENT-DEMAND',
      name: 'Demand Forecaster',
      model: 'Holt-Winters Diurnal Decomposition',
      status: 'Active',
      purpose: 'Projects 24h block consumption peaks to optimize sump pump schedules.',
      evidenceCount: 'MAPE: 6.2% on test validation',
    },
    {
      id: 'AGENT-PLANNER',
      name: 'Multi-Step Action Planner',
      model: 'Constraint-satisfaction Agent',
      status: 'Standby',
      purpose: 'Generates ordered, multi-step mitigation sequences with rollback gates.',
      evidenceCount: 'Generates structured Action Plans',
    },
    {
      id: 'AGENT-VERIFIER',
      name: 'Evidence & Guardrail Verifier',
      model: 'Ground-truth Audit Rule-engine',
      status: 'Active',
      purpose: 'Rejects unsubstantiated claims or actions violating vulnerable zone protections.',
      evidenceCount: '100% proposition verification check',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-ink-600/10">
        <div>
          <h1 className="text-xl font-bold text-ink-900">
            Autonomous Reasoning & Agent Orchestration
          </h1>
          <p className="text-xs text-ink-600">
            Intelligent multi-agent coordination with strict evidence-grounding and verifier checks.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="glass-pill px-3 py-1 text-xs text-ink-600 font-medium">
            Active Agents: 4
          </span>
          <div className="sim-badge-sticky px-2.5 py-1 text-xs rounded font-medium">
            Seed 42 deterministic
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {agentsList.map((agent) => (
          <div key={agent.id} className="glass-panel p-5 space-y-3">
            <div className="flex items-start justify-between">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <Bot className="w-4 h-4 text-sky-500 stroke-[1.5]" />
                  <span className="font-semibold text-sm text-ink-900">{agent.name}</span>
                </div>
                <span className="font-mono text-[10px] text-ink-600">{agent.id}</span>
              </div>

              <span className="px-2 py-0.5 text-[10px] rounded-pill bg-leaf/10 text-leaf font-medium">
                {agent.status}
              </span>
            </div>

            <p className="text-xs text-ink-600">{agent.purpose}</p>

            <div className="pt-2 border-t border-ink-600/10 flex items-center justify-between text-[11px] text-ink-600">
              <span className="font-mono text-sky-700 dark:text-sky-300">{agent.model}</span>
              <span>{agent.evidenceCount}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
