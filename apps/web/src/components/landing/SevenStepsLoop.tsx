import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useScroll, useReducedMotion } from 'framer-motion';
import { 
  Activity, 
  AlertTriangle, 
  TrendingUp, 
  ListOrdered, 
  Sliders, 
  CheckSquare, 
  Gauge,
  Check,
  X
} from 'lucide-react';

interface StepData {
  id: string;
  number: string;
  title: string;
  subtitle: string;
  question: string;
}

const STEPS: StepData[] = [
  {
    id: 'monitor',
    number: '01',
    title: 'Monitor',
    subtitle: 'Ultrasonic meters, piezoresistive pressure, tank sounders',
    question: 'Where is water moving right now across the 24 segments?',
  },
  {
    id: 'detect',
    number: '02',
    title: 'Detect',
    subtitle: 'IsolationForest & dynamic residual headloss analysis',
    question: 'Is this sudden drop normal diurnal usage or a burst weepage?',
  },
  {
    id: 'predict',
    number: '03',
    title: 'Predict',
    subtitle: 'Holt-Winters diurnal seasonal demand forecasting',
    question: 'Will the 80 kL North tank run dry before the evening mess load?',
  },
  {
    id: 'prioritize',
    number: '04',
    title: 'Prioritize',
    subtitle: 'Criticality scoring with strict vulnerable zone weighting',
    question: 'Which of the 3 active alerts impacts student health and safety?',
  },
  {
    id: 'optimize',
    number: '05',
    title: 'Optimize',
    subtitle: 'Linear programming allocator (scipy.optimize.linprog)',
    question: 'What pump dispatch and valve throttle preserves the 500 kL sump?',
  },
  {
    id: 'intervene',
    number: '06',
    title: 'Intervene',
    subtitle: 'SCADA valve actuation and CMMS work order dispatch',
    question: 'Wait for Estate Admin clearance before modulating line pressure.',
  },
  {
    id: 'measure',
    number: '07',
    title: 'Measure',
    subtitle: 'Continuous evaluation against physical ground truth',
    question: 'Did the intervention save the targeted 48 kL with 0 equity violations?',
  },
];

