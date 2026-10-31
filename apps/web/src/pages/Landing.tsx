import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import Lenis from 'lenis';
import { Sparkles, ArrowRight, Play } from 'lucide-react';

import { Logo } from '../components/common/Logo';
import { WaterFillText } from '../components/landing/WaterFillText';
import { HeroCloudParallax } from '../components/landing/HeroCloudParallax';
import { HeroCursorRipple } from '../components/landing/HeroCursorRipple';
import { HeroPreviewCard } from '../components/landing/HeroPreviewCard';
import { NightLeakStory } from '../components/landing/NightLeakStory';
import { SevenStepsLoop } from '../components/landing/SevenStepsLoop';
import { HumanInCharge } from '../components/landing/HumanInCharge';
import { NumbersReplay } from '../components/landing/NumbersReplay';
import { ClosingCallout } from '../components/landing/ClosingCallout';
import { useAuthStore } from '../store/auth';

export const Landing: React.FC = () => {
  const { role } = useAuthStore();
  const heroCardRef = useRef<HTMLDivElement>(null);
  const shouldReduceMotion = useReducedMotion();

  // Mouse coordinate state for cloud parallax
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // 1. Lenis Smooth Scroll Lifecycle (active on landing page only)
  useEffect(() => {
    if (shouldReduceMotion) return;

    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      touchMultiplier: 2,
    });

    let rafId: number;
    function raf(time: number) {
      lenis.raf(time);
      rafId = requestAnimationFrame(raf);
    }
    rafId = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(rafId);
      lenis.destroy();
    };
  }, [shouldReduceMotion]);

  // Mouse move handler for Hero parallax
  const handleHeroMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (shouldReduceMotion) return;
    const { clientX, clientY } = e;
    const { innerWidth, innerHeight } = window;
    setMousePos({
      x: (clientX / innerWidth) * 2 - 1,
      y: (clientY / innerHeight) * 2 - 1,
    });
  };

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Staggered unblur animation variants for hero headline words (60ms apart)
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.06,
        delayChildren: 0.15,
      },
    },
  };

  const wordVariants = {
    hidden: {
      opacity: 0,
      y: 18,
      filter: 'blur(8px)',
    },
    visible: {
      opacity: 1,
      y: 0,
      filter: 'blur(0px)',
      transition: {
        duration: 0.45,
        ease: [0.22, 1, 0.36, 1],
      },
    },
  };

  return (
    <div className="min-h-screen bg-mist selection:bg-sky-100 selection:text-sky-700">
      {/* 1. Large Rounded Hero Card (XinoTask look with Sky Gradient) */}
      <div className="p-2.5 sm:p-4 lg:p-6">
        <div
          ref={heroCardRef}
          onMouseMove={handleHeroMouseMove}
          className="relative w-full rounded-[28px] sm:rounded-[36px] lg:rounded-[44px] overflow-hidden shadow-hero-card pt-4 pb-12 sm:pb-20 px-4 sm:px-8 border border-white/80 dark:border-white/10"
          style={{
            background: 'linear-gradient(180deg, #3A93D8 0%, #6BAEE2 32%, #C2DEF6 72%, #F2F6FA 100%)',
          }}
        >
          {/* Cloud Parallax Layers */}
          <HeroCloudParallax mousePos={mousePos} />

          {/* Cursor Soft Ripple Rings */}
          <HeroCursorRipple containerRef={heroCardRef} />

          {/* Thin White Nav inside the Hero Card */}
          <header className="relative z-20 max-w-6xl mx-auto flex items-center justify-between py-2 sm:py-3 px-3 sm:px-6 glass-pill bg-white/70 dark:bg-white/15 border border-white/80 dark:border-white/20 shadow-sm">
            {/* Logo Left */}
            <Logo size="md" />

            {/* Links Centre */}
            <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-ink-900 dark:text-white">
              <button
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                className="hover:text-sky-700 transition-colors"
              >
                Home
              </button>
              <button
                onClick={() => scrollToSection('how-it-works')}
                className="hover:text-sky-700 transition-colors"
              >
                How it works
              </button>
              <button
                onClick={() => scrollToSection('guardrails')}
                className="hover:text-sky-700 transition-colors"
              >
                Guardrails
              </button>
              <button
                onClick={() => scrollToSection('impact')}
                className="hover:text-sky-700 transition-colors"
              >
                Impact
              </button>
              <Link
                to={role ? '/app/evaluation' : '/login'}
                className="hover:text-sky-700 transition-colors"
              >
                Evaluation
              </Link>
            </nav>

            {/* White 'Start for free' style button Right */}
            <Link
              to={role ? '/app/overview' : '/login'}
              className="px-4 py-2 bg-white hover:bg-sky-50 text-sky-700 text-xs font-semibold rounded-pill transition-all shadow-sm hover:shadow hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-1.5"
            >
              <span>Open control center</span>
              <ArrowRight className="w-3.5 h-3.5 stroke-[1.5]" />
            </Link>
          </header>

          {/* Hero Core Content */}
          <div className="relative z-20 max-w-4xl mx-auto text-center pt-12 sm:pt-16 pb-8 space-y-6">
            {/* 2. Pill Badge with Small Sparkle */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 glass-pill bg-white/70 dark:bg-sky-950/40 text-xs font-semibold text-sky-700 dark:text-sky-100 border border-white/80 dark:border-white/10 shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5 text-sky-500 stroke-[1.5]" />
              <span>Campus water, simulated and guarded</span>
            </motion.div>

            {/* 3. Headline: Two lines, light weight with bold phrase & Water-fill 'நீர்' */}
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              className="space-y-1 sm:space-y-2 select-none"
            >
              <div className="text-3xl sm:text-5xl lg:text-6xl font-light text-ink-900 tracking-tight leading-tight sm:leading-snug">
                {['Your', 'all-in-one', 'fortress', 'for'].map((word, i) => (
                  <motion.span
                    key={i}
                    variants={wordVariants}
                    className="inline-block mr-2 sm:mr-3"
                  >
                    {word}
                  </motion.span>
                ))}
              </div>

              <div className="text-3xl sm:text-5xl lg:text-6xl text-ink-900 tracking-tight leading-tight sm:leading-snug flex items-center justify-center flex-wrap gap-2 sm:gap-3">
                {/* Logo glyph tile inline (where XinoTask has the blue X tile) */}
                <motion.span
                  variants={wordVariants}
                  className="inline-flex items-center justify-center p-1.5 sm:p-2 bg-white/80 dark:bg-sky-950/60 rounded-btn border border-white/90 dark:border-white/20 shadow-sm"
                >
                  <WaterFillText size="lg" />
                </motion.span>

                <motion.span
                  variants={wordVariants}
                  className="font-bold text-sky-700 dark:text-sky-900 inline-block"
                >
                  smarter campus water
                </motion.span>
              </div>
            </motion.div>

            {/* 4. One Sentence Subcopy */}
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="text-sm sm:text-base text-ink-600 max-w-xl mx-auto font-normal leading-relaxed"
            >
              Spots a leak before the tank drops, forecasts the shortage, ranks the repairs, and waits for a human to say yes.
            </motion.p>

            {/* 5. Two Action Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              className="flex flex-wrap items-center justify-center gap-3.5 pt-2"
            >
              {/* Solid Blue Button */}
              <Link
                to={role ? '/app/overview' : '/login'}
                className="px-6 py-3 bg-sky-500 hover:bg-sky-700 text-white text-xs sm:text-sm font-semibold rounded-btn transition-all shadow-md hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2"
              >
                <span>Open control center</span>
                <ArrowRight className="w-4 h-4 stroke-[1.5]" />
              </Link>

              {/* Faint Glass Replay Button */}
              <button
                onClick={() => scrollToSection('replay-story')}
                className="px-6 py-3 bg-white/40 hover:bg-white/60 dark:bg-white/10 dark:hover:bg-white/20 backdrop-blur-md text-ink-900 dark:text-sky-950 text-xs sm:text-sm font-semibold rounded-btn border border-white/60 transition-all hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2"
              >
                <Play className="w-3.5 h-3.5 fill-current stroke-[1.5]" />
                <span>Watch the 90-second replay</span>
              </button>
            </motion.div>
          </div>

          {/* 6. Product Preview Card Rising from the Bottom of the Hero */}
          <div className="pt-6">
            <HeroPreviewCard />
          </div>
        </div>
      </div>

      {/* 7. Sections on Mist Background */}
      <div id="replay-story">
        {/* 7.a 'A leak looks like a normal night' */}
        <NightLeakStory />

        {/* 7.b 'Seven steps, one loop' */}
        <SevenStepsLoop />

        {/* 7.c 'You stay in charge' */}
        <HumanInCharge />

        {/* 7.d 'Numbers from the replay' */}
        <NumbersReplay />

        {/* 7.e Closing Band */}
        <ClosingCallout />
      </div>

      {/* Landing Footer */}
      <footer className="py-6 px-4 text-center text-xs text-ink-600 border-t border-ink-600/10">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-tamil font-bold text-sky-700">நீர்</span>
            <span className="font-sans font-bold text-ink-900">Aran</span>
            <span>—</span>
            <span>Every drop accounted for.</span>
          </div>

          <div className="text-[11px] text-ink-600">
            TCS Tech Day • Challenge 12: AI for Water Resilience & Smart Resource Management
          </div>
        </div>
      </footer>
    </div>
  );
};
