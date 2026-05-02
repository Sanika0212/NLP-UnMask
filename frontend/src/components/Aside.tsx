'use client';
import { useState } from 'react';
import { useSessionStore } from '@/lib/store';
import { TOPICS } from '@/lib/topics';
import Avatar from './Avatar';

type Tab = 'mastery' | 'context' | 'trace';

export default function Aside({ onCollapse }: { onCollapse?: () => void }) {
  const [activeTab, setActiveTab] = useState<Tab>('mastery');
  const mastery        = useSessionStore((s) => s.mastery);
  const misconceptions = useSessionStore((s) => s.misconceptions);
  const pcrMode        = useSessionStore((s) => s.pcrMode);
  const messages       = useSessionStore((s) => s.messages);

  // Supervisor steps for trace tab
  const supervisorSteps = messages.filter((m) => m.supervisorStep);

  // Aggregate dotted concept keys (e.g. brachial_plexus.origin) by topic prefix
  const topicMastery = (topicKey: string): number => {
    const entries = Object.entries(mastery).filter(([k]) => k.startsWith(topicKey + '.'));
    if (entries.length === 0) return mastery[topicKey] ?? 0;
    return entries.reduce((s, [, v]) => s + v, 0) / entries.length;
  };
  const nodeColor = (id: string) => {
    const m = topicMastery(id);
    if (m > 0.6) return 'oklch(0.6 0.09 195)';
    if (m > 0.3) return 'oklch(0.78 0.06 195)';
    return 'oklch(0.85 0.04 50)';
  };
  const nodeBorder = (id: string) => {
    const m = topicMastery(id);
    if (m > 0.3) return 'oklch(0.36 0.07 195)';
    return 'oklch(0.65 0.13 50)';
  };

  return (
    <div className="aside">
      {/* Collapsed-state icon rail — CSS shows this only when aside-collapsed */}
      <div className="aside-rail-icons">
        <button className="icon-btn active" title="Mastery" onClick={onCollapse}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <circle cx="12" cy="12" r="3" />
            <path d="M3 12h6M15 12h6M12 3v6M12 15v6" />
          </svg>
        </button>
        <button className="icon-btn" title="Context" onClick={onCollapse}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
        </button>
        <button className="icon-btn" title="Trace" onClick={onCollapse}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
        </button>
      </div>

      {/* Tabs bar */}
      <div className="aside-tabs">
        <button className={`aside-tab${activeTab==='mastery' ? ' active':''}`} onClick={() => setActiveTab('mastery')}>Mastery</button>
        <button className={`aside-tab${activeTab==='context' ? ' active':''}`} onClick={() => setActiveTab('context')}>Context</button>
        <button className={`aside-tab${activeTab==='trace'   ? ' active':''}`} onClick={() => setActiveTab('trace')}>Trace</button>
        <button className="icon-btn aside-collapse-btn" onClick={onCollapse} title="Collapse panel">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 6l6 6-6 6" />
            <path d="M5 6l6 6-6 6" />
          </svg>
        </button>
      </div>

      {/* PCR mode pill */}
      <div className={`pcr-mode ${pcrMode}`} id="pcr">
        <span className="lbl">PCR</span>
        <span className="val">
          <span className="pip" />
          {pcrMode}
        </span>
        <span style={{ marginLeft:'auto', fontSize:'11px', color:'var(--ink-3)', fontFamily:'ui-monospace,monospace' }}>
          μ = {Object.keys(mastery).length > 0
            ? (Object.values(mastery).reduce((a,b) => a+b, 0) / Object.values(mastery).length).toFixed(2)
            : '—'}
        </span>
      </div>

      {/* Body */}
      <div className="aside-body">
        {activeTab === 'mastery' && (
          <>
            {/* Concept DAG — matches reference exactly */}
            <div className="panel">
              <div className="panel-head">
                <h4>Concept graph</h4>
                <span className="pmeta">10 nodes</span>
              </div>
              <div className="dag">
                <svg viewBox="0 0 280 230" xmlns="http://www.w3.org/2000/svg">
                  {/* edges */}
                  <g stroke="oklch(0.86 0.012 80)" strokeWidth="1.4" fill="none">
                    {/* L0→L1 */}
                    <path d="M140 22 L75 72" /><path d="M140 22 L210 72" />
                    {/* L1→L2 */}
                    <path d="M75 72 L38 132" /><path d="M75 72 L108 132" />
                    <path d="M210 72 L178 132" /><path d="M210 72 L248 132" />
                    {/* L2→L3 */}
                    <path d="M38 132 L28 188" /><path d="M38 132 L88 188" />
                    <path d="M178 132 L168 188" /><path d="M248 132 L238 188" />
                  </g>
                  {/* nodes */}
                  <g fontFamily="Inter, sans-serif" fontSize="9" fill="oklch(0.42 0.015 265)">
                    {/* L0 */}
                    <circle cx="140" cy="22" r="12" fill={nodeColor('spinal_cord')} stroke={nodeBorder('spinal_cord')} strokeWidth="1.5" />
                    <text x="140" y="42" textAnchor="middle">spinal cord</text>
                    {/* L1 */}
                    <circle cx="75" cy="72" r="10" fill={nodeColor('brachial_plexus')} stroke={nodeBorder('brachial_plexus')} strokeWidth="1.5" />
                    <text x="75" y="90" textAnchor="middle">brachial</text>
                    <circle cx="210" cy="72" r="10" fill={nodeColor('rotator_cuff')} stroke={nodeBorder('rotator_cuff')} strokeWidth="1.5" />
                    <text x="210" y="90" textAnchor="middle">rotator cuff</text>
                    {/* L2 */}
                    <circle cx="38" cy="132" r="8" fill={nodeColor('peripheral_nerves')} stroke={nodeBorder('peripheral_nerves')} strokeWidth="1.5" />
                    <text x="38" y="148" textAnchor="middle">peripheral</text>
                    <circle cx="108" cy="132" r="8" fill={nodeColor('dermatomes')} stroke={nodeBorder('dermatomes')} strokeWidth="1.5" />
                    <text x="108" y="148" textAnchor="middle">dermatomes</text>
                    <circle cx="178" cy="132" r="8" fill={nodeColor('shoulder_joint')} stroke={nodeBorder('shoulder_joint')} strokeWidth="1.5" />
                    <text x="178" y="148" textAnchor="middle">shoulder</text>
                    <circle cx="248" cy="132" r="8" fill={nodeColor('upper_limb_muscles')} stroke={nodeBorder('upper_limb_muscles')} strokeWidth="1.5" />
                    <text x="248" y="148" textAnchor="middle">muscles</text>
                    {/* L3 */}
                    <circle cx="28" cy="188" r="6" fill={nodeColor('nerve_injuries')} stroke={nodeBorder('nerve_injuries')} strokeWidth="1.5" />
                    <text x="28" y="202" textAnchor="middle">nerve inj.</text>
                    <circle cx="88" cy="188" r="6" fill={nodeColor('elbow_joint')} stroke={nodeBorder('elbow_joint')} strokeWidth="1.5" />
                    <text x="88" y="202" textAnchor="middle">elbow</text>
                    <circle cx="168" cy="188" r="6" fill={nodeColor('wrist_hand')} stroke={nodeBorder('wrist_hand')} strokeWidth="1.5" />
                    <text x="168" y="202" textAnchor="middle">wrist/hand</text>
                    <circle cx="238" cy="188" r="6" fill="oklch(0.95 0.005 80)" stroke="oklch(0.86 0.012 80)" strokeWidth="1.5" />
                  </g>
                </svg>
              </div>
              <div className="dag-legend">
                <span><i style={{ background:'oklch(0.6 0.09 195)' }} /> mastered</span>
                <span><i style={{ background:'oklch(0.78 0.06 195)' }} /> in progress</span>
                <span><i style={{ background:'oklch(0.85 0.04 50)' }} /> weak</span>
              </div>
            </div>

            {/* Misconceptions panel */}
            <div className="panel">
              <div className="panel-head">
                <h4>Misconceptions logged</h4>
                <span className="pmeta">{misconceptions.length} this session</span>
              </div>
              <div className="panel-body">
                {misconceptions.length === 0 ? (
                  <p style={{ margin:0, color:'var(--ink-3)', fontSize:'12px' }}>None recorded yet.</p>
                ) : (
                  misconceptions.map((m, i) => (
                    <p key={i} style={{ margin: i < misconceptions.length-1 ? '0 0 8px':'0', fontSize:'12.5px' }}>
                      <b>{m.topic}.</b> {m.note}{' '}
                      <span className="mono muted">turn {m.turn}</span>
                    </p>
                  ))
                )}
              </div>
            </div>
          </>
        )}

        {activeTab === 'context' && (
          <div className="panel">
            <div className="panel-head">
              <h4>Topic Mastery</h4>
              <span className="pmeta">{TOPICS.length} topics</span>
            </div>
            <div className="panel-body">
              {TOPICS.map((topic) => {
                const m = topicMastery(topic.key);
                return (
                  <div key={topic.key} style={{ marginBottom:'10px', fontSize:'12px' }}>
                    <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'3px' }}>
                      <span>{topic.label}</span>
                      <span style={{ color:'var(--ink-3)', fontVariantNumeric:'tabular-nums' }}>
                        {m > 0 ? `${Math.round(m*100)}%` : '—'}
                      </span>
                    </div>
                    <div style={{ height:'3px', background:'var(--rule)', borderRadius:'2px', overflow:'hidden' }}>
                      <div style={{
                        height:'100%', width:`${m*100}%`,
                        background: m > 0.6 ? 'var(--accent)' : m > 0.3 ? 'oklch(0.78 0.06 195)' : m > 0 ? 'var(--warn)' : 'transparent',
                        transition:'width 600ms ease',
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {activeTab === 'trace' && (
          <div className="panel">
            <div className="panel-head">
              <h4>Agent trace</h4>
              <span className="pmeta">{supervisorSteps.length} steps</span>
            </div>
            <div className="panel-body" style={{ fontSize:'12px' }}>
              {supervisorSteps.length === 0 ? (
                <p style={{ margin:0, color:'var(--ink-3)' }}>Routing trace will appear during tutoring.</p>
              ) : (
                supervisorSteps.map((msg, i) => (
                  <div key={i} style={{ marginBottom:'10px', paddingBottom:'10px', borderBottom: i < supervisorSteps.length-1 ? '1px solid var(--rule)':'none' }}>
                    <div style={{ display:'flex', gap:'6px', alignItems:'center', marginBottom:'3px' }}>
                      <span style={{ fontFamily:'ui-monospace,monospace', fontWeight:500, color:'var(--ink-2)' }}>
                        {msg.supervisorStep!.agent}
                      </span>
                      {msg.supervisorStep!.phase && (
                        <span style={{ fontSize:'10px', color:'var(--ink-3)', fontFamily:'ui-monospace,monospace' }}>
                          → {msg.supervisorStep!.phase}
                        </span>
                      )}
                    </div>
                    <div style={{ color:'var(--ink-3)', lineHeight:1.4 }}>
                      {msg.supervisorStep!.reasoning}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="aside-foot">
        <Avatar size={16} state="idle" />
        <span>route: <span className="mono">{useSessionStore.getState().phase}</span> · grader pass · NLI ✓</span>
      </div>
    </div>
  );
}
