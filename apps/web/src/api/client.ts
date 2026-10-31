/**
 * NEERARAN Resilient API Client.
 * Strict Hackathon Protocol:
 * - 4s hard timeout with AbortController
 * - 1 automatic retry
 * - Deterministic fallback to bundled snapshots in /fallback/
 * - Guaranteed: NEVER throws unhandled exceptions, NEVER blanks the screen.
 */
import { create } from 'zustand';

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
  const fullUrl = `${API_BASE}${endpoint}`;

  // Attempt 1
  try {
    const res = await fetchWithTimeout(fullUrl, options, 4000);
    if (res.ok) {
      const data = await res.json();
      setStatus('live', false);
      return data as T;
    }
  } catch (err) {
    // Attempt 2: 1 automatic retry after 300ms
    try {
      await new Promise((resolve) => setTimeout(resolve, 300));
      const retryRes = await fetchWithTimeout(fullUrl, options, 4000);
      if (retryRes.ok) {
        const data = await retryRes.json();
        setStatus('live', false);
        return data as T;
      }
    } catch (retryErr) {
      console.warn(`[API] Endpoint ${endpoint} failed after retry. Engaging fallback snapshot.`);
    }
  }

  // Graceful Fallback Snapshot Loader
  if (fallbackSnapshotUrl) {
    try {
      setStatus('degraded', true, 'Operating on bundled digital twin snapshot.');
      const fallbackRes = await fetch(fallbackSnapshotUrl);
      if (fallbackRes.ok) {
        const fallbackData = await fallbackRes.json();
        return fallbackData as T;
      }
    } catch (fallbackErr) {
      console.error('[API] Fallback file read failed:', fallbackErr);
    }
  }

  setStatus('offline', true, 'Backend disconnected.');
  // Safe default empty response rather than throwing unhandled exception
  return {} as T;
}

// Typed API operations
export const api = {
  getSimulationState: () =>
    apiFetch<any>('/api/sim/state', { method: 'GET' }, '/fallback/snapshot_initial.json'),

  getCampusTopology: () =>
    apiFetch<any>('/api/campus/topology', { method: 'GET' }, '/fallback/topology.json'),

  setSpeed: (speed: 1 | 5 | 20) =>
    apiFetch<any>('/api/sim/speed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed }),
    }),

  togglePause: (paused: boolean) =>
    apiFetch<any>('/api/sim/pause', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paused }),
    }),

  stepTick: (minutes: number = 1.0) =>
    apiFetch<any>('/api/sim/tick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ minutes }),
    }),

  reset: (seed: number = 42) =>
    apiFetch<any>('/api/sim/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ seed }),
    }),

  injectLeak: (pipeId: string, leakRateLpm: number = 45.0) =>
    apiFetch<any>('/api/sim/leak/inject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pipe_id: pipeId, leak_rate_lpm: leakRateLpm }),
    }),

  clearLeak: (pipeId: string) =>
    apiFetch<any>('/api/sim/leak/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pipe_id: pipeId }),
    }),
};
