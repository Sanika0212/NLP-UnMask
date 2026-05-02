'use client';
import { useRef, useEffect } from 'react';
import { useSessionStore } from '@/lib/store';
import Avatar from '@/components/Avatar';
import Turn from './Turn';
import ProgressView from './ProgressView';
import PracticeView from './PracticeView';
import AssessView from './AssessView';

export default function Thread({ activeTab }: { activeTab?: string }) {
  const threadRef = useRef<HTMLDivElement>(null);
  const messages = useSessionStore((state) => state.messages);
  const isThinking = useSessionStore((state) => state.isThinking);
  const elapsedSeconds = 0;

  // All hooks must run unconditionally before any early return
  useEffect(() => {
    if (threadRef.current && activeTab === 'tutor') {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [messages.length, activeTab]);

  // Show tab-specific views
  if (activeTab === 'progress') return <ProgressView />;
  if (activeTab === 'practice') return <PracticeView />;
  if (activeTab === 'assess') return <AssessView />;

  if (messages.length === 0) {
    return (
      <div
        ref={threadRef}
        className="thread"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div style={{
          textAlign: 'center',
          color: 'var(--ink-3)',
          fontSize: '14px',
        }}>
          <p style={{ margin: '0 0 8px' }}>No messages yet</p>
          <p style={{ margin: 0, fontSize: '12px' }}>
            Start the conversation with a question or observation.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={threadRef} className="thread">
      <div className="thread-inner">
        {messages.map((msg) => (
          <Turn
            key={msg.id}
            message={msg}
            elapsed={elapsedSeconds}
          />
        ))}
        {isThinking && (
          <div className="turn">
            <div className="av"><Avatar state="thinking" size={32} /></div>
            <div className="body">
              <div className="meta">UnMask · Thinking…</div>
              <span className="status thinking">
                <span className="pip" />
                Processing your answer…
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
