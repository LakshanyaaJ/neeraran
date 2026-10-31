import React from 'react';
import { motion, useInView, useReducedMotion } from 'framer-motion';
import { useRef } from 'react';
import { AlertCircle, Clock } from 'lucide-react';

export const NightLeakStory: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(sectionRef, { once: true, margin: '-80px' });
  const shouldReduceMotion = useReducedMotion();

  return (
    <section ref={sectionRef} className="py-20 px-4 sm:px-6 max-w-6xl mx-auto space-y-10">
      <div className="max-w-2xl space-y-3 text-left">
        <div className="inline-flex items-center gap-2 px-3 py-1 glass-pill text-xs font-semibold text-sky-700 dark:text-sky-300">
          <span>Physical Detection Story</span>
        </div>
        <h2 className="text-3xl sm:text-4xl font-light text-ink-900 tracking-tight">
          A leak looks like a <span className="font-bold text-ink-900">normal night</span>.
        </h2>
        <p className="text-sm sm:text-base text-ink-600 leading-relaxed font-normal">
          Between 02:00 and 04:30 AM, residential hostels sleep, and flow meters settle at their minimum night baseline of <strong className="text-ink-900">14 L/min</strong>. When joint corrosion cracked Branch L-2, the line held at <strong className="text-coral">62 L/min</strong>. A totalizer saw normal consumption. NEERARAN saw an uncharacteristic 48-litre bleed.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center text-left">
        {/* Left: Two Engineering Numbers */}
        <div className="lg:col-span-4 space-y-4">
          <div className="glass-panel p-5 space-y-1 border-l-4 border-l-leaf">
            <span className="text-xs text-ink-600 font-medium">Expected Minimum Night Flow</span>
            <div className="text-3xl font-bold font-mono text-ink-900">
              14.2 <span className="text-xs font-sans font-normal text-ink-600">L/min</span>
            </div>
            <p className="text-[11px] text-ink-600">
              Typical fixture seal baseline across Cauvery and Vaigai hostels at 03:00 AM.
            </p>
          </div>

          <div className="glass-panel p-5 space-y-1 border-l-4 border-l-coral">
            <span className="text-xs text-coral font-medium">Registered Abnormal Flow</span>
            <div className="text-3xl font-bold font-mono text-coral">
              62.8 <span className="text-xs font-sans font-normal text-ink-600">L/min</span>
            </div>
            <p className="text-[11px] text-ink-600">
              +48.6 L/min nocturnal weepage detected by IsolationForest residual analysis.
            </p>
          </div>
        </div>

        {/* Right: Interactive Flow Line Chart with Animated Coral Marker */}
        <div className="lg:col-span-8 glass-panel p-6 space-y-4 bg-white/70 dark:bg-sky-950/40 border border-white/80 dark:border-white/10">
          <div className="flex items-center justify-between text-xs text-ink-600 pb-2 border-b border-ink-600/10">
            <div className="flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-sky-500 stroke-[1.5]" />
              <span className="font-medium text-ink-900">Telemetry Stream: FM-03 (Vaigai Hostel Feed)</span>
            </div>
            <span className="font-mono text-[11px]">Sampling: 1-min intervals</span>
          </div>

          {/* SVG Chart */}
          <div className="relative w-full h-56 sm:h-64">
            <svg viewBox="0 0 700 240" className="w-full h-full overflow-visible">
              {/* Grid Lines */}
              <line x1="40" y1="40" x2="680" y2="40" stroke="currentColor" strokeOpacity="0.08" strokeDasharray="4 4" />
              <line x1="40" y1="100" x2="680" y2="100" stroke="currentColor" strokeOpacity="0.08" strokeDasharray="4 4" />
              <line x1="40" y1="160" x2="680" y2="160" stroke="currentColor" strokeOpacity="0.08" strokeDasharray="4 4" />
              <line x1="40" y1="210" x2="680" y2="210" stroke="currentColor" strokeOpacity="0.15" />

              {/* Y-Axis Labels */}
              <text x="32" y="44" textAnchor="end" className="text-[10px] font-mono fill-current opacity-40">100 L</text>
              <text x="32" y="104" textAnchor="end" className="text-[10px] font-mono fill-current opacity-40">60 L</text>
              <text x="32" y="164" textAnchor="end" className="text-[10px] font-mono fill-current opacity-40">20 L</text>

              {/* Expected Baseline Curve (Dotted Green) */}
              <path
                d="M50,70 C140,80 200,120 280,180 C360,200 440,200 520,180 C580,140 640,90 680,60"
                fill="none"
                stroke="#4CBF86"
                strokeWidth="1.8"
                strokeDasharray="4 4"
                opacity="0.6"
              />

              {/* Actual Sensor Curve (Drawn with Motion) */}
              <motion.path
                d="M50,70 C140,80 200,110 280,110 C360,105 440,108 520,102 C580,95 640,80 680,60"
                fill="none"
                stroke="#3A8FDA"
                strokeWidth="2.5"
                initial={{ pathLength: shouldReduceMotion ? 1 : 0 }}
                animate={isInView ? { pathLength: 1 } : { pathLength: 0 }}
                transition={{ duration: 1.8, ease: 'easeOut' }}
              />

              {/* Coral Marker: Where Agent Flags the Leak */}
              {isInView && (
                <g>
                  {/* Ping circle */}
                  <motion.circle
                    cx="360"
                    cy="105"
                    r="8"
                    fill="#E5594F"
                    initial={{ scale: 0.8, opacity: 0.8 }}
                    animate={{ scale: [1, 2.2, 1], opacity: [0.8, 0, 0.8] }}
                    transition={{ repeat: Infinity, duration: 1.8 }}
                  />
                  <circle cx="360" cy="105" r="4.5" fill="#E5594F" />

                  {/* Marker Stem & Box */}
                  <line x1="360" y1="105" x2="360" y2="40" stroke="#E5594F" strokeWidth="1.5" />
                  <rect x="270" y="12" width="180" height="26" rx="6" fill="#E5594F" />
                  <text x="360" y="29" textAnchor="middle" fill="#FFFFFF" className="text-[10px] font-semibold">
                    Flagged 02:47 AM (EVID-PRS-4029)
                  </text>
                </g>
              )}

              {/* X-Axis Labels */}
              <text x="50" y="230" textAnchor="middle" className="text-[10px] font-mono fill-current opacity-50">23:00</text>
              <text x="200" y="230" textAnchor="middle" className="text-[10px] font-mono fill-current opacity-50">01:00</text>
              <text x="360" y="230" textAnchor="middle" className="text-[10px] font-mono fill-current font-bold text-coral">03:00</text>
              <text x="520" y="230" textAnchor="middle" className="text-[10px] font-mono fill-current opacity-50">05:00</text>
              <text x="680" y="230" textAnchor="middle" className="text-[10px] font-mono fill-current opacity-50">07:00</text>
            </svg>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px] text-ink-600">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-leaf inline-block border-b border-dashed" />
                <span>Normal Diurnal Model (14 L/min)</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-sky-500 inline-block" />
                <span>Live Ultrasonic Telemetry (62 L/min)</span>
              </span>
            </div>
            <span className="text-coral font-medium flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5 stroke-[1.5]" />
              Residual deviation: +48.6 L/min
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};
