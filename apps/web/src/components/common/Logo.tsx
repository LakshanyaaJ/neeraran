import React from 'react';
import { Link } from 'react-router-dom';

interface LogoProps {
  className?: string;
  showTagline?: boolean;
  size?: 'sm' | 'md' | 'lg';
  asLink?: boolean;
}

export const Logo: React.FC<LogoProps> = ({
  className = '',
  showTagline = false,
  size = 'md',
  asLink = true,
}) => {
  const sizeClasses = {
    sm: {
      tamil: 'text-xl',
      latin: 'text-lg',
      waveW: 'w-5',
      waveH: 'h-1.5',
      tagline: 'text-[10px]',
    },
    md: {
      tamil: 'text-2xl',
      latin: 'text-2xl',
      waveW: 'w-7',
      waveH: 'h-2',
      tagline: 'text-xs',
    },
    lg: {
      tamil: 'text-4xl',
      latin: 'text-4xl',
      waveW: 'w-10',
      waveH: 'h-2.5',
      tagline: 'text-sm',
    },
  }[size];

  const content = (
    <div className={`inline-flex flex-col select-none ${className}`}>
      <div className="flex items-baseline gap-0.5 relative">
        {/* Tamil 'நீர்' in Anek Tamil */}
        <span
          className={`font-tamil font-bold text-sky-700 dark:text-sky-300 leading-none tracking-tight ${sizeClasses.tamil}`}
          style={{ transform: 'translateY(-1px)' }}
        >
          நீர்
        </span>

        {/* Latin 'Aran' in Onest */}
        <span
          className={`font-sans font-bold text-ink-900 leading-none tracking-tight ${sizeClasses.latin}`}
        >
          Aran
        </span>

        {/* Small wave line under the join */}
        <div className="absolute -bottom-1.5 left-[1.1rem]">
          <svg
            className={`${sizeClasses.waveW} ${sizeClasses.waveH} text-sky-500`}
            viewBox="0 0 28 6"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M1 3C3.5 1 5.5 1 8 3C10.5 5 12.5 5 15 3C17.5 1 19.5 1 22 3C24.5 5 26.5 5 27 4"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>

      {showTagline && (
        <span className={`text-ink-600 font-normal mt-1.5 ${sizeClasses.tagline}`}>
          Every drop accounted for.
        </span>
      )}
    </div>
  );

  if (asLink) {
    return (
      <Link to="/" className="inline-flex items-center hover:opacity-95 transition-opacity">
        {content}
      </Link>
    );
  }

  return content;
};
