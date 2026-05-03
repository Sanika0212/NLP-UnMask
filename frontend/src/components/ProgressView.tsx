'use client';
import { useMemo } from 'react';
import { useSessionStore } from '@/lib/store';
import { TOPICS, getTopicMastery, isWeakTopic } from '@/lib/topics';

export default function ProgressView() {
  const mastery    = useSessionStore((s) => s.mastery);
  const weakTopics = useSessionStore((s) => s.weakTopics);
  const misconceptions = useSessionStore((s) => s.misconceptions);
  const phase      = useSessionStore((s) => s.phase);
  const diagComplete = useSessionStore((s) => s.diagnosticComplete);
  const youtubeResources = useSessionStore((s) => s.youtubeResources);

  const masteryTopics = useMemo(() => TOPICS.map((t) => ({
    ...t,
    score: getTopicMastery(mastery, t.key),
  })), [mastery]);

  const phaseColors: Record<string, string> = {
    rapport: 'var(--ink-3)',
    tutoring: 'var(--accent)',
    assessment: 'var(--good)',
    wrapup: 'var(--good)',
  };

  return (
    <div style={{ padding: '18px', overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Session status */}
      <div className="panel">
        <div className="panel-head">
          <h4>Session Status</h4>
        </div>
        <div className="panel-body" style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '120px' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>Phase</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: phaseColors[phase] ?? 'var(--ink)', textTransform: 'capitalize' }}>{phase}</div>
          </div>
          <div style={{ flex: 1, minWidth: '120px' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>Diagnostic</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: diagComplete ? 'var(--good)' : 'var(--accent)' }}>
              {diagComplete ? 'Complete' : 'In Progress'}
            </div>
          </div>
          <div style={{ flex: 1, minWidth: '120px' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>Weak Areas</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: weakTopics.length ? 'var(--warn)' : 'var(--good)' }}>
              {weakTopics.length || 'None yet'}
            </div>
          </div>
        </div>
      </div>

      {/* Mastery bars */}
      <div className="panel">
        <div className="panel-head">
          <h4>Topic Mastery</h4>
          <span className="pmeta">0–100%</span>
        </div>
        <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {masteryTopics.map((t) => {
            const pct = Math.round(t.score * 100);
            const isWeak = isWeakTopic(weakTopics, t.key);
            const barColor = pct >= 75 ? 'var(--good)' : pct >= 40 ? 'var(--accent)' : 'var(--warn)';
            return (
              <div key={t.key}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--ink)', fontWeight: isWeak ? 600 : 400 }}>
                    {t.label}
                    {isWeak && <span style={{ marginLeft: '6px', fontSize: '11px', color: 'var(--warn)', background: 'var(--warn-soft)', padding: '1px 6px', borderRadius: '999px' }}>weak</span>}
                  </span>
                  <span style={{ fontSize: '12px', color: 'var(--ink-3)', fontVariantNumeric: 'tabular-nums' }}>{pct}%</span>
                </div>
                <div style={{ height: '6px', background: 'var(--paper-2)', borderRadius: '999px', overflow: 'hidden', border: '1px solid var(--rule)' }}>
                  <div style={{ height: '100%', width: `${pct}%`, background: barColor, borderRadius: '999px', transition: 'width 600ms ease' }} />
                </div>
              </div>
            );
          })}
          {masteryTopics.every((t) => t.score === 0) && (
            <p style={{ fontSize: '13px', color: 'var(--ink-3)', margin: 0 }}>No data yet — complete some tutoring turns to see mastery scores.</p>
          )}
        </div>
      </div>

      {/* YouTube recommendations — shown after wrapup when resources are ready */}
      {youtubeResources.length > 0 && (
        <div className="panel">
          <div className="panel-head">
            <h4>Recommended Videos</h4>
            <span className="pmeta">for weak topics</span>
          </div>
          <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {youtubeResources.map((yt, i) => {
              const url = `https://www.youtube.com/results?search_query=${encodeURIComponent(yt.search_query)}`;
              return (
                <a
                  key={i}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex', gap: '12px', alignItems: 'flex-start',
                    padding: '10px 12px', borderRadius: 'var(--r)',
                    background: 'var(--paper-3)', border: '1px solid var(--rule)',
                    textDecoration: 'none', color: 'inherit',
                    transition: 'border-color 120ms',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--rule)')}
                >
                  <svg viewBox="0 0 24 24" width="18" height="18" style={{ flexShrink: 0, marginTop: '3px', color: '#FF0000' }} fill="currentColor">
                    <path d="M21.8 8s-.2-1.4-.8-2c-.8-.8-1.6-.8-2-.9C16.8 5 12 5 12 5s-4.8 0-7 .1c-.4.1-1.2.1-2 .9-.6.6-.8 2-.8 2S2 9.6 2 11.2v1.5c0 1.6.2 3.2.2 3.2s.2 1.4.8 2c.8.8 1.8.8 2.3.8C6.8 19 12 19 12 19s4.8 0 7-.1c.4-.1 1.2-.1 2-.9.6-.6.8-2 .8-2s.2-1.6.2-3.2v-1.5C22 9.6 21.8 8 21.8 8zM9.7 14.5V9.5l5.3 2.5-5.3 2.5z" />
                  </svg>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 500, fontSize: '13px', color: 'var(--ink)', marginBottom: '2px' }}>
                      {yt.title}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--ink-3)', marginBottom: '4px' }}>
                      {yt.creator}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.4 }}>
                      {yt.description}
                    </div>
                  </div>
                </a>
              );
            })}
          </div>
        </div>
      )}

      {/* Misconceptions log */}
      {misconceptions.length > 0 && (
        <div className="panel">
          <div className="panel-head">
            <h4>Misconception Log</h4>
            <span className="pmeta">{misconceptions.length} flagged</span>
          </div>
          <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {misconceptions.map((m, i) => (
              <div key={i} style={{ padding: '10px 12px', background: 'var(--warn-soft)', border: '1px solid var(--warn)', borderRadius: 'var(--r)', fontSize: '13px' }}>
                <div style={{ fontWeight: 600, color: 'var(--ink)', marginBottom: '2px' }}>{m.topic}</div>
                <div style={{ color: 'var(--ink-2)', lineHeight: 1.5 }}>{m.note}</div>
                <div style={{ fontSize: '11px', color: 'var(--ink-3)', marginTop: '4px' }}>Turn {m.turn}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
