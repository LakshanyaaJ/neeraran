import { create } from 'zustand';

interface ThemeState {
  isNightOps: boolean;
  toggleNightOps: () => void;
  setNightOps: (enabled: boolean) => void;
}

const STORAGE_KEY = 'neeraran_night_ops';

const initialNightOps = (() => {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored !== null) return stored === 'true';
  return false;
})();

// Apply class initially
if (initialNightOps) {
  document.documentElement.classList.add('dark');
} else {
  document.documentElement.classList.remove('dark');
}

export const useThemeStore = create<ThemeState>((set) => ({
  isNightOps: initialNightOps,

  toggleNightOps: () => {
    set((state) => {
      const next = !state.isNightOps;
      localStorage.setItem(STORAGE_KEY, String(next));
      if (next) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      return { isNightOps: next };
    });
  },

  setNightOps: (enabled: boolean) => {
    localStorage.setItem(STORAGE_KEY, String(enabled));
    if (enabled) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    set({ isNightOps: enabled });
  },
}));

