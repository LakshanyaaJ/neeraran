/**
 * NEERARAN Resilient API Client — Phase 9
 * Connects frontend to the digital twin simulator and agent core.
 * Features:
 * - 4s hard timeout with AbortController & 1 automatic retry
 * - Deterministic fallback to bundled snapshots in /fallback/
 * - Demo Safe Mode (Shift+D toggle) for zero-latency, dead-API presentation
 * - Attached X-User-Role header for RBAC
 * - Guaranteed: NEVER blanks the screen or throws unhandled TypeError
 */
import { create } from 'zustand';
import { useAuthStore } from '../store/auth';

export type SystemConnectionStatus = 'live' | 'degraded' | 'offline' | 'demo_safe';

interface SystemStatusState {
  status: SystemConnectionStatus;
  isUsingFallback: boolean;
  isDemoSafeMode: boolean;
  lastUpdated: string;
  errorMessage: string | null;
  setStatus: (status: SystemConnectionStatus, isFallback: boolean, msg?: string | null) => void;
  toggleDemoSafeMode: () => boolean;
  setDemoSafeMode: (enabled: boolean) => void;
}

const initialDemoSafe = typeof window !== 'undefined' && sessionStorage.getItem('neeraran_demo_safe') === 'true';

export const useSystemStatusStore = create<SystemStatusState>((set, get) => ({
  status: initialDemoSafe ? 'demo_safe' : 'live',
  isUsingFallback: initialDemoSafe,
  isDemoSafeMode: initialDemoSafe,
  lastUpdated: new Date().toLocaleTimeString(),
  errorMessage: null,
  setStatus: (status, isUsingFallback, errorMessage = null) => {
    // If in demo safe mode, preserve demo_safe status
    if (get().isDemoSafeMode) {
      set({ status: 'demo_safe', isUsingFallback: true, lastUpdated: new Date().toLocaleTimeString() });
      return;
    }
    set({ status, isUsingFallback, errorMessage, lastUpdated: new Date().toLocaleTimeString() });
  },
  toggleDemoSafeMode: () => {
    const nextState = !get().isDemoSafeMode;
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('neeraran_demo_safe', String(nextState));
    }
    set({
      isDemoSafeMode: nextState,
      isUsingFallback: nextState,
      status: nextState ? 'demo_safe' : 'live',
      lastUpdated: new Date().toLocaleTimeString(),
    });
    return nextState;
  },
  setDemoSafeMode: (enabled: boolean) => {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('neeraran_demo_safe', String(enabled));
    }
    set({
      isDemoSafeMode: enabled,
      isUsingFallback: enabled,
      status: enabled ? 'demo_safe' : 'live',
      lastUpdated: new Date().toLocaleTimeString(),
    });
  },
}));

// Wire global Shift+D listener for Demo Safe Mode
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'D' && e.shiftKey) {
      const activeElement = document.activeElement;
      const isInput = activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA');
      if (!isInput) {
        e.preventDefault();
        const next = useSystemStatusStore.getState().toggleDemoSafeMode();
        console.info(`[NEERARAN] Demo Safe Mode toggled: ${next ? 'ACTIVE' : 'INACTIVE'}`);
      }
    }
  });
}

