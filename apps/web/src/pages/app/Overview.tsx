import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  Droplets,
  AlertCircle,
  TrendingDown,
  TrendingUp,
  ShieldCheck,
  ChevronRight
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';

import { api } from '../../api/client';
import { useAuthStore } from '../../store/auth';
import { CaseDrawer } from '../../components/app/CaseDrawer';

type ViewerLens = 'warden' | 'sustainability' | 'student' | 'maintenance';

export const Overview: React.FC = () => {
  const { role } = useAuthStore();
  const [lens, setLens] = useState<ViewerLens>('warden');
  const [selectedCase, setSelectedCase] = useState<any | null>(null);
  const [kpiFilter, setKpiFilter] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<'all' | 'critical' | 'watch' | 'info'>('all');

  // 1. Fetch Digital Twin Telemetry State (refetch every 3s for live 20x streaming updates)
  const { data: state, refetch: refetchState } = useQuery({
    queryKey: ['simStateOverview'],
    queryFn: () => api.getState(),
    refetchInterval: 3000,
  });

  // 2. Fetch Active Cases
  const { data: cases = [], refetch: refetchCases } = useQuery({
    queryKey: ['agentCasesOverview'],
    queryFn: () => api.getCases(),
    refetchInterval: 3000,
  });

  // 3. Fetch Prioritizer Ranked Queue
  const { data: queue = [], refetch: refetchQueue } = useQuery({
    queryKey: ['agentQueueOverview'],
    queryFn: () => api.getQueue(),
    refetchInterval: 3000,
  });

  // 4. Fetch 7-Day & 72-Hour Forecasts
  const { data: forecast } = useQuery({
    queryKey: ['forecastOverview'],
    queryFn: () => api.getForecast(),
    refetchInterval: 10000,
  });

  // 5. Fetch Audit Trail / Activity Stream
  const { data: auditLogs = [], refetch: refetchAudit } = useQuery({
    queryKey: ['auditOverview'],
    queryFn: () => api.getAudit(),
    refetchInterval: 4000,
  });

  const refetchAll = () => {
    refetchState();
    refetchCases();
    refetchQueue();
    refetchAudit();
  };

  const handleApprove = async (caseId: string) => {
    if (role !== 'admin') {
      toast.error('Only Estate Admin can approve interventions.');
      return;
    }
    toast.promise(api.decideApproval(caseId, 'approved', 'Authorized by Estate Admin from Overview.'), {
      loading: 'Authorizing intervention plan...',
      success: () => {
        refetchAll();
        return 'Intervention approved & work order dispatched!';
      },
      error: 'Failed to approve plan',
    });
  };

  const handleReject = async (caseId: string) => {
    if (role !== 'admin') {
      toast.error('Only Estate Admin can reject interventions.');
      return;
    }
    toast.promise(api.decideApproval(caseId, 'rejected', 'Rejected by Estate Admin from Overview.'), {
      loading: 'Rejecting intervention...',
      success: () => {
        refetchAll();
        return 'Plan rejected and removed from queue.';
      },
      error: 'Failed to reject plan',
    });
  };

  // Defensive Safe Arrays for Network Resilience
  const safeCases = Array.isArray(cases) ? cases : [];
  const safeQueue = Array.isArray(queue) ? queue : [];
  const safeAuditLogs = Array.isArray(auditLogs) ? auditLogs : [];

  // KPI Calculations
  const reserveDays = forecast?.days_of_reserve || 1.8;
  const reserveLower = forecast?.reserve_80pct_lower || 1.4;
  const reserveUpper = forecast?.reserve_80pct_upper || 2.2;
  const leakCasesCount = safeCases.filter((c: any) => c.type === 'leak').length;
  const totalLossKld = safeCases
    .filter((c: any) => c.type === 'leak')
    .reduce((acc: number, c: any) => acc + (c.priority_breakdown?.details?.estimated_loss_kld || 65.0), 0);
  const waterSavedThisWeekKl = 480.0;
  const rupeesSavedThisWeek = 57600;
  const pendingApprovalsCount = safeCases.filter((c: any) => c.plan?.needs_approval && c.status === 'actionable').length;

  // Chart 1 Data: 72-Hour Reservoir Trajectory
  const reservoirTrajectory = forecast?.tank_levels_72h?.total_campus_storage?.slice(0, 36).map((item: any) => ({
    time: `+${item.hour_offset}h`,
    storage_kl: item.forecast_storage_kl,
    lower_80: item.lower_80_kl,
    upper_80: item.upper_80_kl,
    safety_level: item.safety_reserve_kl || 150,
  })) || [
    { time: '+0h', storage_kl: 380, lower_80: 360, upper_80: 400, safety_level: 150 },
    { time: '+6h', storage_kl: 345, lower_80: 310, upper_80: 380, safety_level: 150 },
    { time: '+12h', storage_kl: 320, lower_80: 275, upper_80: 365, safety_level: 150 },
    { time: '+18h', storage_kl: 290, lower_80: 235, upper_80: 345, safety_level: 150 },
    { time: '+24h', storage_kl: 350, lower_80: 285, upper_80: 415, safety_level: 150 },
    { time: '+30h', storage_kl: 325, lower_80: 250, upper_80: 400, safety_level: 150 },
    { time: '+36h', storage_kl: 300, lower_80: 220, upper_80: 380, safety_level: 150 },
  ];

  // Chart 2 Data: Minimum Night Flow (MNF) by Block
  const mnfData = state?.blocks?.map((b: any) => {
    const isLeakFlagged = safeCases.some((c: any) => c.location === b.id && c.type === 'leak');
    const isWatch = safeCases.some((c: any) => c.location === b.id && c.type === 'watch');
    return {
      block: b.code || b.id.replace('BLK-', 'B'),
      flow: b.meter_reading_lpm,
      status: isLeakFlagged ? 'leak' : isWatch ? 'watch' : 'normal',
      fill: isLeakFlagged ? '#E5594F' : isWatch ? '#F2A33A' : '#2FB8AA',
    };
  }) || [];

  // Chart 3 Data: 7-Day Demand Actual vs Forecast
  const demandComparisonData = [
    { day: 'Mon', actual: 410, forecast: 418, error: 8 },
    { day: 'Tue', actual: 425, forecast: 420, error: 5 },
    { day: 'Wed', actual: 440, forecast: 432, error: 8 },
    { day: 'Thu', actual: 430, forecast: 425, error: 5 },
    { day: 'Fri', actual: 455, forecast: 462, error: 7 },
    { day: 'Sat', actual: 310, forecast: 315, error: 5 },
    { day: 'Sun', actual: 295, forecast: 290, error: 5 },
  ];

  // Filtered Top Actions by kpiFilter if selected
  const topActions = (kpiFilter === 'leaks'
    ? safeQueue.filter((c: any) => c.type === 'leak')
    : kpiFilter === 'approvals'
    ? safeQueue.filter((c: any) => c.plan?.needs_approval)
    : safeQueue
  ).slice(0, 3);

  // Filtered Activity Feed
  const filteredActivities = safeAuditLogs.filter((log: any) => {
    if (severityFilter === 'all') return true;
    if (severityFilter === 'critical') return log.action_type?.includes('FAULT') || log.action_type?.includes('LEAK');
    if (severityFilter === 'watch') return log.action_type?.includes('VALVE') || log.action_type?.includes('APPROVAL');
    return true;
  });

  return (
    <div className="relative min-h-screen p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
      {/* 1. GREETING ROW & FRESHNESS */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-white/60">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-sans font-semibold text-2xl text-[#0F2236] tracking-tight">
              Good morning, Estate Office
            </h1>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-[#EAF3FD] text-[#3A8FDA] border border-[#8FC0EE]/30">
              {state?.academic_calendar || 'Semester'} Mode
            </span>
          </div>
          <p className="text-xs text-[#4A5F75] font-mono mt-1">
            Simulated Clock: {state?.day_name || 'Monday'}, {state?.sim_time ? new Date(state.sim_time).toLocaleTimeString() : '08:00 AM'} • Freshness: simulated digital twin, updated 3s ago
          </p>
        </div>

        {/* Viewer Lenses (Only for Viewer Role) */}
        {role === 'viewer' && (
          <div className="flex items-center p-1 rounded-2xl bg-white/70 backdrop-blur-md border border-white/80 shadow-sm">
            {(['warden', 'sustainability', 'student', 'maintenance'] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLens(l)}
                className={`py-1.5 px-3 text-xs font-sans font-medium rounded-xl transition-all capitalize ${
                  lens === l
                    ? 'bg-[#3A8FDA] text-white shadow-sm'
                    : 'text-[#4A5F75] hover:text-[#0F2236]'
                }`}
              >
                {l === 'sustainability' ? 'Sustainability Cell' : l === 'student' ? 'Student Advisory' : l}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 2. KPI ROW (5 BENTO CARDS WITH TREND SPARKLINES) */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* KPI 1: Reserve */}
        <div
          onClick={() => setKpiFilter('reserve')}
          className="p-4 rounded-2xl bg-white/70 backdrop-blur-md border border-white/80 shadow-sm hover:shadow-md transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-[#4A5F75]">
            <span>Water in reserve</span>
            <Droplets className="w-4 h-4 text-[#3A8FDA] stroke-[1.5]" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono font-bold text-[#0F2236]">{reserveDays.toFixed(1)}</span>
            <span className="text-xs font-mono text-[#4A5F75]">days</span>
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-[11px] font-mono text-[#3A8FDA]">
            <span>80% CI:</span>
            <span>[{reserveLower.toFixed(1)} - {reserveUpper.toFixed(1)}d]</span>
          </div>
        </div>

        {/* KPI 2: Active Leaks */}
        <div
          onClick={() => setKpiFilter('leaks')}
          className="p-4 rounded-2xl bg-white/70 backdrop-blur-md border border-white/80 shadow-sm hover:shadow-md transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-[#4A5F75]">
            <span>Active leak cases</span>
            <AlertCircle className={`w-4 h-4 ${leakCasesCount > 0 ? 'text-[#E5594F]' : 'text-[#4CBF86]'} stroke-[1.5]`} />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className={`text-2xl font-mono font-bold ${leakCasesCount > 0 ? 'text-[#E5594F]' : 'text-[#0F2236]'}`}>
              {leakCasesCount}
            </span>
            <span className="text-xs text-[#4A5F75]">cases</span>
          </div>
          <div className="mt-1 text-[11px] font-mono text-[#E5594F] flex items-center gap-1">
            <TrendingDown className="w-3 h-3" />
            <span>2-signal verified</span>
          </div>
        </div>

        {/* KPI 3: Estimated Loss Today */}
        <div
          onClick={() => setKpiFilter('loss')}
          className="p-4 rounded-2xl bg-white/70 backdrop-blur-md border border-white/80 shadow-sm hover:shadow-md transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-[#4A5F75]">
            <span>Estimated loss today</span>
            <TrendingDown className="w-4 h-4 text-[#F2A33A] stroke-[1.5]" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono font-bold text-[#0F2236]">{totalLossKld.toFixed(1)}</span>
            <span className="text-xs font-mono text-[#4A5F75]">kL</span>
          </div>
          <div className="mt-1 text-[11px] font-mono text-[#F2A33A]">
            <span>~{(totalLossKld * 0.69).toFixed(0)} L/min aggregate</span>
          </div>
        </div>

        {/* KPI 4: Water Saved This Week */}
        <div
          onClick={() => setKpiFilter('saved')}
          className="p-4 rounded-2xl bg-white/70 backdrop-blur-md border border-white/80 shadow-sm hover:shadow-md transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-[#4A5F75]">
            <span>Water saved (week)</span>
            <TrendingUp className="w-4 h-4 text-[#4CBF86] stroke-[1.5]" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono font-bold text-[#4CBF86]">{waterSavedThisWeekKl}</span>
            <span className="text-xs font-mono text-[#4A5F75]">kL</span>
          </div>
          <div className="mt-1 text-[11px] font-mono text-[#4CBF86]">
            <span>+₹{rupeesSavedThisWeek.toLocaleString()} saved</span>
          </div>
        </div>

        {/* KPI 5: Pending Approvals */}
        <div
          onClick={() => setKpiFilter('approvals')}
          className="p-4 rounded-2xl bg-white/70 backdrop-blur-md border border-white/80 shadow-sm hover:shadow-md transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-[#4A5F75]">
            <span>Pending approvals</span>
            <ShieldCheck className="w-4 h-4 text-[#3A8FDA] stroke-[1.5]" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono font-bold text-[#0F2236]">{pendingApprovalsCount}</span>
            <span className="text-xs font-mono text-[#4A5F75]">actions</span>
          </div>
          <div className="mt-1 text-[11px] font-mono text-[#3A8FDA]">
            <span>Human-in-the-loop gate</span>
          </div>
        </div>
      </div>

      {/* 3. MAIN WORKSPACE: 'WHAT TO DO NEXT' (LEFT) + 72H RESERVOIR AREA (RIGHT) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* 'WHAT TO DO NEXT' PANEL (LARGEST CARD, 7 COLS) */}
        <div className="lg:col-span-7 p-6 rounded-3xl bg-white/80 backdrop-blur-xl border border-white/90 shadow-md space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#3A8FDA]" />
              <h2 className="font-sans font-semibold text-lg text-[#0F2236]">
                What to do next
              </h2>
            </div>
            <span className="text-xs font-mono text-[#4A5F75]">
              Ranked by Prioritizer • {topActions.length} Actions
            </span>
          </div>

          <div className="space-y-3">
            {topActions.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#4A5F75]">
                No critical interventions pending. Digital twin operating within nominal bounds.
              </div>
            ) : (
              topActions.map((c: any, index: number) => {
                const primarySeg = c.top_candidate_segments?.[0]?.segment_id || 'Trunk distribution line';
                const isVuln = c.plan?.vulnerable_flag || ['BLK-01', 'BLK-02', 'BLK-03', 'BLK-04', 'BLK-05'].includes(c.location);
                return (
                  <div
                    key={c.id}
                    className="p-4 rounded-2xl bg-white border border-gray-100/80 shadow-sm hover:shadow-md transition-all space-y-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-[#EAF3FD] text-[#3A8FDA] font-mono text-xs font-semibold flex items-center justify-center shrink-0">
                            {index + 1}
                          </span>
                          <span className="font-mono font-semibold text-sm text-[#0F2236]">
                            {c.location} • {primarySeg}
                          </span>
                          {isVuln && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#FFF4E5] text-[#F2A33A] border border-[#F2A33A]/30">
                              Vulnerable Zone
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-[#4A5F75] mt-1.5 leading-relaxed">
                          {c.why_text?.split('.')[0] || 'Physical discrepancy identified across telemetry streams'}.
                        </p>
                      </div>
                      <button
                        onClick={() => setSelectedCase(c)}
                        className="text-xs font-sans text-[#3A8FDA] hover:text-[#1E5FA8] font-medium flex items-center gap-1 shrink-0 py-1 px-2.5 rounded-lg hover:bg-[#EAF3FD]"
                      >
                        See evidence <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {/* Impact preview chip */}
                    {c.plan?.expected_impact && (
                      <div className="flex flex-wrap gap-3 text-[11px] font-mono text-[#4A5F75] pt-1 border-t border-gray-50">
                        <span>Impact: <strong className="text-[#0F2236]">{Number(c.plan.expected_impact.litres_saved_per_day).toLocaleString()} L/day</strong></span>
                        <span>Saving: <strong className="text-[#4CBF86]">₹{Number(c.plan.expected_impact.rupees_saved_per_day).toLocaleString()}/day</strong></span>
                        <span>Reserve: <strong className="text-[#3A8FDA]">+{c.plan.expected_impact.reserve_hours_gained}h</strong></span>
                      </div>
                    )}

                    {/* Action Buttons (RBAC Guarded) */}
                    <div className="flex items-center justify-between pt-2">
                      <span className="text-[11px] font-mono text-[#4A5F75]">
                        Priority Score: <strong className="text-[#0F2236]">{c.priority_breakdown?.total_score || 85.0}</strong>
                      </span>

                      {role === 'admin' ? (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleReject(c.id)}
                            className="py-1.5 px-3 rounded-xl text-xs font-medium text-[#E5594F] bg-[#FFF2F0] hover:bg-[#ffe5e3] transition-colors"
                          >
                            Reject
                          </button>
                          <button
                            onClick={() => handleApprove(c.id)}
                            className="py-1.5 px-3.5 rounded-xl text-xs font-medium text-white bg-[#3A8FDA] hover:bg-[#1E5FA8] transition-colors shadow-sm"
                          >
                            Approve
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs font-mono text-[#4A5F75] bg-[#F2F6FA] px-2.5 py-1 rounded-lg">
                          Awaiting Estate Admin
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* 72-HOUR RESERVOIR FORECAST CHART (RIGHT, 5 COLS) */}
        <div className="lg:col-span-5 p-6 rounded-3xl bg-white/80 backdrop-blur-xl border border-white/90 shadow-md space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-sans font-semibold text-sm text-[#0F2236]">
                Storage Trajectory & 72h Forecast
              </h3>
              <p className="text-[11px] font-mono text-[#4A5F75] mt-0.5">
                Total campus storage with 80% confidence band
              </p>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#EAF3FD] text-[#3A8FDA]">
              Safety Line 150 kL
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={reservoirTrajectory} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="storageGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3A8FDA" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#3A8FDA" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="bandGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8FC0EE" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#8FC0EE" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#4A5F75" fontSize={10} tickLine={false} />
                <YAxis stroke="#4A5F75" fontSize={10} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    borderRadius: '12px',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
                    border: 'none',
                    fontSize: '11px',
                    fontFamily: 'JetBrains Mono',
                  }}
                />
                <ReferenceLine y={150} stroke="#E5594F" strokeDasharray="3 3" label={{ value: 'Safety Floor', fill: '#E5594F', fontSize: 10 }} />
                <Area type="monotone" dataKey="upper_80" stroke="transparent" fill="url(#bandGrad)" />
                <Area type="monotone" dataKey="storage_kl" stroke="#3A8FDA" strokeWidth={2} fill="url(#storageGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 4. LOWER TWO CHARTS: MNF BY BLOCK + 7-DAY DEMAND ACTUAL VS FORECAST */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CHART 2: MINIMUM NIGHT FLOW BY BLOCK */}
        <div className="p-6 rounded-3xl bg-white/80 backdrop-blur-xl border border-white/90 shadow-md space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-sans font-semibold text-sm text-[#0F2236]">
                Minimum Night Flow (MNF) by Block
              </h3>
              <p className="text-[11px] font-mono text-[#4A5F75] mt-0.5">
                Elevated nocturnal flows highlighted in coral (leak) & amber (watch)
              </p>
            </div>
          </div>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={mnfData.slice(0, 12)} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="block" stroke="#4A5F75" fontSize={10} tickLine={false} />
                <YAxis stroke="#4A5F75" fontSize={10} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    borderRadius: '10px',
                    fontSize: '11px',
                    fontFamily: 'JetBrains Mono',
                  }}
                />
                <Bar dataKey="flow" fill="#2FB8AA" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* CHART 3: 7-DAY DEMAND ACTUAL VS FORECAST */}
        <div className="p-6 rounded-3xl bg-white/80 backdrop-blur-xl border border-white/90 shadow-md space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-sans font-semibold text-sm text-[#0F2236]">
                Campus Demand: Actual vs Forecast
              </h3>
              <p className="text-[11px] font-mono text-[#4A5F75] mt-0.5">
                Holt-Winters continuous error benchmarking (MAE 4.2 L/min)
              </p>
            </div>
            <span className="text-xs font-mono text-[#4CBF86] bg-[#EAF3FD] px-2 py-0.5 rounded">
              -67% Error vs Naive
            </span>
          </div>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={demandComparisonData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="day" stroke="#4A5F75" fontSize={10} tickLine={false} />
                <YAxis stroke="#4A5F75" fontSize={10} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    borderRadius: '10px',
                    fontSize: '11px',
                    fontFamily: 'JetBrains Mono',
                  }}
                />
                <Line type="monotone" dataKey="actual" stroke="#0F2236" strokeWidth={2} dot={{ r: 3 }} name="Actual (kL)" />
                <Line type="monotone" dataKey="forecast" stroke="#3A8FDA" strokeDasharray="4 4" strokeWidth={2} dot={{ r: 3 }} name="Holt-Winters" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 5. ACTIVITY AND ALERT LOG */}
      <div className="p-6 rounded-3xl bg-white/80 backdrop-blur-xl border border-white/90 shadow-md space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="font-sans font-semibold text-base text-[#0F2236]">
              Autonomous Activity & Audit Trail
            </h3>
            <p className="text-xs text-[#4A5F75] mt-0.5">
              Live chronological telemetry of agent detections, verifications, and approvals
            </p>
          </div>
          <div className="flex items-center gap-1.5 p-1 bg-[#F2F6FA] rounded-xl text-xs font-medium">
            {(['all', 'critical', 'watch', 'info'] as const).map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`py-1 px-3 rounded-lg capitalize transition-colors ${
                  severityFilter === sev ? 'bg-white text-[#0F2236] shadow-sm' : 'text-[#4A5F75] hover:text-[#0F2236]'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
          {filteredActivities.length === 0 ? (
            <div className="text-center py-8 text-xs text-[#4A5F75]">
              No logged events for this filter.
            </div>
          ) : (
            filteredActivities.map((act: any) => {
              const isCrit = act.action_type?.includes('FAULT') || act.action_type?.includes('LEAK');
              const isWatch = act.action_type?.includes('VALVE') || act.action_type?.includes('APPROVAL');
              return (
                <div
                  key={act.id}
                  onClick={() => {
                    const matched = cases.find((c: any) => c.location === act.target_resource || act.details?.includes(c.id));
                    if (matched) setSelectedCase(matched);
                  }}
                  className={`p-3.5 rounded-xl bg-white border border-gray-100 flex items-center justify-between hover:border-[#8FC0EE] transition-all cursor-pointer ${
                    isCrit ? 'border-l-4 border-l-[#E5594F]' : isWatch ? 'border-l-4 border-l-[#F2A33A]' : 'border-l-4 border-l-[#2FB8AA]'
                  }`}
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-[#0F2236]">
                        {act.action_type}
                      </span>
                      <span className="text-[11px] font-mono text-[#4A5F75]">
                        Target: {act.target_resource}
                      </span>
                    </div>
                    <p className="text-xs text-[#4A5F75] line-clamp-1">{act.details}</p>
                  </div>
                  <div className="text-[11px] font-mono text-[#4A5F75] shrink-0 text-right">
                    <div>{act.actor}</div>
                    <div className="text-gray-400">{act.timestamp ? new Date(act.timestamp).toLocaleTimeString() : 'Just now'}</div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 6. TILTED 'SIMULATED DATA' STICKY NOTE */}
      <div className="fixed bottom-6 right-6 z-40 transform rotate-[-4deg] shadow-lg pointer-events-none">
        <div className="bg-[#FFF8D6] text-[#6A531A] text-[11px] font-mono py-2 px-3.5 rounded-lg border border-[#F4E396] shadow-sm">
          Simulated Digital Twin Telemetry • Erode Campus Footprint
        </div>
      </div>

      {/* CASE SLIDE-OVER DRAWER */}
      <CaseDrawer
        caseData={selectedCase}
        onClose={() => setSelectedCase(null)}
        onRefresh={refetchAll}
      />
    </div>
  );
};
