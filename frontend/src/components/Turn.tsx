'use client';
import React from 'react';
import { Message } from '@/lib/types';
import Avatar from './Avatar';
import DiagramCard from './DiagramCard';
import { useSessionStore } from '@/lib/store';

interface Props {
  message: Message;
  elapsed?: number;
}

function fmt(date: Date): string {
  return `${String(date.getHours()).padStart(2,'0')}:${String(date.getMinutes()).padStart(2,'0')}`;
}

function renderMarkdown(text: string): React.ReactNode[] {
  // Split by double newlines to create paragraphs
  const paragraphs = text.split('\n\n');

  return paragraphs.flatMap((para, paraIdx) => {
    const lines = para.split('\n');
    const elements: React.ReactNode[] = [];
    let listItems: React.ReactNode[] = [];

    lines.forEach((line, lineIdx) => {
      // Check for heading markers at line start
      if (line.startsWith('## ')) {
        // Flush any pending list items first
        if (listItems.length > 0) {
          elements.push(
            <ul key={`list-${paraIdx}-${lineIdx}`} style={{ margin: '6px 0', paddingLeft: '20px' }}>
              {listItems}
            </ul>
          );
          listItems = [];
        }
        const heading = line.slice(3).trim();
        const processedHeading = processInlineMarkdown(heading);
        elements.push(
          <h3 key={`h3-${paraIdx}-${lineIdx}`} style={{ margin: '8px 0 4px 0', fontSize: '1.1em', fontWeight: 600 }}>
            {processedHeading}
          </h3>
        );
        return;
      }

      if (line.startsWith('### ')) {
        // Flush any pending list items first
        if (listItems.length > 0) {
          elements.push(
            <ul key={`list-${paraIdx}-${lineIdx}`} style={{ margin: '6px 0', paddingLeft: '20px' }}>
              {listItems}
            </ul>
          );
          listItems = [];
        }
        const heading = line.slice(4).trim();
        const processedHeading = processInlineMarkdown(heading);
        elements.push(
          <h4 key={`h4-${paraIdx}-${lineIdx}`} style={{ margin: '6px 0 2px 0', fontSize: '1em', fontWeight: 600 }}>
            {processedHeading}
          </h4>
        );
        return;
      }

      // Check for list items (lines starting with '- ')
      if (line.startsWith('- ')) {
        const itemText = line.slice(2).trim();
        const processedItem = processInlineMarkdown(itemText);
        listItems.push(
          <li key={`li-${paraIdx}-${lineIdx}`}>{processedItem}</li>
        );
        return;
      }

      // Flush any pending list items if we hit a non-list line
      if (listItems.length > 0) {
        elements.push(
          <ul key={`list-${paraIdx}-${lineIdx}`} style={{ margin: '6px 0', paddingLeft: '20px' }}>
            {listItems}
          </ul>
        );
        listItems = [];
      }

      // Process regular lines with inline markdown
      if (line.trim()) {
        const processedLine = processInlineMarkdown(line);
        elements.push(
          <p key={`p-${paraIdx}-${lineIdx}`} style={{ margin: '0 0 6px 0' }}>
            {processedLine}
          </p>
        );
      } else {
        // Empty line
        elements.push(<p key={`p-${paraIdx}-${lineIdx}`} style={{ margin: '0' }}>&nbsp;</p>);
      }
    });

    // Flush any remaining list items at end of paragraph
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${paraIdx}-end`} style={{ margin: '6px 0', paddingLeft: '20px' }}>
          {listItems}
        </ul>
      );
    }

    return elements;
  });
}

function processInlineMarkdown(text: string): React.ReactNode {
  // Process inline markdown: **bold**, *italic*, _italic_, and question wrapping
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Match **bold** pattern
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    if (boldMatch) {
      const idx = remaining.indexOf(boldMatch[0]);
      if (idx > 0) {
        parts.push(remaining.slice(0, idx));
      }
      parts.push(<strong key={`b-${key++}`}>{processInlineMarkdown(boldMatch[1])}</strong>);
      remaining = remaining.slice(idx + boldMatch[0].length);
      continue;
    }

    // Match *italic* pattern (not inside words)
    const italicMatch = remaining.match(/(?:^|\s)\*([^\s*][^*]*[^\s*]|[^\s*])\*(?:\s|$)/);
    if (italicMatch && italicMatch.index !== undefined) {
      const idx = italicMatch.index;
      const before = remaining.slice(0, idx);
      const italic = italicMatch[1];
      const after = remaining.slice(idx + italicMatch[0].length);
      parts.push(before);
      parts.push(<em key={`i-${key++}`}>{italic}</em>);
      remaining = after;
      continue;
    }

    // Match _italic_ pattern
    const underlineItalicMatch = remaining.match(/_([^\s_][^_]*[^\s_]|[^\s_])_/);
    if (underlineItalicMatch && underlineItalicMatch.index !== undefined) {
      const idx = underlineItalicMatch.index;
      if (idx > 0) {
        parts.push(remaining.slice(0, idx));
      }
      parts.push(<em key={`i-${key++}`}>{underlineItalicMatch[1]}</em>);
      remaining = remaining.slice(idx + underlineItalicMatch[0].length);
      continue;
    }

    // No more markdown patterns, add the rest
    parts.push(remaining);
    break;
  }

  // If text ends with ? or starts with question pattern, wrap in question styling
  const fullText = text.trim();
  if (fullText.endsWith('?') || /^(what|why|how|when|where|who|can|could|would|is|are|do|does)\s/i.test(fullText)) {
    return (
      <span className="q">
        {parts}
      </span>
    );
  }

  return parts;
}

export default function Turn({ message, elapsed = 0 }: Props) {
  const studentName = useSessionStore((s) => s.studentName);
  const initials = studentName.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();

  if (message.role === 'user') {
    return (
      <div className="turn user">
        <div className="body">
          <div className="meta">{fmt(message.timestamp)}</div>
          <div className="bubble">{message.content}</div>
        </div>
        <div className="av user-av">{initials}</div>
      </div>
    );
  }

  // Supervisor step — small faded badge, no avatar
  if (message.supervisorStep && !message.content) {
    const { agent, reasoning } = message.supervisorStep;
    const icon: Record<string,string> = { diagnostic:'🩺', tutor:'📖', assessment:'🧪', wrapup:'📋' };
    return (
      <div style={{ display:'flex', alignItems:'center', gap:8, padding:'2px 0' }}>
        <div className="step-badge">
          <span>{icon[agent] ?? '🤖'}</span>
          <span className="agent">{agent}</span>
          <span style={{ color:'var(--ink-3)', maxWidth:340, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
            {reasoning}
          </span>
        </div>
      </div>
    );
  }

  // Thinking placeholder
  if (message.isThinking) {
    return (
      <div className="turn">
        <div className="av"><Avatar state="thinking" size={32} /></div>
        <div className="body">
          <div className="meta">UnMask · Thinking…</div>
          <div className="status thinking">
            <span className="pip" />
            Processing your answer…
          </div>
        </div>
      </div>
    );
  }

  const authorLabel = message.author || 'UnMask';
  const avatarState = message.avatarState ?? 'speaking';

  return (
    <div className="turn">
      <div className="av"><Avatar state={avatarState} size={32} /></div>
      <div className="body">
        <div className="meta">{authorLabel} · {fmt(message.timestamp)}</div>
        <div className="bubble">
          {renderMarkdown(message.content)}
        </div>

        {message.visualHint && <DiagramCard hint={message.visualHint} />}

        {(message as any).quickReplies && (message as any).quickReplies.length > 0 && (
          <div className="quick-replies" style={{ display: 'flex', gap: '6px', marginTop: '12px', flexWrap: 'wrap' }}>
            {(message as any).quickReplies.map((reply: string, idx: number) => (
              <button
                key={idx}
                className="qr"
                onClick={() => useSessionStore.getState().sendMessage(reply)}
              >
                {reply}
              </button>
            ))}
          </div>
        )}

        <div className="tools">
          <button
            className="icon-btn"
            title="Copy"
            onClick={() => navigator.clipboard.writeText(message.content)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="9" y="9" width="11" height="11" rx="2"/>
              <path d="M5 15V5a2 2 0 0 1 2-2h10"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
