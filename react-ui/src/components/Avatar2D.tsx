import React from 'react';
import { cn } from '../utils/cn'; // We'll create this utility

interface Avatar2DProps {
  src?: string;
  alt: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
  fallback?: string;
}

export const Avatar2D: React.FC<Avatar2DProps> = ({
  src,
  alt,
  size = 'md',
  className,
  fallback,
}) => {
  const sizeClasses = {
    xs: 'w-6 h-6',
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
  };

  const getFallbackInitial = (name: string) => {
    return name.charAt(0).toUpperCase();
  };

  return (
    <div
      className={cn(
        'rounded-full overflow-hidden bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center text-white font-medium',
        sizeClasses[size],
        className
      )}
    >
      {src ? (
        <img
          src={src}
          alt={alt}
          className="w-full h-full object-cover"
          onError={(e) => {
            // Fallback to initial if image fails to load
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            const parent = target.parentElement;
            if (parent && !parent.querySelector('.fallback-text')) {
              const fallbackEl = document.createElement('div');
              fallbackEl.className = 'fallback-text flex items-center justify-center w-full h-full bg-gradient-to-br from-blue-400 to-purple-500 text-white font-medium';
              fallbackEl.textContent = getFallbackInitial(alt);
              parent.appendChild(fallbackEl);
            }
          }}
        />
      ) : (
        <span className="text-xs font-medium">
          {fallback || getFallbackInitial(alt)}
        </span>
      )}
    </div>
  );
};