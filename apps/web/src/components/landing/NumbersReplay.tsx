import React, { useEffect, useState, useRef } from 'react';
import { useInView, useReducedMotion } from 'framer-motion';

interface CounterProps {
  from?: number;
  to: number;
  duration?: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
}

const AnimatedCounter: React.FC<CounterProps> = ({
  from = 0,
  to,
  duration = 1.6,
  decimals = 0,
  suffix = '',
  prefix = '',
}) => {
  const [val, setVal] = useState(from);
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: '-40px' });
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    if (!inView) return;
    if (shouldReduceMotion) {
      setVal(to);
      return;
    }

    let startTime: number | null = null;
    let animId: number;

    const step = (now: number) => {
      if (!startTime) startTime = now;
      const progress = Math.min(1, (now - startTime) / (duration * 1000));
      // Ease out cubic
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = from + (to - from) * ease;
      setVal(current);

      if (progress < 1) {
        animId = requestAnimationFrame(step);
      } else {
        setVal(to);
      }
    };

    animId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animId);
  }, [inView, from, to, duration, shouldReduceMotion]);

  const formatted = decimals > 0 ? val.toFixed(decimals) : Math.floor(val).toLocaleString();

  return (
    <span ref={ref} className="tabular-nums">
      {prefix}{formatted}{suffix}
    </span>
  );
};

export const NumbersReplay: React.FC = () => {
  return (
    <section id="impact" className="py-24 px-4 sm:px-6 max-w-6xl mx-auto space-y-12 text-left">
      <div className="space-y-3 max-w-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 glass-pill text-xs font-semibold text-sky-700 dark:text-sky-300">
          <span>Digital Twin Physical Evaluation</span>
        </div>
        <h2 className="text-3xl sm:text-4xl font-light text-ink-900 tracking-tight">
          Numbers from the <span className="font-bold text-ink-900">replay</span>.
        </h2>
        <p className="text-sm sm:text-base text-ink-600">
          Quantified directly from the synthetic campus digital twin benchmark (seed 42).
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Metric 1 */}
        <div className="glass-panel p-6 space-y-2 border-t-2 border-t-sky-500">
          <span className="text-xs text-ink-600 font-medium">Leaks Caught</span>
          <div className="text-4xl sm:text-5xl font-bold font-mono text-ink-900 tracking-tight">
            <AnimatedCounter to={14} />
          </div>
          <p className="text-xs text-ink-600 leading-relaxed pt-1">
            Isolated before water levels in any of the 4 overhead tanks dropped below critical.
          </p>
        </div>

        {/* Metric 2 */}
        <div className="glass-panel p-6 space-y-2 border-t-2 border-t-aqua">
          <span className="text-xs text-ink-600 font-medium">Demand Forecast Error</span>
          <div className="text-4xl sm:text-5xl font-bold font-mono text-ink-900 tracking-tight">
            <AnimatedCounter to={6.4} decimals={1} suffix="%" />
          </div>
          <p className="text-xs text-ink-600 leading-relaxed pt-1">
            Mean absolute percentage error (MAPE) across diurnal cycles in academic and residential blocks.
          </p>
        </div>

        {/* Metric 3 */}
        <div className="glass-panel p-6 space-y-2 border-t-2 border-t-leaf">
          <span className="text-xs text-ink-600 font-medium">Daily Water Conserved</span>
          <div className="text-4xl sm:text-5xl font-bold font-mono text-ink-900 tracking-tight">
            <AnimatedCounter to={52800} suffix=" L" />
          </div>
          <p className="text-xs text-ink-600 leading-relaxed pt-1">
            Saved per 24 hours through nocturnal joint weepage curtailment and 112 kL STP recycling.
          </p>
        </div>

        {/* Metric 4 */}
        <div className="glass-panel p-6 space-y-2 border-t-2 border-t-amber">
          <span className="text-xs text-ink-600 font-medium">Reserve Headroom Gained</span>
          <div className="text-4xl sm:text-5xl font-bold font-mono text-ink-900 tracking-tight">
            <AnimatedCounter to={11.4} decimals={1} prefix="+" suffix=" hrs" />
          </div>
          <p className="text-xs text-ink-600 leading-relaxed pt-1">
            Additional campus emergency runout buffer added to the 500 kL central utility sump.
          </p>
        </div>
      </div>
    </section>
  );
};

