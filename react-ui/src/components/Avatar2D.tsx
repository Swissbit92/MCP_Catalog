import React from 'react';
import { cn } from '../utils/cn'; // We'll create this utility

interface Avatar2DProps {
  src?: string;
  alt: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
  fallback?: string;
  rarity?: string;
}

export const Avatar2D: React.FC<Avatar2DProps> = ({
  src,
  alt,
  size = 'md',
  className,
  fallback,
  rarity,
}) => {
  const sizeClasses = {
    xs: 'w-6 h-6',
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
  };

  const getRarityStyles = (rarity?: string) => {
    switch (rarity) {
      case 'legendary':
        return 'ring-2 ring-yellow-400 shadow-lg shadow-yellow-500/30';
      case 'epic':
        return 'ring-2 ring-purple-400 shadow-lg shadow-purple-500/30';
      case 'rare':
        return 'ring-2 ring-blue-400 shadow-lg shadow-blue-500/30';
      case 'common':
      default:
        return 'ring-1 ring-gray-400 shadow-md shadow-gray-400/20';
    }
  };

  const getFallbackInitial = (name: string) => {
    return name.charAt(0).toUpperCase();
  };

  return (
    <div
      className={cn(
        'rounded-full overflow-hidden bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center text-white font-medium transition-all duration-300 hover:scale-105',
        sizeClasses[size],
        rarity ? getRarityStyles(rarity) : '',
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
                fallbackEl.className = `fallback-text flex items-center justify-center w-full h-full text-white font-medium transition-all duration-300 ${
                  rarity === 'legendary' ? 'bg-gradient-to-br from-yellow-400 to-amber-500' :
                  rarity === 'epic' ? 'bg-gradient-to-br from-purple-400 to-violet-500' :
                  rarity === 'rare' ? 'bg-gradient-to-br from-blue-400 to-cyan-500' :
                  'bg-gradient-to-br from-gray-400 to-slate-500'
                }`;
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