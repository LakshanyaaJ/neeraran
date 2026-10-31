import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Search, 
  Moon, 
  Sun, 
  LogOut, 
  ChevronDown,
  RotateCcw,
  ShieldCheck
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { Logo } from '../common/Logo';
import { SystemStatusPill } from '../common/SystemStatusPill';
import { CompactSimControl } from './CompactSimControl';
import { useAuthStore } from '../../store/auth';
import { useThemeStore } from '../../store/theme';
import { api, useSystemStatusStore } from '../../api/client';

interface NavItem {
  id: string;
  label: string;
  path: string;
}

const NAV_TABS: NavItem[] = [
  { id: 'overview', label: 'Overview', path: '/app/overview' },
  { id: 'map', label: 'Map', path: '/app/map' },
  { id: 'agents', label: 'Agents', path: '/app/agents' },
  { id: 'approvals', label: 'Approvals', path: '/app/approvals' },
  { id: 'simulation', label: 'Simulation', path: '/app/simulation' },
  { id: 'evaluation', label: 'Evaluation', path: '/app/evaluation' },
  { id: 'responsible-ai', label: 'Responsible AI', path: '/app/responsible-ai' },
];

export const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const { role, logout } = useAuthStore();
  const { isNightOps, toggleNightOps } = useThemeStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleResetDemo = async () => {
    if (role !== 'admin') {
      toast.error('Only Estate Admin can reset the demo state.');
      return;
    }
    toast.promise(api.resetDemo(), {
      loading: 'Resetting demo to Day 1 08:00...',
      success: () => {
        setIsMenuOpen(false);
        window.location.reload();
        return 'Demo restored to Day 1 08:00 (clean approvals & audit)';
      },
      error: 'Failed to reset demo state',
    });
  };

  const handleToggleDemoSafe = () => {
    const isNowSafe = useSystemStatusStore.getState().toggleDemoSafeMode();
    setIsMenuOpen(false);
    toast.success(
      isNowSafe
        ? 'Demo Safe Mode enabled (Shift+D to toggle). Operating entirely offline.'
        : 'Demo Safe Mode disabled. Reconnected to live stream.',
      { icon: isNowSafe ? '🛡️' : '🌐' }
    );
  };

  const roleLabel = role === 'admin' ? 'Estate Admin' : 'Viewer';

  return (
    <header className="sticky top-0 z-30 w-full px-4 sm:px-6 py-3">
      <div className="max-w-[1440px] mx-auto flex items-center justify-between gap-3">
        {/* Left: Brand Logo */}
        <div className="flex-shrink-0 flex items-center gap-3">
          <Logo size="md" />
        </div>

        {/* Center: Bento Centred Pill Navbar with Sliding LayoutId Pill */}
        <nav className="hidden lg:flex items-center glass-pill p-1.5 shadow-sm border border-white/70 dark:border-white/10 bg-white/50 dark:bg-sky-950/40">
          {NAV_TABS.map((tab) => (
            <NavLink
              key={tab.id}
              to={tab.path}
              className={({ isActive }) =>
                `relative px-3.5 py-1.5 text-xs font-medium rounded-pill transition-colors select-none ${
                  isActive
                    ? 'text-ink-900 font-semibold'
                    : 'text-ink-600 hover:text-ink-900'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="activeNavTab"
                      className="absolute inset-0 bg-white dark:bg-sky-700/60 rounded-pill shadow-sm"
                      transition={{ type: 'spring', bounce: 0.18, duration: 0.4 }}
                    />
                  )}
                  <span className="relative z-10">{tab.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Right: Search, Night Ops, System Status, Avatar */}
        <div className="flex items-center gap-2.5">
          {/* Search box */}
          <div className="hidden md:flex items-center relative">
            <Search className="w-3.5 h-3.5 text-ink-600 absolute left-3 pointer-events-none stroke-[1.5]" />
            <input
              type="text"
              placeholder="Search assets, pipes, alerts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs rounded-pill bg-white/70 dark:bg-sky-950/40 border border-white/80 dark:border-white/10 text-ink-900 placeholder:text-ink-600 focus:outline-none focus:ring-1 focus:ring-sky-500 w-48 lg:w-56 transition-all"
            />
          </div>

          {/* Night Ops Toggle */}
          <button
            onClick={toggleNightOps}
            className="glass-pill p-2 text-ink-600 hover:text-ink-900 transition-colors"
            title={isNightOps ? 'Switch to Day Mode' : 'Switch to Night Ops'}
            aria-label="Night Ops Toggle"
          >
            {isNightOps ? (
              <Sun className="w-3.5 h-3.5 text-amber stroke-[1.5]" />
            ) : (
              <Moon className="w-3.5 h-3.5 text-sky-700 stroke-[1.5]" />
            )}
          </button>

          {/* Compact Simulation Control Bar (Phase 7) */}
          <CompactSimControl />

          {/* System Status Pill */}
          <div className="hidden sm:block">
            <SystemStatusPill />
          </div>

          {/* Role Avatar & Menu */}
          <div className="relative">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="glass-pill pl-2 pr-3 py-1 flex items-center gap-2 hover:bg-white/80 dark:hover:bg-sky-900/40 transition-colors text-xs"
            >
              <div className="w-6 h-6 rounded-full bg-sky-500 text-white flex items-center justify-center font-bold text-[10px]">
                {role === 'admin' ? 'EA' : 'VW'}
              </div>
              <span className="font-medium text-ink-900 hidden sm:inline">{roleLabel}</span>
              <ChevronDown className="w-3 h-3 text-ink-600 stroke-[1.5]" />
            </button>

            {/* Dropdown Menu */}
            {isMenuOpen && (
              <div className="absolute right-0 mt-2 w-48 glass-panel py-1.5 shadow-lg border border-white/80 dark:border-white/10 z-50 animate-in fade-in zoom-in-95 duration-100">
                <div className="px-3 py-1.5 border-b border-ink-600/10 text-xs text-ink-600">
                  <span>Signed in as</span>
                  <div className="font-semibold text-ink-900">{roleLabel}</div>
                </div>

                {role === 'admin' && (
                  <button
                    onClick={handleResetDemo}
                    className="w-full text-left px-3 py-2 text-xs text-ink-900 hover:bg-sky-50 dark:hover:bg-sky-900/30 flex items-center gap-2 transition-colors border-b border-ink-600/10"
                  >
                    <RotateCcw className="w-3.5 h-3.5 text-azure-600 stroke-[1.5]" />
                    <span>Reset Demo (Day 1)</span>
                  </button>
                )}

                <button
                  onClick={handleToggleDemoSafe}
                  className="w-full text-left px-3 py-2 text-xs text-ink-900 hover:bg-sky-50 dark:hover:bg-sky-900/30 flex items-center justify-between transition-colors border-b border-ink-600/10"
                >
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 stroke-[1.5]" />
                    <span>Demo Safe Mode</span>
                  </div>
                  <span className="text-[10px] font-mono text-ink-400">Shift+D</span>
                </button>

                <button
                  onClick={() => {
                    setIsMenuOpen(false);
                    handleLogout();
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-coral hover:bg-coral/10 flex items-center gap-2 transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5 stroke-[1.5]" />
                  <span>Exit Session</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Nav Drawer Row */}
      <div className="lg:hidden flex overflow-x-auto gap-1 py-2 px-1 mt-2 no-scrollbar">
        {NAV_TABS.map((tab) => (
          <NavLink
            key={tab.id}
            to={tab.path}
            className={({ isActive }) =>
              `px-3 py-1 text-xs whitespace-nowrap rounded-pill font-medium transition-colors ${
                isActive
                  ? 'bg-sky-500 text-white'
                  : 'glass-pill text-ink-600'
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </div>
    </header>
  );
};
