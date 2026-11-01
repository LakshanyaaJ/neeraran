import React, { useRef } from 'react';
import { motion, useScroll, useTransform, useReducedMotion } from 'framer-motion';
import { Droplet, Layers, Activity, CloudSun, ShieldCheck, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export const HeroPreviewCard: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const shouldReduceMotion = useReducedMotion();

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start end', 'end start'],
  });

  // Straightens from 6 deg tilt, lifts, and scales
  const rotateZ = useTransform(scrollYProgress, [0, 0.45], [6, 0]);
  const rotateX = useTransform(scrollYProgress, [0, 0.45], [8, 0]);
  const translateY = useTransform(scrollYProgress, [0, 0.45], [50, -10]);
  const scale = useTransform(scrollYProgress, [0, 0.45], [0.94, 1.0]);

  return (
    <div ref={containerRef} className="w-full max-w-5xl mx-auto px-2 sm:px-6 relative z-20">
      <motion.div
        style={{
          rotateZ: shouldReduceMotion ? 0 : rotateZ,
          rotateX: shouldReduceMotion ? 0 : rotateX,
          y: shouldReduceMotion ? 0 : translateY,
          scale: shouldReduceMotion ? 1 : scale,
          transformPerspective: 1200,
        }}
        className="glass-panel p-4 sm:p-6 bg-white/85 dark:bg-[#101E2E]/90 border border-white/90 dark:border-white/10 shadow-hero-card rounded-[28px] overflow-hidden transition-all duration-300"
      >
        {/* Mini Control Center Topbar */}
        <div className="flex items-center justify-between pb-4 border-b border-ink-600/10 text-xs">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-leaf animate-ping" />
              <span className="w-2.5 h-2.5 rounded-full bg-leaf -ml-4" />
              <span className="font-semibold text-leaf text-[11px]">Digital Twin Active</span>
            </div>
            <span className="text-ink-600 hidden sm:inline">•</span>
            <span className="text-ink-600 font-mono text-[11px] hidden sm:inline">Seed: 42 • 10Hz Tick</span>
          </div>

          <div className="flex items-center gap-2">
            <div className="glass-pill px-2.5 py-0.5 text-[11px] font-medium text-ink-900 border-sky-100 dark:border-white/10">
              Role: Estate Admin
            </div>
            <Link
              to="/app/overview"
              className="px-2.5 py-0.5 bg-sky-500 hover:bg-sky-700 text-white rounded-pill text-[11px] font-medium flex items-center gap-1 transition-colors"
            >
              <span>Open live</span>
              <ArrowUpRight className="w-3 h-3 stroke-[1.5]" />
            </Link>
          </div>
        </div>

        {/* Mini KPI Cards Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 py-4 text-left">
          {/* Sump */}
          <div className="p-3 bg-mist/60 dark:bg-sky-950/40 rounded-btn border border-sky-100/60 dark:border-white/5 space-y-1">
            <div className="flex items-center justify-between text-ink-600 text-[11px]">
              <span>Campus Sump</span>
              <Droplet className="w-3.5 h-3.5 text-sky-500 stroke-[1.5]" />
            </div>
            <div className="text-lg font-bold font-mono text-ink-900">390.0 <span className="text-[10px] font-sans font-normal text-ink-600">kL</span></div>
            <div className="w-full bg-sky-100 dark:bg-sky-900/40 h-1 rounded-full overflow-hidden">
              <div className="bg-sky-500 h-full w-[78%]" />
            </div>
          </div>

          {/* Reserves */}
          <div className="p-3 bg-mist/60 dark:bg-sky-950/40 rounded-btn border border-sky-100/60 dark:border-white/5 space-y-1">
            <div className="flex items-center justify-between text-ink-600 text-[11px]">
              <span>Reserves</span>
              <Layers className="w-3.5 h-3.5 text-leaf stroke-[1.5]" />
            </div>
            <div className="text-lg font-bold font-mono text-ink-900">646.5 <span className="text-[10px] font-sans font-normal text-ink-600">kL</span></div>
            <div className="text-[10px] text-leaf font-medium flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 stroke-[1.5]" />
              <span>+11.1 hrs headroom</span>
            </div>
          </div>

          {/* Demand */}
          <div className="p-3 bg-mist/60 dark:bg-sky-950/40 rounded-btn border border-sky-100/60 dark:border-white/5 space-y-1">
            <div className="flex items-center justify-between text-ink-600 text-[11px]">
              <span>Demand</span>
              <Activity className="w-3.5 h-3.5 text-amber stroke-[1.5]" />
            </div>
            <div className="text-lg font-bold font-mono text-ink-900">973.0 <span className="text-[10px] font-sans font-normal text-ink-600">L/min</span></div>
            <div className="text-[10px] text-ink-600">20 blocks active</div>
          </div>

          {/* Weather */}
          <div className="p-3 bg-mist/60 dark:bg-sky-950/40 rounded-btn border border-sky-100/60 dark:border-white/5 space-y-1">
            <div className="flex items-center justify-between text-ink-600 text-[11px]">
              <span>Weather</span>
              <CloudSun className="w-3.5 h-3.5 text-sky-700 stroke-[1.5]" />
            </div>
            <div className="text-lg font-bold font-mono text-ink-900">28.4°C</div>
            <div className="text-[10px] text-sky-700 dark:text-sky-300 font-medium">Clear sky • 65% RH</div>
          </div>
        </div>

        {/* Live Anomaly Detection Banner with Pulsing Dot */}
        <div className="p-3.5 bg-coral/10 border border-coral/30 rounded-btn flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-left">
          <div className="flex items-start gap-2.5">
            <div className="relative mt-0.5">
              <span className="w-3 h-3 rounded-full bg-coral block animate-ping" />
              <span className="w-3 h-3 rounded-full bg-coral block absolute inset-0" />
            </div>

            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-coral">Piezoresistive Anomaly Flagged</span>
                <span className="text-[10px] font-mono bg-white/80 dark:bg-sky-950/80 px-1.5 py-0.5 rounded text-ink-600">
                  EVID-PRS-4029
                </span>
              </div>
              <p className="text-xs text-ink-900 font-medium">
                Nocturnal weepage detected on Supply Branch L-2 (Vaigai Hostel Feed). Estimated loss: 48 L/min.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-[11px] text-ink-600 hidden md:inline">Recommendation: Throttle valve to 65%</span>
            <span className="px-2 py-1 bg-white dark:bg-sky-900/50 text-ink-900 text-[11px] font-semibold rounded-btn border border-slate-200 dark:border-white/10 shadow-sm">
              Plan Generated
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
