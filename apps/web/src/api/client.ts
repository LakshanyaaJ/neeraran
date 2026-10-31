/**
 * NEERARAN Resilient API Client — Phase 5
 * Connects frontend to the digital twin simulator and agent core.
 * Features:
 * - 4s hard timeout with AbortController & 1 automatic retry
 * - Deterministic fallback to bundled snapshots in /fallback/
 * - Attached X-User-Role header for RBAC
 * - Guaranteed: NEVER blanks the screen
 */
import { create } from 'zustand';
import { useAuthStore } from '../store/auth';

export type SystemConnectionStatus = 'live' | 'degraded' | 'offline';

interface SystemStatusState {
  status: SystemConnectionStatus;
  isUsingFallback: boolean;
  lastUpdated: string;
  errorMessage: string | null;
  setStatus: (status: SystemConnectionStatus, isFallback: boolean, msg?: string | null) => void;
}

export const useSystemStatusStore = create<SystemStatusState>((set) => ({
  status: 'live',
  isUsingFallback: false,
  lastUpdated: new Date().toLocaleTimeString(),
  errorMessage: null,
  setStatus: (status, isUsingFallback, errorMessage = null) =>
    set({ status, isUsingFallback, errorMessage, lastUpdated: new Date().toLocaleTimeString() }),
}));

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
  const setStatus = useSystemStatusStore.getState().setStatus;
  const role = useAuthStore.getState().role;
  const fullUrl = `${API_BASE}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
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
      return data as T;
    }
  } catch (err) {
    // Attempt 2: 1 automatic retry after 250ms
    try {
      await new Promise((resolve) => setTimeout(resolve, 250));
      const retryRes = await fetchWithTimeout(fullUrl, enhancedOptions, 4000);
      if (retryRes.ok) {
        const data = await retryRes.json();
        setStatus('live', false);
        return data as T;
      }
    } catch (retryErr) {
      console.warn(`[API] Endpoint ${endpoint} unreachable. Engaging fallback.`);
    }
  }

  // Graceful Fallback Snapshot Loader
  if (fallbackSnapshotUrl) {
    try {
      setStatus('degraded', true, 'Operating on bundled digital twin snapshot.');
      const fallbackRes = await fetch(fallbackSnapshotUrl);
      if (fallbackRes.ok) {
        const fallbackData = await fallbackRes.json();
        // If snapshot has final_state property, unwrap if expecting state
        if (endpoint.includes('/state') && fallbackData.final_state) {
          return fallbackData.final_state as T;
        }
        return fallbackData as T;
      }
    } catch (fallbackErr) {
      console.error('[API] Fallback load failed:', fallbackErr);
    }
  }

  setStatus('degraded', true, 'Backend disconnected.');
  return {} as T;
}

// Typed API operations
export const api = {
  // Simulator endpoints
  getState: () =>
    apiFetch<any>('/api/state', { method: 'GET' }, '/fallback/day_snapshot.json'),

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

  getComplaints: () =>
    apiFetch<any[]>('/api/complaints', { method: 'GET' }, '/fallback/day_snapshot.json'),

  // Agent Core endpoints
  getCases: () =>
    apiFetch<any[]>('/api/cases', { method: 'GET' }, '/fallback/day_snapshot.json'),

  getCaseDetail: (id: string) =>
    apiFetch<any>(`/api/cases/${id}`, { method: 'GET' }, '/fallback/leak_story.json'),

  getQueue: () =>
    apiFetch<any[]>('/api/queue', { method: 'GET' }, '/fallback/day_snapshot.json'),

  getForecast: () =>
    apiFetch<any>('/api/forecast', { method: 'GET' }, '/fallback/day_snapshot.json'),

  getPlan: () =>
    apiFetch<any>('/api/plan', { method: 'GET' }, '/fallback/leak_story.json'),

  decideApproval: (id: string, decision: 'approved' | 'rejected', note: string = '') =>
    apiFetch<any>(`/api/approvals/${id}`, {
      method: 'POST',
      body: JSON.stringify({ decision, note }),
    }),

  getAudit: () =>
    apiFetch<any[]>('/api/audit', { method: 'GET' }, '/fallback/day_snapshot.json'),

  getTraces: () =>
    apiFetch<any[]>('/api/traces', { method: 'GET' }, '/fallback/day_snapshot.json'),

  runOrchestrator: () =>
    apiFetch<any>('/api/orchestrator/run', { method: 'POST' }),

  // Backward-compatibility aliases
  getCampusTopology: () =>
    apiFetch<any>('/api/campus', { method: 'GET' }, '/fallback/campus.json'),

  getSimulationState: () =>
    apiFetch<any>('/api/state', { method: 'GET' }, '/fallback/day_snapshot.json'),

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

  updatePrioritizerWeights: (weights: Record<string, number>) =>
    apiFetch<any>('/api/prioritizer/weights', {
      method: 'POST',
      body: JSON.stringify(weights),
    }),
};
