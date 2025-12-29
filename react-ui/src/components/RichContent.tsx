import React, { useState } from 'react';
import { Copy, Check, ExternalLink } from 'lucide-react';

interface RichContentProps {
  content: string;
  className?: string;
}

// Helper function to parse and render markdown formatting
const parseMarkdown = (text: string): React.ReactNode[] => {
  const parts: React.ReactNode[] = [];
  let key = 0;

  // Split by lines to handle bullet points
  const lines = text.split('\n');
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // Check if line is a bullet point (starts with * or •)
    const bulletMatch = line.match(/^(\s*)[*•]\s+(.+)$/);
    
    if (bulletMatch) {
      const indent = bulletMatch[1];
      const content = bulletMatch[2];
      parts.push(
        <div key={key++} className={`flex items-start gap-2 ${indent ? 'ml-4' : ''}`}>
          <span className="text-gray-500 select-none">•</span>
          <span>{parseInlineMarkdown(content, key)}</span>
        </div>
      );
    } else {
      // Regular line - parse inline markdown
      const parsed = parseInlineMarkdown(line, key);
      parts.push(
        <React.Fragment key={key++}>
          {parsed}
          {i < lines.length - 1 && <br />}
        </React.Fragment>
      );
    }
    
    key += 100; // Increment key to avoid conflicts
  }
  
  return parts;
};

// Helper to parse inline markdown (bold, italic, links, URLs)
const parseInlineMarkdown = (text: string, startKey: number): React.ReactNode[] => {
  let key = startKey;

  // Process <br> tags first (literal HTML breaks from LLM)
  const brParts: React.ReactNode[] = [];
  text.split(/(<br\s*\/?>)/i).forEach((segment, i) => {
    if (i % 2 === 0) {
      // Not a br match - will process for bold/italic later
      brParts.push(segment);
    } else {
      // br match - replace with actual React <br />
      brParts.push(<br key={`br-${key++}`} />);
    }
  });

  // Process bold (**text**) - greedy to handle multiple on same line
  const boldParts: React.ReactNode[] = [];
  brParts.forEach((part) => {
    if (typeof part === 'string') {
      part.split(/(\*\*[^*]+\*\*)/).forEach((segment, i) => {
        if (i % 2 === 0) {
          // Not a bold match - will process for italic/links later
          boldParts.push(segment);
        } else {
          // Bold match - strip ** and wrap in <strong>
          const content = segment.slice(2, -2);
          boldParts.push(<strong key={`bold-${key++}`} className="font-bold">{content}</strong>);
        }
      });
    } else {
      // Already a React node (br), keep as-is
      boldParts.push(part);
    }
  });
  
  // Process italic (*text*) - process each part from bold
  const italicParts: React.ReactNode[] = [];
  boldParts.forEach((part) => {
    if (typeof part === 'string') {
      part.split(/(\*[^*]+\*)/).forEach((segment, i) => {
        if (i % 2 === 0) {
          // Not an italic match - will process for links later
          italicParts.push(segment);
        } else {
          // Italic match - strip * and wrap in <em>
          const content = segment.slice(1, -1);
          italicParts.push(<em key={`italic-${key++}`} className="italic">{content}</em>);
        }
      });
    } else {
      // Already a React node (bold), keep as-is
      italicParts.push(part);
    }
  });
  
  // Process markdown links ([text](url))
  const linkParts: React.ReactNode[] = [];
  italicParts.forEach((part) => {
    if (typeof part === 'string') {
      const segments = part.split(/(\[([^\]]+)\]\(([^)]+)\))/);
      for (let i = 0; i < segments.length; i++) {
        if (i % 4 === 0 && segments[i]) {
          // Not a link match - will process for URLs later
          linkParts.push(segments[i]);
        } else if (i % 4 === 2) {
          // Link text
          const linkText = segments[i];
          const linkUrl = segments[i + 1];
          linkParts.push(
            <a
              key={`link-${key++}`}
              href={linkUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1"
            >
              {linkText}
              <ExternalLink size={12} className="inline" />
            </a>
          );
        }
      }
    } else {
      // Already a React node, keep as-is
      linkParts.push(part);
    }
  });
  
  // Process plain URLs
  const finalParts: React.ReactNode[] = [];
  linkParts.forEach((part) => {
    if (typeof part === 'string') {
      const segments = part.split(/(https?:\/\/[^\s<>"']+)/);
      segments.forEach((segment, i) => {
        if (i % 2 === 0) {
          // Not a URL, add as text
          if (segment) finalParts.push(segment);
        } else {
          // URL match
          finalParts.push(
            <a
              key={`url-${key++}`}
              href={segment}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1 break-all"
            >
              {segment}
              <ExternalLink size={12} className="inline" />
            </a>
          );
        }
      });
    } else {
      // Already a React node, keep as-is
      finalParts.push(part);
    }
  });
  
  return finalParts.length > 0 ? finalParts : [text];
};

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

  // Regular text content with markdown formatting
  return (
    <div className={`text-sm leading-relaxed ${className}`}>
      {parseMarkdown(content)}
    </div>
  );
};