import React from 'react';
import { Database, Search, Brain, Link, Zap } from 'lucide-react';
import { ResponseMetadata } from '../services/api';

interface SourceIndicatorProps {
  metadata?: ResponseMetadata;
  className?: string;
}

/**
 * SourceIndicator displays visual badges showing the data source for a message.
 *
 * Supports four source types:
 * - llm: Pure LLM response (purple)
 * - brave_mcp: Web search via Brave MCP (blue)
 * - mongodb_mcp: Trading data via MongoDB MCP (green)
 * - multi_mcp: Multiple sources combined (orange)
 *
 * Also displays:
 * - Cache status (lightning bolt icon for cached data)
 * - Tools used (e.g., "bitcoin_current_price")
 * - Data timestamp (e.g., "Updated 23s ago")
 */
export const SourceIndicator: React.FC<SourceIndicatorProps> = ({ metadata, className = '' }) => {
  if (!metadata) {
    return null;
  }

  const { source_type, tools_used = [], cache_status, data_timestamp } = metadata;

  // Configuration for each source type
  const sourceConfig = {
    llm: {
      icon: Brain,
      label: 'Pure LLM Response',
      color: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    },
    brave_mcp: {
      icon: Search,
      label: 'Web Search (Brave MCP)',
      color: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    },
    mongodb_mcp: {
      icon: Database,
      label: 'Trading Data (MongoDB MCP)',
      color: 'bg-green-500/10 text-green-400 border-green-500/20',
    },
    multi_mcp: {
      icon: Link,
      label: 'Multi-Source Analysis',
      color: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    },
  };

  const config = sourceConfig[source_type];
  const IconComponent = config.icon;

  // Format data timestamp as relative time
  const formatRelativeTime = (timestamp: string | null | undefined): string => {
    if (!timestamp) return '';

    try {
      const date = new Date(timestamp);
      // Check if date is valid
      if (isNaN(date.getTime())) {
        return '';
      }

      const now = new Date();
      const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

      // Handle negative differences (future dates)
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

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border ${config.color} mt-2 ${className}`}>
      <IconComponent size={14} className="flex-shrink-0" />
      <span className="font-semibold">{config.label}</span>

      {/* Cache status indicator */}
      {cache_status === 'hit' && (
        <span className="text-yellow-400 flex items-center gap-0.5" title="Retrieved from cache">
          <Zap size={12} className="fill-yellow-400" />
        </span>
      )}

      {/* Tools used */}
      {tools_used.length > 0 && (
        <span className="opacity-70 text-[10px]">
          • {tools_used.map(tool => {
            // Format tool names nicely
            return tool.replace('bitcoin_', '').replace(/_/g, ' ');
          }).join(', ')}
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
