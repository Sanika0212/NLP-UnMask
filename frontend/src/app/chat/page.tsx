'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSessionStore } from '@/lib/store';
import Rail from '@/components/Rail';
import Aside from '@/components/Aside';
import TopBar from '@/components/TopBar';
import Thread from '@/components/Thread';
import Composer from '@/components/Composer';

export default function ChatPage() {
  const router = useRouter();
  const store = useSessionStore();
  const phase = useSessionStore((s) => s.phase);
  const [railCollapsed, setRailCollapsed] = useState(false);
  const [asideCollapsed, setAsideCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [activeTab, setActiveTab] = useState('tutor');

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
        />
      )}

      {/* MAIN COLUMN */}
      <div
        className="main"
      >
        {/* TopBar */}
        <TopBar
          onToggleRail={() => setRailCollapsed(!railCollapsed)}
          onToggleAside={() => setAsideCollapsed(!asideCollapsed)}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />

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

        {/* Composer */}
        <Composer />
      </div>

      {/* RIGHT ASIDE */}
      {!isMobile && (
        <Aside
          onCollapse={() => setAsideCollapsed(!asideCollapsed)}
        />
      )}
    </div>
  );
}
