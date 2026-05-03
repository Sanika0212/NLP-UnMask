'use client';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useSessionStore } from '@/lib/store';
import Rail from '@/components/Rail';
import Aside from '@/components/Aside';
import TopBar from '@/components/TopBar';
import Thread from '@/components/Thread';
import Composer from '@/components/Composer';
import SimulationPanel from '@/components/SimulationPanel';

export default function ChatPage() {
  const router = useRouter();
  const store = useSessionStore();
  const phase = useSessionStore((s) => s.phase);
  const [railCollapsed, setRailCollapsed] = useState(false);
  const [asideCollapsed, setAsideCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [activeTab, setActiveTab] = useState('tutor');
  const [paused, setPaused] = useState(false);

  // Redirect if session not set up
  useEffect(() => {
    if (!store.setupDone) {
      router.push('/');
    }
  }, [store.setupDone, router]);

  // Handle responsive collapse
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width < 880) {
        setRailCollapsed(true);
      } else {
        setRailCollapsed(false);
      }
      if (width < 640) {
        setIsMobile(true);
      } else {
        setIsMobile(false);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);


  // Determine grid template columns based on collapsed state
  let gridTemplate = '280px 1fr 340px';
  if (railCollapsed && asideCollapsed) {
    gridTemplate = '56px 1fr 44px';
  } else if (railCollapsed) {
    gridTemplate = '56px 1fr 340px';
  } else if (asideCollapsed) {
    gridTemplate = '280px 1fr 44px';
  }
  if (isMobile) {
    gridTemplate = '1fr';
  }

  return (
    <div
      className={`app ${railCollapsed ? 'rail-collapsed' : ''} ${asideCollapsed ? 'aside-collapsed' : ''}`}
      style={{
        gridTemplateColumns: gridTemplate,
        backgroundColor: 'var(--paper)',
      }}
    >
      {/* LEFT RAIL */}
      {!isMobile && (
        <Rail
          onCollapse={() => setRailCollapsed(!railCollapsed)}
          paused={paused}
        />
      )}

      {/* MAIN COLUMN */}
      <div
        className="main"
        style={{ position: 'relative' }}
      >
        {/* TopBar */}
        <TopBar
          onToggleRail={() => setRailCollapsed(!railCollapsed)}
          onToggleAside={() => setAsideCollapsed(!asideCollapsed)}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          paused={paused}
          onPause={() => setPaused((p) => !p)}
        />

        {/* Pause overlay */}
        {paused && (
          <div style={{
            position: 'absolute', inset: 0, zIndex: 50,
            background: 'rgba(var(--paper-rgb, 250,249,247), 0.92)',
            backdropFilter: 'blur(6px)',
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: '12px',
          }}>
            <div style={{ fontSize: '32px' }}>⏸</div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--ink)' }}>Session Paused</div>
            <div style={{ fontSize: '13px', color: 'var(--ink-3)' }}>Timer is paused. Click Resume to continue.</div>
            <button className="start-btn primary" onClick={() => setPaused(false)} style={{ marginTop: '8px' }}>
              <span className="t">Resume →</span>
            </button>
          </div>
        )}

        {/* Thread */}
        <Thread activeTab={activeTab} />

        {/* Wrapup Banner */}
        {phase === 'wrapup' && (
          <div style={{
            padding: '12px 20px',
            background: 'var(--accent-soft)',
            borderTop: '1px solid var(--accent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            flexShrink: 0,
          }}>
            <span style={{ fontSize: '13px', color: 'var(--ink-2)' }}>
              Session complete — please take the post-session survey to finish the pilot study.
            </span>
            <button
              onClick={() => router.push('/survey')}
              className="start-btn primary"
              style={{ minWidth: '160px', flexShrink: 0 }}
            >
              <span className="t">Take Survey →</span>
            </button>
          </div>
        )}

        {/* Composer — only on tutor tab and not paused */}
        {activeTab === 'tutor' && !paused && <Composer />}
      </div>

      {/* RIGHT ASIDE */}
      {!isMobile && (
        <Aside
          onCollapse={() => setAsideCollapsed(!asideCollapsed)}
        />
      )}

      {/* Simulation panel — only in local dev (NEXT_PUBLIC_SHOW_SIMULATOR=1) */}
      {process.env.NEXT_PUBLIC_SHOW_SIMULATOR === '1' && <SimulationPanel />}
    </div>
  );
}
