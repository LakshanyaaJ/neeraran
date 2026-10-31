import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';

interface WaterFillTextProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

/**
 * WaterFillText renders the Tamil word 'நீர்' with an animated liquid wave fill effect.
 * The water rises from bottom to top on initial load, then idles with a faint subtle ripple.
 */
export const WaterFillText: React.FC<WaterFillTextProps> = ({
  className = '',
  size = 'xl',
}) => {
  const shouldReduceMotion = useReducedMotion();

  const fontSizes = {
    sm: 'text-2xl',
    md: 'text-4xl',
    lg: 'text-5xl sm:text-6xl',
    xl: 'text-5xl sm:text-7xl lg:text-8xl',
  }[size];

  if (shouldReduceMotion) {
    return (
      <span className={`font-tamil font-bold text-sky-700 dark:text-sky-300 inline-block ${fontSizes} ${className}`}>
        நீர்
      </span>
    );
  }

  return (
    <span className={`relative inline-block select-none overflow-hidden font-tamil font-bold ${fontSizes} ${className}`}>
      {/* Background outline/hollow text */}
      <span className="text-sky-300/40 dark:text-sky-900/40 leading-none">
        நீர்
      </span>

      {/* Rising liquid wave clip container */}
      <motion.span
        initial={{ height: '0%' }}
        animate={{ height: '100%' }}
        transition={{
          duration: 1.4,
          delay: 0.3,
          ease: [0.16, 1, 0.3, 1],
        }}
        className="absolute bottom-0 left-0 right-0 overflow-hidden text-sky-700 dark:text-sky-300 pointer-events-none"
      >
        {/* Full filled text anchored to the bottom */}
        <span className="absolute bottom-0 left-0 leading-none whitespace-nowrap">
          நீர்
        </span>

        {/* Subtle idle surface ripple line */}
        <motion.span
          animate={{
            x: ['-50%', '0%'],
          }}
          transition={{
            repeat: Infinity,
            duration: 4,
            ease: 'linear',
          }}
          className="absolute top-0 left-0 w-[200%] h-1 bg-sky-300/50 blur-[0.5px] pointer-events-none"
        />
      </motion.span>
    </span>
  );
};
