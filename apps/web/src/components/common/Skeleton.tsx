import React from 'react';

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '' }) => {
  return (
    <div
      className={`animate-pulse bg-sky-100/60 dark:bg-sky-900/40 rounded-btn ${className}`}
    />
  );
};
