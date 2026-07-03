import React from 'react';
import { Search, Brain, Zap, Wallet } from 'lucide-react';
import { ResponseMetadata } from '../services/api';
import { getSourceNarrative, formatToolNarrative } from './nephilim/mcpNarratives';

interface SourceIndicatorProps {
  metadata?: ResponseMetadata;
  className?: string;
}

// Hex colors matching ToolIndicator and mcpNarratives
const SOURCE_COLORS: Record<string, string> = {
  llm: '#b07cc6',
  brave_mcp: '#2ecc71',
  wallet_mcp: '#FFD700',
  wallet_proposal: '#FFD700',
  wallet_flow: '#FFD700',
};

const ICON_CONFIG: Record<string, typeof Brain> = {
  llm: Brain,
  brave_mcp: Search,
  wallet_mcp: Wallet,
  wallet_proposal: Wallet,
  wallet_flow: Wallet,
};

/**
 * SourceIndicator displays visual badges showing the data source for a message.
 *
 * Supports source types: llm, brave_mcp, wallet_mcp, wallet_proposal, wallet_flow.
 *
 * Also displays cache status, tools used, and data timestamp.
 */
export const SourceIndicator: React.FC<SourceIndicatorProps> = ({
  metadata,
  className = ''
}) => {
  if (!metadata) {
    return null;
  }

  const { source_type, tools_used = [], cache_status, data_timestamp } = metadata;
  const narrative = getSourceNarrative(source_type);
  const IconComponent = ICON_CONFIG[source_type] || Brain;
  const hexColor = SOURCE_COLORS[source_type] || SOURCE_COLORS.llm;

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
  const baseClasses = `inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border mt-2 ${className}`;

  return (
    <div
      className={baseClasses}
      style={{
        backgroundColor: `${hexColor}15`,
        color: hexColor,
        borderColor: `${hexColor}30`,
      }}
    >
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
          • {tools_used.map(tool => formatToolNarrative(tool)).join(', ')}
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
