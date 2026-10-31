import { create } from 'zustand';

export type UserRole = 'admin' | 'viewer' | null;

interface AuthState {
  role: UserRole;
  login: (role: 'admin' | 'viewer') => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

const STORAGE_KEY = 'neeraran_role';

export const useAuthStore = create<AuthState>((set, get) => ({
  role: (sessionStorage.getItem(STORAGE_KEY) as UserRole) || null,

  login: (role: 'admin' | 'viewer') => {
    sessionStorage.setItem(STORAGE_KEY, role);
    set({ role });
  },

  logout: () => {
    sessionStorage.removeItem(STORAGE_KEY);
    set({ role: null });
  },

  isAuthenticated: () => {
    return get().role !== null;
  },
}));
