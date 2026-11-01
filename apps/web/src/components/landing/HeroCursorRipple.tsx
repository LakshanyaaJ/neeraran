import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';

interface Ripple {
  id: number;
  x: number;
  y: number;
}

interface HeroCursorRippleProps {
  containerRef: React.RefObject<HTMLDivElement | null>;
}

export const HeroCursorRipple: React.FC<HeroCursorRippleProps> = ({ containerRef }) => {
  const shouldReduceMotion = useReducedMotion();
  const [ripples, setRipples] = useState<Ripple[]>([]);

  useEffect(() => {
    if (shouldReduceMotion) return;

    const container = containerRef.current;
    if (!container) return;

    let lastTime = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const now = Date.now();
      // Throttle ripple spawn to every 80ms for performance
      if (now - lastTime < 80) return;
      lastTime = now;

      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const newRipple: Ripple = {
        id: now,
        x,
        y,
      };

      setRipples((prev) => [...prev.slice(-6), newRipple]);
    };

    container.addEventListener('mousemove', handleMouseMove);
    return () => container.removeEventListener('mousemove', handleMouseMove);
  }, [containerRef, shouldReduceMotion]);

  if (shouldReduceMotion) return null;

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-10">
      <AnimatePresence>
        {ripples.map((r) => (
          <motion.div
            key={r.id}
            initial={{ scale: 0.4, opacity: 0.35 }}
            animate={{ scale: 2.8, opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.9, ease: 'easeOut' }}
            onAnimationComplete={() => {
              setRipples((prev) => prev.filter((item) => item.id !== r.id));
            }}
            style={{
              position: 'absolute',
              left: r.x - 24,
              top: r.y - 24,
              width: 48,
              height: 48,
              borderRadius: '9999px',
              border: '1.5px solid rgba(255, 255, 255, 0.65)',
              boxShadow: '0 0 16px rgba(58, 143, 218, 0.3)',
            }}
          />
        ))}
      </AnimatePresence>
    </div>
  );
};