export const SevenStepsLoop: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const shouldReduceMotion = useReducedMotion();

  // Scroll listener to update active step as user scrolls down the section
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start center', 'end center'],
  });

  useEffect(() => {
    if (shouldReduceMotion) return;
    const unsubscribe = scrollYProgress.on('change', (latest) => {
      // Map scroll progress 0.0 - 1.0 to steps 0 - 6
      const stepIndex = Math.min(STEPS.length - 1, Math.max(0, Math.floor(latest * STEPS.length)));
      setActiveStep(stepIndex);
    });
    return () => unsubscribe();
  }, [scrollYProgress, shouldReduceMotion]);

  const currentStep = STEPS[activeStep];

  return (
    <section id="how-it-works" ref={containerRef} className="py-24 px-4 sm:px-6 max-w-6xl mx-auto space-y-12 text-left">
      <div className="space-y-3 max-w-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 glass-pill text-xs font-semibold text-sky-700 dark:text-sky-300">
          <span>Autonomous Resilience Loop</span>
        </div>
        <h2 className="text-3xl sm:text-4xl font-light text-ink-900 tracking-tight">
          Seven steps, <span className="font-bold text-ink-900">one loop</span>.
        </h2>
        <p className="text-sm sm:text-base text-ink-600">
          Each screen directly answers what to do next, where, and why. Scroll to see the engine execute from raw telemetry to ground-truth validation.
        </p>
      </div>

      {/* Horizontal Progress Bar connecting steps */}
      <div className="relative pt-2 pb-6 overflow-x-auto no-scrollbar">
        {/* Track Line */}
        <div className="absolute top-7 left-4 right-4 h-0.5 bg-sky-100 dark:bg-sky-950/60 z-0" />
        
        {/* Drawn Active Line */}
        <motion.div
          className="absolute top-7 left-4 h-0.5 bg-sky-500 z-0 transition-all duration-300"
          style={{
            width: `${(activeStep / (STEPS.length - 1)) * 96}%`,
          }}
        />

        <div className="relative z-10 flex justify-between min-w-[620px] px-2">
          {STEPS.map((s, idx) => {
            const isActive = idx === activeStep;
            const isCompleted = idx < activeStep;
            return (
              <button
                key={s.id}
                onClick={() => setActiveStep(idx)}
                className="flex flex-col items-center gap-2 group transition-all text-left"
              >
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center font-mono text-xs font-bold transition-all shadow-sm ${
                    isActive
                      ? 'bg-sky-500 text-white scale-110 ring-4 ring-sky-100 dark:ring-sky-900/40'
                      : isCompleted
                      ? 'bg-sky-700 text-white'
                      : 'bg-white dark:bg-sky-950/60 text-ink-600 border border-sky-100 dark:border-white/10 group-hover:border-sky-300'
                  }`}
                >
                  {s.number}
                </div>
                <span
                  className={`text-xs whitespace-nowrap font-medium transition-colors ${
                    isActive
                      ? 'text-ink-900 font-bold'
                      : 'text-ink-600 group-hover:text-ink-900'
                  }`}
                >
                  {s.title}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Bento Two-Column Step Stage Visualizer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        {/* Left: Step Description */}
        <div className="lg:col-span-5 glass-panel p-6 sm:p-8 flex flex-col justify-between space-y-6">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-sky-700 dark:text-sky-300 bg-sky-50 dark:bg-sky-950/60 px-2.5 py-1 rounded-btn border border-sky-100 dark:border-white/10">
                Step {currentStep.number} of 07
              </span>
              <span className="text-xs text-ink-600 font-medium">Continuous Cycle</span>
            </div>

            <h3 className="text-2xl font-bold text-ink-900">
              {currentStep.title}
            </h3>

            <p className="text-sm text-ink-600">
              {currentStep.subtitle}
            </p>

            <div className="p-4 rounded-btn bg-white/70 dark:bg-sky-950/40 border border-sky-100 dark:border-white/10 space-y-1">
              <span className="text-[11px] font-semibold text-sky-700 dark:text-sky-300">
                Operational question answered:
              </span>
              <p className="text-xs font-medium text-ink-900">
                "{currentStep.question}"
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-4 border-t border-ink-600/10 text-xs text-ink-600">
            <span>Click any step above to inspect</span>
          </div>
        </div>

        {/* Right: Swappable Live Visual */}
        <div className="lg:col-span-7 glass-panel p-6 sm:p-8 flex items-center justify-center bg-white/60 dark:bg-sky-950/40 border border-white/80 dark:border-white/10 min-h-[360px]">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep.id}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
              className="w-full"
            >
              {activeStep === 0 && (
                /* Step 0: Monitor Ticks */
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs pb-2 border-b border-ink-600/10">
                    <span className="font-semibold text-ink-900 flex items-center gap-1.5">
                      <Activity className="w-4 h-4 text-sky-500 stroke-[1.5]" />
                      Real-time Ultrasonic Ticks
                    </span>
                    <span className="font-mono text-leaf text-[11px] font-bold">10Hz Synchronized</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                    <div className="p-3 bg-white/80 dark:bg-sky-900/30 rounded-btn border border-sky-100 dark:border-white/5 space-y-1">
                      <span className="text-ink-600 text-[10px]">FM-01 Cauvery Boys Hostel</span>
                      <div className="text-lg font-bold text-ink-900">95.4 <span className="text-xs font-normal">L/min</span></div>
                      <span className="text-[10px] text-leaf">Head: 2.45 bar</span>
                    </div>
                    <div className="p-3 bg-white/80 dark:bg-sky-900/30 rounded-btn border border-sky-100 dark:border-white/5 space-y-1">
                      <span className="text-ink-600 text-[10px]">FM-03 Vaigai Girls Hostel</span>
                      <div className="text-lg font-bold text-coral">62.8 <span className="text-xs font-normal">L/min</span></div>
                      <span className="text-[10px] text-coral font-medium">Head drop: 1.70 bar</span>
                    </div>
                    <div className="p-3 bg-white/80 dark:bg-sky-900/30 rounded-btn border border-sky-100 dark:border-white/5 space-y-1">
                      <span className="text-ink-600 text-[10px]">FM-04 Health Centre</span>
                      <div className="text-lg font-bold text-ink-900">22.1 <span className="text-xs font-normal">L/min</span></div>
                      <span className="text-[10px] text-leaf">Strict Vulnerable: Guarded</span>
                    </div>
                    <div className="p-3 bg-white/80 dark:bg-sky-900/30 rounded-btn border border-sky-100 dark:border-white/5 space-y-1">
                      <span className="text-ink-600 text-[10px]">FM-06 Central Mess Complex</span>
                      <div className="text-lg font-bold text-ink-900">121.5 <span className="text-xs font-normal">L/min</span></div>
                      <span className="text-[10px] text-sky-700 dark:text-sky-300">Breakfast prep surge</span>
                    </div>
                  </div>
                </div>
              )}

              {activeStep === 1 && (
                /* Step 1: Detect Spike */
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs pb-2 border-b border-ink-600/10">
                    <span className="font-semibold text-coral flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-coral stroke-[1.5]" />
                      IsolationForest Residual Spike
                    </span>
                    <span className="font-mono text-xs bg-coral/10 text-coral px-2 py-0.5 rounded font-bold">Score: -0.84</span>
                  </div>
                  <div className="p-4 bg-coral/5 border border-coral/20 rounded-btn space-y-2 text-xs">
                    <div className="flex justify-between font-mono">
                      <span>Anomaly Identifier:</span>
                      <span className="font-bold text-ink-900">EVID-PRS-4029</span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span>Location:</span>
                      <span className="text-ink-900">PIPE-H-03 (Vaigai Distribution)</span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span>Residual Gap:</span>
                      <span className="text-coral font-bold">+48.6 L/min above baseline</span>
                    </div>
                  </div>
                </div>
              )}

              {activeStep === 2 && (
                /* Step 2: Predict Forecast Band */
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs pb-2 border-b border-ink-600/10">
                    <span className="font-semibold text-ink-900 flex items-center gap-1.5">
                      <TrendingUp className="w-4 h-4 text-sky-500 stroke-[1.5]" />
                      Holt-Winters 24h Diurnal Forecast Envelope
                    </span>
                    <span className="font-mono text-leaf text-xs">MAPE: 6.4%</span>
                  </div>
                  <div className="p-4 bg-white/80 dark:bg-sky-900/30 rounded-btn border border-sky-100 dark:border-white/5 space-y-2 text-xs">
                    <div className="flex justify-between font-mono">
                      <span>Peak Demand Window:</span>
                      <span className="text-ink-900 font-bold">12:30 - 14:00 (Lunch Prep)</span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span>Projected Hostels Draw:</span>
                      <span className="text-ink-900 font-bold">295 kL / day</span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span>OHT-Hostel Runout Risk:</span>
                      <span className="text-leaf font-bold">None (18.2 hrs reserve maintained)</span>
                    </div>
                  </div>
                </div>
              )}

              {activeStep === 3 && (
                /* Step 3: Prioritize Criticality */
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs pb-2 border-b border-ink-600/10">
                    <span className="font-semibold text-ink-900 flex items-center gap-1.5">
                      <ListOrdered className="w-4 h-4 text-amber stroke-[1.5]" />
                      Ranked Mitigation Queue
                    </span>
                    <span className="text-xs text-ink-600">Vulnerable Zones First</span>
                  </div>
                  <div className="space-y-2 text-xs">
                    <div className="p-2.5 bg-amber/10 border border-amber/30 rounded-btn flex items-center justify-between font-mono">
                      <span>1. Vaigai Hostel Branch (Vulnerable)</span>
                      <span className="text-coral font-bold">Score: 98/100</span>
                    </div>
                    <div className="p-2.5 bg-white/70 dark:bg-sky-900/30 border border-slate-200 dark:border-white/5 rounded-btn flex items-center justify-between font-mono">
                      <span>2. Campus Health Centre Line (Vulnerable)</span>
                      <span className="text-leaf font-bold">Score: 42/100</span>
                    </div>
                    <div className="p-2.5 bg-white/70 dark:bg-sky-900/30 border border-slate-200 dark:border-white/5 rounded-btn flex items-center justify-between font-mono">
                      <span>3. Sports Turf Recycled Loop</span>
                      <span className="text-ink-600 font-bold">Score: 18/100</span>
                    </div>
                  </div>
                </div>
              )}

              {activeStep === 4 && (
                /* Step 4: Optimize Plan */
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs pb-2 border-b border-ink-600/10">
                    <span className="font-semibold text-ink-900 flex items-center gap-1.5">
                      <Sliders className="w-4 h-4 text-sky-700 stroke-[1.5]" />
                      scipy.optimize.linprog Modulation Schedule
                    </span>
                    <span className="font-mono text-leaf text-xs">Convergence: Optimal</span>
                  </div>
                  <div className="p-4 bg-sky-50 dark:bg-sky-950/60 rounded-btn border border-sky-100 dark:border-white/10 space-y-2 text-xs font-mono">
                    <div className="flex justify-between">
                      <span>Target Valve:</span>
                      <span className="text-ink-900 font-bold">VALVE-03-VGH</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Modulation Action:</span>
                      <span className="text-sky-700 dark:text-sky-300 font-bold">Throttle to 65% (01:00 - 05:00)</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Predicted Weepage Cut:</span>
                      <span className="text-leaf font-bold">36.5 L/min saved</span>
                    </div>
                  </div>
                </div>
              )}

              {activeStep === 5 && (
                /* Step 5: Intervene Card */
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs pb-2 border-b border-ink-600/10">
                    <span className="font-semibold text-ink-900 flex items-center gap-1.5">
                      <CheckSquare className="w-4 h-4 text-sky-500 stroke-[1.5]" />
                      Human Authorization Gate (Admin Only)
                    </span>
                    <span className="text-[10px] bg-amber/10 text-amber px-2 py-0.5 rounded font-bold">Pending Approval</span>
                  </div>
                  <div className="p-4 bg-white/80 dark:bg-sky-900/30 rounded-btn border border-sky-100 dark:border-white/5 space-y-3 text-xs">
                    <p className="font-medium text-ink-900">
                      Dispatches SCADA valve throttle command to curtail joint bleed without impacting tap pressure.
                    </p>
                    <div className="flex gap-2">
                      <button className="flex-1 py-1.5 bg-sky-500 text-white rounded-btn font-semibold flex items-center justify-center gap-1">
                        <Check className="w-3.5 h-3.5" /> Approve
                      </button>
                      <button className="flex-1 py-1.5 bg-white text-coral border border-coral/30 rounded-btn font-semibold flex items-center justify-center gap-1">
                        <X className="w-3.5 h-3.5" /> Reject
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {activeStep === 6 && (
                /* Step 6: Measure Scoreboard */
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs pb-2 border-b border-ink-600/10">
                    <span className="font-semibold text-ink-900 flex items-center gap-1.5">
                      <Gauge className="w-4 h-4 text-leaf stroke-[1.5]" />
                      Simulator Ground-Truth Validation
                    </span>
                    <span className="font-mono text-leaf text-xs font-bold">Audit Verified</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                    <div className="p-3 bg-leaf/10 rounded-btn border border-leaf/20 space-y-1">
                      <span className="text-ink-600 text-[10px]">Net Water Conserved</span>
                      <div className="text-xl font-bold text-leaf">+52.8 kL</div>
                      <span className="text-[10px] text-ink-600">Daily campus total</span>
                    </div>
                    <div className="p-3 bg-sky-50 dark:bg-sky-950/60 rounded-btn border border-sky-100 dark:border-white/10 space-y-1">
                      <span className="text-ink-600 text-[10px]">Equity Violations</span>
                      <div className="text-xl font-bold text-leaf">0</div>
                      <span className="text-[10px] text-ink-600">Strict 100% compliance</span>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
};
