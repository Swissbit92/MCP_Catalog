import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface RichContentProps {
  content: string;
  className?: string;
}

export const RichContent: React.FC<RichContentProps> = ({ content, className = '' }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  // Check if content is JSON
  const isJson = (() => {
    try {
      JSON.parse(content);
      return true;
    } catch {
      return false;
    }
  })();

  // Check if content is a code block (starts and ends with ```)
  const isCodeBlock = content.trim().startsWith('```') && content.trim().endsWith('```');

  if (isJson) {
    const formattedJson = JSON.stringify(JSON.parse(content), null, 2);
    const isLongJson = formattedJson.length > 500;

    return (
      <div className={`relative ${className}`}>
        <div className="flex items-center justify-between mb-1">
          <div className="text-xs text-gray-400 font-mono">JSON Response</div>
          <button
            onClick={() => copyToClipboard(formattedJson)}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-300 transition-colors p-2 md:p-1 rounded hover:bg-gray-800 touch-manipulation min-h-[32px]"
            title="Copy JSON"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
            <span className="hidden sm:inline">{copied ? 'Copied!' : 'Copy'}</span>
          </button>
        </div>
        <div className={`relative ${isLongJson ? 'max-h-64 overflow-hidden' : ''}`}>
          <pre className="bg-gray-900 text-green-400 p-3 rounded-lg text-sm font-mono whitespace-pre-wrap overflow-x-auto">
            {formattedJson}
          </pre>
          {isLongJson && !isExpanded && (
            <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-gray-900 to-transparent flex items-end justify-center pb-2">
              <button
                onClick={() => setIsExpanded(true)}
                className="text-xs text-blue-400 hover:text-blue-300 bg-gray-800 px-2 py-1 rounded"
              >
                Show more
              </button>
            </div>
          )}
        </div>
        {isLongJson && isExpanded && (
          <button
            onClick={() => setIsExpanded(false)}
            className="text-xs text-blue-400 hover:text-blue-300 mt-2"
          >
            Show less
          </button>
        )}
      </div>
    );
  }

  if (isCodeBlock) {
    // Extract language and code from code block
    const lines = content.trim().split('\n');
    const firstLine = lines[0];
    const language = firstLine.replace(/^```/, '') || 'text';
    const code = lines.slice(1, -1).join('\n');

    return (
      <div className={`relative ${className}`}>
        <div className="flex items-center justify-between mb-1">
          <div className="text-xs text-gray-400 font-mono">Code ({language})</div>
          <button
            onClick={() => copyToClipboard(code)}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-300 transition-colors p-2 md:p-1 rounded hover:bg-gray-800 touch-manipulation min-h-[32px]"
            title="Copy code"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
            <span className="hidden sm:inline">{copied ? 'Copied!' : 'Copy'}</span>
          </button>
        </div>
        <pre className="bg-gray-900 text-green-400 p-3 rounded-lg text-sm font-mono whitespace-pre-wrap overflow-x-auto">
          {code}
        </pre>
      </div>
    );
  }

  // Regular text content
  return (
    <div className={`text-sm leading-relaxed whitespace-pre-wrap ${className}`}>
      {content}
    </div>
  );
};