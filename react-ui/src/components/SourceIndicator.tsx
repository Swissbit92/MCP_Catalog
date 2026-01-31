import React from 'react';
import { Database, Search, Brain, Link, Zap } from 'lucide-react';
import { ResponseMetadata } from '../services/api';
import {
  getSourceNarrative,
  formatToolNarrative,
  isNephilimPersona,
  NEPHILIM_SOURCE_NARRATIVES,
} from './nephilim/mcpNarratives';

interface SourceIndicatorProps {
  metadata?: ResponseMetadata;
  personaKey?: string;
  className?: string;
}

/**
 * SourceIndicator displays visual badges showing the data source for a message.
 *
 * Supports four source types:
 * - llm: Pure LLM response (purple)
 * - brave_mcp: Web search via Brave MCP (blue) / "Cipher's Archives" in NEPHILIM mode
 * - mongodb_mcp: Trading data via MongoDB MCP (green) / "Aurora's Crystal Grid" in NEPHILIM mode
 * - multi_mcp: Multiple sources combined (orange) / "The Convergence" in NEPHILIM mode
 *
 * Also displays:
 * - Cache status (lightning bolt icon for cached data)
 * - Tools used (e.g., "bitcoin_current_price" or "Price Vision" in NEPHILIM mode)
 * - Data timestamp (e.g., "Updated 23s ago")
 */
export const SourceIndicator: React.FC<SourceIndicatorProps> = ({
  metadata,
  personaKey,
  className = ''
}) => {
  if (!metadata) {
    return null;
  }

  const { source_type, tools_used = [], cache_status, data_timestamp } = metadata;
  const isNephilimMode = isNephilimPersona(personaKey);

  // Get narrative or standard config based on mode
  const narrative = getSourceNarrative(source_type, isNephilimMode);

  // Standard icon configuration
  const iconConfig: Record<string, typeof Brain> = {
    llm: Brain,
    brave_mcp: Search,
    mongodb_mcp: Database,
    multi_mcp: Link,
  };
  const IconComponent = iconConfig[source_type] || Brain;

  // Color configuration - use NEPHILIM colors in that mode
  const getColorClasses = () => {
    if (isNephilimMode) {
      const nephilimNarrative = NEPHILIM_SOURCE_NARRATIVES[source_type];
      if (nephilimNarrative) {
        // Use inline styles for NEPHILIM persona colors
        return {
          useInlineStyle: true,
          color: nephilimNarrative.color,
        };
      }
    }

    // Standard color classes
    const standardColors: Record<string, string> = {
      llm: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
      brave_mcp: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      mongodb_mcp: 'bg-green-500/10 text-green-400 border-green-500/20',
      multi_mcp: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    };
    return {
      useInlineStyle: false,
      className: standardColors[source_type] || standardColors.llm,
    };
  };

  const colorConfig = getColorClasses();

  // Format data timestamp as relative time
  const formatRelativeTime = (timestamp: string | null | undefined): string => {
    if (!timestamp) return '';

    try {
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) return '';

      const now = new Date();
      const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

      if (diffSeconds < 0) return '';
      if (diffSeconds < 60) return `${diffSeconds}s ago`;
      if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
      if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
      return `${Math.floor(diffSeconds / 86400)}d ago`;
    } catch {
      return '';
    }
  };

  const relativeTime = formatRelativeTime(data_timestamp);

  // Build the component
  const baseClasses = `inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border mt-2 ${className}`;

  if (colorConfig.useInlineStyle && 'color' in colorConfig) {
    // NEPHILIM mode with custom colors
    return (
      <div
        className={baseClasses}
        style={{
          backgroundColor: `${colorConfig.color}15`,
          color: colorConfig.color,
          borderColor: `${colorConfig.color}30`,
        }}
      >
        {/* NEPHILIM emoji icon */}
        <span className="text-sm">{narrative.icon}</span>
        <span className="font-semibold">{narrative.label}</span>

        {/* Patron indicator for NEPHILIM */}
        {isNephilimMode && source_type !== 'llm' && (
          <span className="opacity-70 text-[10px]">
            • via {NEPHILIM_SOURCE_NARRATIVES[source_type]?.patron}
          </span>
        )}

        {/* Cache status indicator */}
        {cache_status === 'hit' && (
          <span className="text-yellow-400 flex items-center gap-0.5" title="Retrieved from cache">
            <Zap size={12} className="fill-yellow-400" />
          </span>
        )}

        {/* Tools used with NEPHILIM formatting */}
        {tools_used.length > 0 && (
          <span className="opacity-70 text-[10px]">
            • {tools_used.map(tool => formatToolNarrative(tool, isNephilimMode)).join(', ')}
          </span>
        )}

        {/* Data timestamp */}
        {relativeTime && (
          <span className="opacity-70 text-[10px]">
            • {relativeTime}
          </span>
        )}
      </div>
    );
  }

  // Standard mode
  return (
    <div className={`${baseClasses} ${'className' in colorConfig ? colorConfig.className : ''}`}>
      <IconComponent size={14} className="flex-shrink-0" />
      <span className="font-semibold">{narrative.label}</span>

      {/* Cache status indicator */}
      {cache_status === 'hit' && (
        <span className="text-yellow-400 flex items-center gap-0.5" title="Retrieved from cache">
          <Zap size={12} className="fill-yellow-400" />
        </span>
      )}

      {/* Tools used */}
      {tools_used.length > 0 && (
        <span className="opacity-70 text-[10px]">
          • {tools_used.map(tool => formatToolNarrative(tool, false)).join(', ')}
        </span>
      )}

      {/* Data timestamp */}
      {relativeTime && (
        <span className="opacity-70 text-[10px]">
          • Updated {relativeTime}
        </span>
      )}
    </div>
  );
};
