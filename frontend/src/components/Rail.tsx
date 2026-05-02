'use client';
import { useState, useEffect } from 'react';
import { useSessionStore } from '@/lib/store';
import { TOPICS } from '@/lib/topics';
import Avatar from './Avatar';

const PHASES = [
  { key: 'rapport',    label: 'Rapport',    time: '0–2m',   desc: 'Diagnostic probes calibrated your starting mastery.' },
  { key: 'tutoring',   label: 'Tutoring',   time: '2–12m',  desc: 'Socratic loop with progressive context revelation.' },
  { key: 'revisit',    label: 'Revisit',    time: '~8m',    desc: 'Steers back to the lowest-mastery topic.' },
  { key: 'assessment', label: 'Assessment', time: '12–14m', desc: 'Clinical NBCOT-style scenario.' },
  { key: 'wrapup',     label: 'Wrap-up',    time: '14–15m', desc: 'Report card · misconceptions · study tips.' },
];

const PHASE_ORDER = PHASES.map((p) => p.key);

export default function Rail({ onCollapse }: { onCollapse?: () => void }) {
  const currentPhase = useSessionStore((s) => s.phase);
  const mastery      = useSessionStore((s) => s.mastery);
  const avatarState  = useSessionStore((s) => s.avatarState);
  const studyFocus   = useSessionStore((s) => s.studyFocus);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const m = Math.floor(elapsedSeconds / 60);
  const s = String(elapsedSeconds % 60).padStart(2, '0');
  const timeStr = `${String(m).padStart(2,'0')}:${s} / 15:00`;

  const currentIdx = PHASE_ORDER.indexOf(currentPhase);

  // Strip "topic:" prefix for display
  const topicLabel = studyFocus
    ? studyFocus.replace('topic:', '').replace(/_/g, ' ')
    : null;

  return (
    <div className="rail">
      {/* Header */}
      <div className="rail-head">
        <Avatar size={30} state={avatarState} />
        <div className="name">
          <b>UnMask</b>
          <span>Anatomy Tutor</span>
        </div>
        <button
          className="icon-btn rail-collapse-btn"
          onClick={onCollapse}
          title="Collapse sidebar"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 6l-6 6 6 6" />
            <path d="M19 6l-6 6 6 6" />
          </svg>
        </button>
      </div>

      <div className="rail-section">Session</div>

      {/* Phase timeline — flat children for CSS grid */}
      <div className="phases">
        {PHASES.map((phase, idx) => {
          const isDone   = idx < currentIdx;
          const isActive = idx === currentIdx;
          return (
            <div key={phase.key} className={`phase${isActive ? ' active' : isDone ? ' done' : ''}`}>
              <span className="pdot" />
              <span className="ptitle">{phase.label}</span>
              <span className="ptime">{phase.time}</span>
              {isActive && <span className="pdesc">{phase.desc}</span>}
            </div>
          );
        })}
      </div>

      <div className="rail-section">Topics</div>

      <div className="topics">
        {TOPICS.map((topic) => {
          const m = mastery[topic.key] ?? 0;
          const isWeak = m > 0 && m < 0.35;
          const isActive = studyFocus === `topic:${topic.key}`;
          return (
            <button
              key={topic.key}
              className={`topic${isWeak ? ' weak' : ''}${isActive ? ' active' : ''}`}
            >
              <span className="tname">{topic.label}</span>
              <span className="tmeter"><i style={{ width: `${Math.round(m * 100)}%` }} /></span>
              <span className="tval">{m > 0 ? m.toFixed(2) : '—'}</span>
            </button>
          );
        })}
      </div>

      <div className="rail-foot">
        <span>NBCOT prep{topicLabel ? ` · ${topicLabel}` : ''}</span>
        <span className="session-time">{timeStr}</span>
      </div>
    </div>
  );
}
