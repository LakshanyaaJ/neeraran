import React, { useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

interface HeroCloudParallaxProps {
  mousePos: { x: number; y: number };
}

export const HeroCloudParallax: React.FC<HeroCloudParallaxProps> = ({ mousePos }) => {
  const shouldReduceMotion = useReducedMotion();
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      setScrollY(window.scrollY);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  if (shouldReduceMotion) {
    return (
      <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-30">
        <div className="absolute inset-0 bg-gradient-to-b from-[#3A93D8]/30 via-transparent to-mist" />
      </div>
    );
  }

  // Parallax offsets based on mouse position & window scroll
  const offsetDeep = {
    x: mousePos.x * 12,
    y: mousePos.y * 8 - scrollY * 0.15,
  };
  const offsetMid = {
    x: mousePos.x * 24,
    y: mousePos.y * 14 - scrollY * 0.25,
  };
  const offsetFront = {
    x: mousePos.x * 38,
    y: mousePos.y * 20 - scrollY * 0.40,
  };

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden select-none z-0">
      {/* Cloud Layer 1 (Deepest, Slowest Drift, Large Soft Masses) */}
      <motion.div
        style={{
          transform: `translate3d(${offsetDeep.x}px, ${offsetDeep.y}px, 0)`,
        }}
        className="absolute -top-10 left-0 w-[200%] h-full opacity-40 will-change-transform"
      >
        <div className="w-full h-full animate-[driftClouds_140s_linear_infinite] flex">
          <svg viewBox="0 0 1600 400" className="w-1/2 h-full opacity-70 fill-white" preserveAspectRatio="none">
            <path d="M0,180 C200,90 350,110 500,70 C650,30 850,80 1000,40 C1200,-10 1400,60 1600,20 L1600,400 L0,400 Z" />
          </svg>
          <svg viewBox="0 0 1600 400" className="w-1/2 h-full opacity-70 fill-white" preserveAspectRatio="none">
            <path d="M0,180 C200,90 350,110 500,70 C650,30 850,80 1000,40 C1200,-10 1400,60 1600,20 L1600,400 L0,400 Z" />
          </svg>
        </div>
      </motion.div>

      {/* Cloud Layer 2 (Mid-depth, Medium Drift Speed, Billowing Crests) */}
      <motion.div
        style={{
          transform: `translate3d(${offsetMid.x}px, ${offsetMid.y}px, 0)`,
        }}
        className="absolute top-12 left-0 w-[200%] h-full opacity-55 will-change-transform"
      >
        <div className="w-full h-full animate-[driftClouds_85s_linear_infinite] flex">
          <svg viewBox="0 0 1600 350" className="w-1/2 h-full opacity-80 fill-white/80" preserveAspectRatio="none">
            <path d="M0,220 C180,140 320,180 480,130 C640,80 780,150 960,110 C1140,70 1350,130 1600,90 L1600,350 L0,350 Z" />
          </svg>
          <svg viewBox="0 0 1600 350" className="w-1/2 h-full opacity-80 fill-white/80" preserveAspectRatio="none">
            <path d="M0,220 C180,140 320,180 480,130 C640,80 780,150 960,110 C1140,70 1350,130 1600,90 L1600,350 L0,350 Z" />
          </svg>
        </div>
      </motion.div>

      {/* Cloud Layer 3 (Foreground, Fastest Drift, Whispy Lower Bank) */}
      <motion.div
        style={{
          transform: `translate3d(${offsetFront.x}px, ${offsetFront.y}px, 0)`,
        }}
        className="absolute top-36 left-0 w-[200%] h-full opacity-70 will-change-transform"
      >
        <div className="w-full h-full animate-[driftClouds_50s_linear_infinite] flex">
          <svg viewBox="0 0 1600 300" className="w-1/2 h-full fill-white" preserveAspectRatio="none">
            <path d="M0,260 C240,190 420,240 600,180 C800,120 1000,210 1200,160 C1400,110 1520,170 1600,150 L1600,300 L0,300 Z" />
          </svg>
          <svg viewBox="0 0 1600 300" className="w-1/2 h-full fill-white" preserveAspectRatio="none">
            <path d="M0,260 C240,190 420,240 600,180 C800,120 1000,210 1200,160 C1400,110 1520,170 1600,150 L1600,300 L0,300 Z" />
          </svg>
        </div>
      </motion.div>
    </div>
  );
};

