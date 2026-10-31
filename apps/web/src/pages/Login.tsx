import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShieldCheck, Eye, ArrowRight, Lock } from 'lucide-react';
import { Logo } from '../components/common/Logo';
import { useAuthStore } from '../store/auth';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuthStore();

  const redirectTarget = searchParams.get('from')
    ? decodeURIComponent(searchParams.get('from')!)
    : '/app/overview';

  const handleSelectRole = (role: 'admin' | 'viewer') => {
    login(role);
    navigate(redirectTarget);
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center px-4 py-12 relative overflow-hidden">
      {/* Drifting cloud layer background */}
      <div className="drifting-cloud-bg">
        <div className="cloud-layer" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-lg space-y-6"
      >
        {/* Branding Header */}
        <div className="text-center space-y-2">
          <Logo size="lg" showTagline={true} />
          <p className="text-sm text-ink-600 max-w-sm mx-auto pt-1">
            Autonomous water resilience & smart resource digital twin for educational campuses.
          </p>
        </div>

        {/* Demo Gate Card */}
        <div className="glass-panel p-6 sm:p-8 space-y-6">
          <div className="flex items-center gap-2 pb-3 border-b border-ink-600/10 text-xs text-ink-600">
            <Lock className="w-3.5 h-3.5 text-sky-500 stroke-[1.5]" />
            <span>Select demonstration role to access the operational digital twin</span>
          </div>

          <div className="space-y-4">
            {/* Option 1: Estate Admin */}
            <div className="p-4 rounded-card bg-white/70 dark:bg-sky-950/40 border border-white/80 dark:border-white/10 hover:border-sky-500 transition-all space-y-3">
              <div className="flex items-start justify-between">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5 text-ink-900 font-semibold text-sm">
                    <ShieldCheck className="w-4 h-4 text-sky-700 stroke-[1.5]" />
                    <span>Estate Admin</span>
                  </div>
                  <p className="text-xs text-ink-600">
                    Full operational control: authorize approval queue, tune anomaly thresholds, and run scenario injectors.
                  </p>
                </div>
              </div>

              <button
                onClick={() => handleSelectRole('admin')}
                className="w-full py-2.5 px-4 bg-sky-500 hover:bg-sky-700 text-white text-xs font-semibold rounded-btn transition-colors flex items-center justify-center gap-2 shadow-sm"
              >
                <span>Enter as Estate Admin</span>
                <ArrowRight className="w-3.5 h-3.5 stroke-[1.5]" />
              </button>
            </div>

            {/* Option 2: Viewer */}
            <div className="p-4 rounded-card bg-white/70 dark:bg-sky-950/40 border border-white/80 dark:border-white/10 hover:border-aqua transition-all space-y-3">
              <div className="flex items-start justify-between">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5 text-ink-900 font-semibold text-sm">
                    <Eye className="w-4 h-4 text-aqua stroke-[1.5]" />
                    <span>Viewer</span>
                  </div>
                  <p className="text-xs text-ink-600">
                    Read-only monitoring with 4 domain lenses: Warden, Sustainability Cell, Student Advisory, and Maintenance.
                  </p>
                </div>
              </div>

              <button
                onClick={() => handleSelectRole('viewer')}
                className="w-full py-2.5 px-4 bg-white hover:bg-mist text-ink-900 dark:text-sky-100 text-xs font-semibold rounded-btn border border-sky-100 dark:border-white/10 transition-colors flex items-center justify-center gap-2 shadow-sm"
              >
                <span>Enter as Viewer</span>
                <ArrowRight className="w-3.5 h-3.5 stroke-[1.5]" />
              </button>
            </div>
          </div>

          <div className="pt-2 text-center">
            <span className="text-[11px] text-ink-600">
              Note: Simulation state runs deterministically on seed 42.
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
