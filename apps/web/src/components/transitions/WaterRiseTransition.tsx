import React, { useState, useEffect } from 'react';
import { motion, useReducedMotion, AnimatePresence } from 'framer-motion';
import { useLocation } from 'react-router-dom';

interface WaterRiseProps {
  children: React.ReactNode;
}

export const WaterRiseTransition: React.FC<WaterRiseProps> = ({ children }) => {
  const location = useLocation();
  const shouldReduceMotion = useReducedMotion();
  const [isWaterRising, setIsWaterRising] = useState(false);
  const [displayLocation, setDisplayLocation] = useState(location);

  // Trigger full water-rise only on major route boundary changes (e.g. entering /app or leaving /app or /login)
  const isMajorTransition = (prevPath: string, nextPath: string) => {
    const isPrevApp = prevPath.startsWith('/app');
    const isNextApp = nextPath.startsWith('/app');
    // If navigating inside /app between tabs, do NOT play full-screen 700ms water rise
    if (isPrevApp && isNextApp) {
      return false;
    }
    return prevPath !== nextPath;
  };

  useEffect(() => {
    if (location.pathname !== displayLocation.pathname) {
      if (isMajorTransition(displayLocation.pathname, location.pathname) && !shouldReduceMotion) {
        setIsWaterRising(true);
        // Step 1: Rise takes 450ms, hold 150ms = at 500ms swap content
        const swapTimer = setTimeout(() => {
          setDisplayLocation(location);
        }, 450);

        // Step 2: Total duration before finishing drain upward = 680ms (< 700ms rule)
        const completeTimer = setTimeout(() => {
          setIsWaterRising(false);
        }, 680);

        return () => {
          clearTimeout(swapTimer);
          clearTimeout(completeTimer);
        };
      } else {
        // Quick transition or reduced motion
        setDisplayLocation(location);
      }
    }
  }, [location, displayLocation, shouldReduceMotion]);

  if (shouldReduceMotion) {
    return (
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18 }}
      >
        {children}
      </motion.div>
    );
  }

  return (
    <div className="relative w-full min-h-screen">
      {/* Full-screen Water-Rise Curtains */}
      <AnimatePresence>
        {isWaterRising && (
          <motion.div
            key="water-curtain"
            className="fixed inset-0 z-50 pointer-events-none flex flex-col items-center justify-center bg-sky-500 overflow-hidden shadow-2xl"
            initial={{ y: '100%' }}
            animate={{
              y: ['100%', '0%', '0%', '-100%'],
            }}
            transition={{
              duration: 0.68,
              times: [0, 0.45, 0.60, 1.0],
              ease: [0.22, 1, 0.36, 1],
            }}
          >
            {/* Wavy top edge of the water curtain */}
            <div className="absolute top-0 left-0 w-full overflow-hidden leading-none -translate-y-[98%]">
              <svg
                viewBox="0 0 1200 120"
                preserveAspectRatio="none"
                className="relative block w-full h-12 text-sky-500 fill-current"
              >
                <path d="M0,0 C150,90 350,-40 500,50 C650,140 900,-20 1200,40 L1200,120 L0,120 Z" />
              </svg>
            </div>

            {/* Glowing Tamil நீர் Glyph holding for 150ms */}
            <motion.div
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: [0, 1, 1, 0], scale: [0.85, 1, 1, 1.05] }}
              transition={{
                duration: 0.68,
                times: [0.2, 0.45, 0.60, 0.85],
              }}
              className="text-white text-center select-none"
            >
              <span className="font-tamil font-bold text-6xl tracking-wider block">
                நீர்
              </span>
              <span className="font-sans font-light text-xs text-sky-100 tracking-widest mt-1 block">
                WATER FORTRESS
              </span>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Page Content */}
      <motion.div
        key={displayLocation.pathname}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.32, ease: 'easeOut' }}
        className="w-full min-h-screen"
      >
        {children}
      </motion.div>
    </div>
  );
};

/**
 * TabTransition for tabs inside /app.
 * Faster 180 ms crossfade with an 8 px upward slide.
 */
export const TabTransition: React.FC<{ children: React.ReactNode; tabKey: string }> = ({
  children,
  tabKey,
}) => {
  const shouldReduceMotion = useReducedMotion();

  if (shouldReduceMotion) {
    return <div>{children}</div>;
  }

  return (
    <motion.div
      key={tabKey}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
      className="w-full"
    >
      {children}
    </motion.div>
  );
};
