'use client';
import { useSessionStore } from '@/lib/store';
import { TOPICS } from '@/lib/topics';

export default function ProgressView() {
  const mastery    = useSessionStore((s) => s.mastery);
  const weakTopics = useSessionStore((s) => s.weakTopics);
  const misconceptions = useSessionStore((s) => s.misconceptions);
  const phase      = useSessionStore((s) => s.phase);
  const diagComplete = useSessionStore((s) => s.diagnosticComplete);

  const masteryTopics = TOPICS.map((t) => ({
    ...t,
    score: mastery[t.key] ?? 0,
  }));

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
            const isWeak = weakTopics.includes(t.key);
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
