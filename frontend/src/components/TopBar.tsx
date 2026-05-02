'use client';
import { useState } from 'react';
import { useSessionStore } from '@/lib/store';
import { TOPICS } from '@/lib/topics';

export default function TopBar({
  onToggleRail,
  onToggleAside,
  activeTab,
  onTabChange,
  paused,
  onPause,
}: {
  onToggleRail?: () => void;
  onToggleAside?: () => void;
  activeTab: string;
  onTabChange: (tab: string) => void;
  paused?: boolean;
  onPause?: () => void;
}) {
  const currentTopic = useSessionStore((s) => s.currentTopic);
  const pcrMode      = useSessionStore((s) => s.pcrMode);
  const phase        = useSessionStore((s) => s.phase);
  const misconceptions = useSessionStore((s) => s.misconceptions);
  const studentName = useSessionStore((s) => s.studentName);

  const topicLabel = TOPICS.find((t) => t.key === currentTopic)?.label ?? 'Anatomy';

  const phaseLabel: Record<string,string> = {
    rapport: 'Rapport', tutoring: 'Tutoring', assessment: 'Assessment', wrapup: 'Wrap-up',
  };

  return (
    <div className="topbar">
      {/* Toggle rail */}
      <button className="icon-btn" onClick={onToggleRail} title="Toggle sidebar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <path d="M9 4v16" />
        </svg>
      </button>

      {/* Breadcrumb */}
      <div className="crumbs">
        <b>Session</b>
        <span className="sep">›</span>
        <span>{topicLabel}</span>
        <span className="pcr-tag">{pcrMode}</span>
      </div>

      {/* Nav tabs */}
      <nav className="topnav">
        {(['tutor','practice','assess','progress'] as const).map((tab) => (
          <button
            key={tab}
            className={`nav-tab${activeTab === tab ? ' active' : ''}`}
            onClick={() => onTabChange(tab)}
          >
            {tab === 'tutor' && (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            )}
            {tab === 'practice' && (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
            )}
            {tab === 'assess' && (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
            )}
            {tab === 'assess' && misconceptions.length > 0 && (
              <span className="badge">{misconceptions.length}</span>
            )}
            {tab === 'progress' && (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M3 3v18h18" />
                <path d="M7 14l4-4 4 4 6-6" />
              </svg>
            )}
            <span className="lbl" style={{ textTransform: 'capitalize' }}>{tab}</span>
          </button>
        ))}

        <span className="nav-divider" />

        <button className="icon-btn" title="Notes" onClick={() => onTabChange('assess')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M5 4h14v16H5z" />
            <path d="M9 9h6M9 13h6M9 17h4" />
          </svg>
        </button>
        <button className="icon-btn" title="Library" onClick={() => onTabChange('practice')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M4 4h6v16H4zM14 4h6v16h-6z" />
          </svg>
        </button>

        {/* Toggle aside */}
        <button className="icon-btn" onClick={onToggleAside} title="Toggle inspector">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="16" rx="2" />
            <path d="M15 4v16" />
            <path d="M19 9l-2 3 2 3" />
          </svg>
        </button>

        <span className="nav-divider" />

        {/* Pause / Resume */}
        <button className="icon-btn" onClick={onPause} title={paused ? 'Resume session' : 'Pause session'}>
          {paused ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <polygon points="5,3 19,12 5,21" fill="currentColor" stroke="none" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none" />
              <rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none" />
            </svg>
          )}
        </button>

        {/* User chip */}
        <button className="user-chip">
          <span className="av">{studentName.slice(0,2).toUpperCase()}</span>
          <span className="uname">{studentName}</span>
        </button>
      </nav>
    </div>
  );
}
