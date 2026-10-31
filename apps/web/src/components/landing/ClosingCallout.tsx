import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Logo } from '../common/Logo';
import { useAuthStore } from '../../store/auth';

export const ClosingCallout: React.FC = () => {
  const { role } = useAuthStore();

  return (
    <section className="py-20 px-4 sm:px-6 max-w-6xl mx-auto">
      <div className="glass-panel p-8 sm:p-12 text-center space-y-6 bg-gradient-to-b from-white/90 via-sky-50/70 to-mist dark:from-sky-950/50 dark:via-sky-900/30 dark:to-[#0B1622] border border-white/90 dark:border-white/10 shadow-glass rounded-[32px]">
        <div className="flex justify-center">
          <Logo size="lg" showTagline={true} />
        </div>

        <div className="max-w-xl mx-auto space-y-2">
          <h2 className="text-2xl sm:text-3xl font-light text-ink-900 tracking-tight">
            Ready to inspect the <span className="font-bold text-sky-700 dark:text-sky-300">live digital twin</span>?
          </h2>
          <p className="text-xs sm:text-sm text-ink-600 font-normal">
            Step into the control center as Estate Admin or Viewer to inspect real-time hydraulic flows, anomaly logs, and approval queues.
          </p>
        </div>

        <div className="pt-2 flex justify-center">
          <Link
            to={role ? '/app/overview' : '/login'}
            className="px-6 py-3 bg-sky-500 hover:bg-sky-700 text-white text-sm font-semibold rounded-btn transition-all shadow-md flex items-center gap-2 hover:-translate-y-0.5 active:translate-y-0"
          >
            <span>Open control center</span>
            <ArrowRight className="w-4 h-4 stroke-[1.5]" />
          </Link>
        </div>
      </div>
    </section>
  );
};
