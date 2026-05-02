'use client';
import { VisualHint } from '@/lib/types';

interface Props {
  hint: VisualHint;
}

export default function DiagramCard({ hint }: Props) {
  const url = hint.imageUrl;
  const isHtml = url?.endsWith('.html');
  const isExternal = url?.startsWith('http');
  const badgeLabel = isHtml ? 'Animated' : isExternal ? 'Web' : url ? 'Image' : null;

  return (
    <div style={{ marginTop: '14px' }}>
      <div style={{
        border: '1px solid var(--rule)',
        borderRadius: 'var(--r)',
        overflow: 'hidden',
        background: 'var(--paper-2)',
      }}>
        {url && isHtml ? (
          <iframe
            src={url}
            title={hint.concept || 'Diagram'}
            style={{
              width: '100%',
              height: '420px',
              border: 'none',
              display: 'block',
            }}
            loading="lazy"
          />
        ) : url ? (
          <img
            src={url}
            alt={hint.concept || 'Diagram'}
            style={{
              width: '100%',
              height: 'auto',
              display: 'block',
              maxHeight: '280px',
              objectFit: 'contain',
            }}
          />
        ) : (
          <div style={{
            height: '220px',
            background: 'repeating-linear-gradient(45deg, var(--paper-3), var(--paper-3) 8px, var(--paper-2) 8px, var(--paper-2) 16px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--ink-3)',
            fontFamily: 'ui-monospace, monospace',
            fontSize: '11px',
          }}>
            [diagram placeholder]
          </div>
        )}

        <div style={{
          padding: '10px 14px',
          fontSize: '12px',
          color: 'var(--ink-2)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderTop: '1px solid var(--rule)',
        }}>
          <span>{hint.caption || hint.concept || 'Diagram'}</span>
          {badgeLabel && (
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '3px 8px',
              borderRadius: '999px',
              background: 'var(--accent-soft)',
              color: 'var(--accent-ink)',
              fontSize: '11px',
              fontFamily: 'ui-monospace, monospace',
            }}>
              <span style={{
                width: '5px',
                height: '5px',
                borderRadius: '50%',
                background: 'var(--accent)',
              }} />
              {badgeLabel}
            </span>
          )}
        </div>
      </div>

      {hint.hintText && (
        <blockquote style={{
          margin: '12px 0 0 0',
          padding: '12px 14px',
          borderLeft: '3px solid var(--accent)',
          background: 'var(--accent-soft)',
          color: 'var(--accent-ink)',
          fontSize: '13px',
          lineHeight: '1.55',
          fontStyle: 'italic',
        }}>
          {hint.hintText}
        </blockquote>
      )}
    </div>
  );
}