const API_BASE = 'http://localhost:8000';

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 4000): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return res;
  } finally {
    clearTimeout(id);
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  fallbackSnapshotUrl?: string
): Promise<T> {
  const stateStore = useSystemStatusStore.getState();
  const isDemoSafe = stateStore.isDemoSafeMode;
  const setStatus = stateStore.setStatus;
  const role = useAuthStore.getState().role;
  const fullUrl = `${API_BASE}${endpoint}`;

  // Helper: check if endpoint expects array
  const isArrayEndpoint =
    endpoint.includes('/cases') ||
    endpoint.includes('/queue') ||
    endpoint.includes('/complaints') ||
    endpoint.includes('/audit') ||
    endpoint.includes('/traces');

  // Fast path: In Demo Safe Mode, immediately load fallback snapshot without attempting network
  if (isDemoSafe && fallbackSnapshotUrl) {
    try {
      setStatus('demo_safe', true, 'Operating in Demo Safe Mode.');
      const fallbackRes = await fetch(fallbackSnapshotUrl);
      if (fallbackRes.ok) {
        const data = await fallbackRes.json();
        if (isArrayEndpoint && !Array.isArray(data)) {
          return [] as unknown as T;
        }
        return data as T;
      }
    } catch (_err) {
      return (isArrayEndpoint ? [] : {}) as T;
    }
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  if (role) {
    headers['x-user-role'] = role;
  }

  const enhancedOptions: RequestInit = {
    ...options,
    headers,
  };

  // Attempt 1
  try {
    const res = await fetchWithTimeout(fullUrl, enhancedOptions, 4000);
    if (res.ok) {
      const data = await res.json();
      setStatus('live', false);
      if (isArrayEndpoint && !Array.isArray(data)) {
        return [] as unknown as T;
      }
      return data as T;
    }
  } catch (_err) {
    // Attempt 2: 1 automatic retry after 200ms
    try {
      await new Promise((resolve) => setTimeout(resolve, 200));
      const retryRes = await fetchWithTimeout(fullUrl, enhancedOptions, 4000);
      if (retryRes.ok) {
        const data = await retryRes.json();
        setStatus('live', false);
        if (isArrayEndpoint && !Array.isArray(data)) {
          return [] as unknown as T;
        }
        return data as T;
      }
    } catch (_retryErr) {
      // API unreachable, fall back
    }
  }

  // Graceful Fallback Snapshot Loader
  if (fallbackSnapshotUrl) {
    try {
      setStatus('degraded', true, 'Operating on bundled digital twin snapshot.');
      const fallbackRes = await fetch(fallbackSnapshotUrl);
      if (fallbackRes.ok) {
        const fallbackData = await fallbackRes.json();
        if (isArrayEndpoint && !Array.isArray(fallbackData)) {
          return [] as unknown as T;
        }
        return fallbackData as T;
      }
    } catch (fallbackErr) {
      console.warn('[API] Fallback load failed:', fallbackErr);
    }
  }

  setStatus('degraded', true, 'Backend disconnected.');
  return (isArrayEndpoint ? [] : {}) as T;
}

// Typed API operations
export const api = {
  // Simulator endpoints
  getState: () =>
    apiFetch<any>('/api/state', { method: 'GET' }, '/fallback/snapshot_initial.json'),

  getCampus: () =>
    apiFetch<any>('/api/campus', { method: 'GET' }, '/fallback/campus.json'),

  controlSim: (play?: boolean, speed?: number, seek?: number) =>
    apiFetch<any>('/api/sim/control', {
      method: 'POST',
      body: JSON.stringify({ play, speed, seek }),
    }),

  injectFault: (faultType: string, entityId: string, lossRate: number = 45.0, details: string = '') =>
    apiFetch<any>('/api/sim/inject', {
      method: 'POST',
      body: JSON.stringify({ fault_type: faultType, entity_id: entityId, true_loss_rate_lpm: lossRate, details }),
    }),

  resetSim: (seed: number = 42) =>
    apiFetch<any>('/api/sim/reset', {
      method: 'POST',
      body: JSON.stringify({ seed }),
    }),

  resetDemo: () =>
    apiFetch<any>('/api/demo/reset', { method: 'POST' }, '/fallback/snapshot_initial.json'),

  getComplaints: () =>
    apiFetch<any[]>('/api/complaints', { method: 'GET' }, '/fallback/complaints.json'),

  // Agent Core endpoints
  getCases: () =>
    apiFetch<any[]>('/api/cases', { method: 'GET' }, '/fallback/cases.json'),

  getCaseDetail: (id: string) =>
    apiFetch<any>(`/api/cases/${id}`, { method: 'GET' }, '/fallback/leak_story.json'),

  getQueue: () =>
    apiFetch<any[]>('/api/queue', { method: 'GET' }, '/fallback/queue.json'),

  getForecast: () =>
    apiFetch<any>('/api/forecast', { method: 'GET' }, '/fallback/forecast.json'),

  getPlan: () =>
    apiFetch<any>('/api/plan', { method: 'GET' }, '/fallback/plan.json'),

  decideApproval: (id: string, decision: 'approved' | 'rejected', note: string = '') =>
    apiFetch<any>(`/api/approvals/${id}`, {
      method: 'POST',
      body: JSON.stringify({ decision, note }),
    }),

  getAudit: () =>
    apiFetch<any[]>('/api/audit', { method: 'GET' }, '/fallback/audit.json'),

  getTraces: () =>
    apiFetch<any[]>('/api/traces', { method: 'GET' }, '/fallback/traces.json'),

  runOrchestrator: () =>
    apiFetch<any>('/api/orchestrator/run', { method: 'POST' }),

  // Backward-compatibility aliases
  getCampusTopology: () =>
    apiFetch<any>('/api/campus', { method: 'GET' }, '/fallback/campus.json'),

  getSimulationState: () =>
    apiFetch<any>('/api/state', { method: 'GET' }, '/fallback/snapshot_initial.json'),

  setSpeed: (speed: 1 | 5 | 20) =>
    apiFetch<any>('/api/sim/control', {
      method: 'POST',
      body: JSON.stringify({ speed }),
    }),

  togglePause: (paused: boolean) =>
    apiFetch<any>('/api/sim/control', {
      method: 'POST',
      body: JSON.stringify({ play: !paused }),
    }),

  stepTick: (_minutes: number = 1.0) =>
    apiFetch<any>('/api/sim/control', {
      method: 'POST',
      body: JSON.stringify({ seek: undefined }),
    }),

  reset: (seed: number = 42) =>
    apiFetch<any>('/api/sim/reset', {
      method: 'POST',
      body: JSON.stringify({ seed }),
    }),

  parseScenario: (prompt: string) =>
    apiFetch<any>('/api/sim/parse-scenario', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    }),

  injectScenario: (events: any[]) =>
    apiFetch<any>('/api/sim/inject-scenario', {
      method: 'POST',
      body: JSON.stringify({ events }),
    }),

  updatePrioritizerWeights: (weights: Record<string, number>) =>
    apiFetch<any>('/api/prioritizer/weights', {
      method: 'POST',
      body: JSON.stringify(weights),
    }),

  getEvalMetrics: () =>
    apiFetch<any>('/api/eval/metrics', { method: 'GET' }, '/fallback/eval_metrics.json'),

  runBenchmark: () =>
    apiFetch<any>('/api/eval/benchmark', { method: 'POST' }),

  updateEvalThreshold: (z_score: number) =>
    apiFetch<any>('/api/eval/threshold', {
      method: 'POST',
      body: JSON.stringify({ z_score }),
    }),
};
