'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSessionStore } from '@/lib/store';
import Avatar from '@/components/Avatar';
import { TOPICS } from '@/lib/topics';

type LearningMode = 'visual' | 'text';

export default function WelcomePage() {
  const router = useRouter();
  const store = useSessionStore();
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<LearningMode | null>(null);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleStartSession = async () => {
    if (!selectedTopic) { setError('Please select a topic first.'); return; }
    if (!selectedMode)  { setError('Please select a learning mode.'); return; }
    setError('');
    setLoading(true);
    try {
      store.setStudentName(name || 'Student');
      await store.createSession();
      const result = await store.setupSession(selectedTopic, selectedMode);
      store.addMessage({
        role: 'bot',
        content: result.welcomeMessage,
        avatarState: 'speaking',
        quickReplies: ["Let's start →"],
      });
      router.push('/chat');
    } catch (err) {
      console.error('Failed to start session:', err);
      setError('Could not connect to the tutor — is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const isDisabled = !selectedTopic || !selectedMode || loading;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: '40px 20px',
      }}
    >
      <div className="welcome-screen">
        <Avatar state="idle" size={96} />

        <h1>
          Welcome to <span className="accent serif">UnMask.</span>
        </h1>

        <p className="lead">
          An NBCOT-prep tutor that <em>never hands you the answer.</em> We reveal concepts progressively, respecting your zone of proximal development.
        </p>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display:'block', fontSize:'11px', fontWeight:600, color:'var(--ink-3)', letterSpacing:'0.08em', textTransform:'uppercase', marginBottom:'8px' }}>
            Your name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Alex"
            style={{ width:'100%', maxWidth:'280px', padding:'9px 12px', border:'1px solid var(--rule-2)', borderRadius:'var(--r)', fontSize:'14px', background:'var(--paper-2)', color:'var(--ink)', outline:'none', fontFamily:'inherit' }}
            onFocus={(e) => { e.currentTarget.style.borderColor='var(--ink)'; }}
            onBlur={(e) => { e.currentTarget.style.borderColor='var(--rule-2)'; }}
          />
        </div>

        <div style={{ marginBottom: '28px' }}>
          <label
            style={{
              display: 'block',
              fontSize: '12px',
              fontWeight: '600',
              color: 'var(--ink-3)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              marginBottom: '12px',
            }}
          >
            Choose a topic
          </label>
          <div className="topic-grid">
            {TOPICS.map((topic) => (
              <button
                key={topic.key}
                className={`topic-btn ${selectedTopic === topic.key ? 'selected' : ''}`}
                onClick={() => setSelectedTopic(topic.key)}
              >
                <div style={{ marginBottom: '4px' }}>
                  {topic.label}
                </div>
                <div className="muted" style={{ fontSize: '12px' }}>
                  {topic.desc}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '28px' }}>
          <label
            style={{
              display: 'block',
              fontSize: '12px',
              fontWeight: '600',
              color: 'var(--ink-3)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              marginBottom: '12px',
            }}
          >
            Learning mode
          </label>
          <div className="mode-row">
            <button
              className={`mode-btn ${selectedMode === 'visual' ? 'selected' : ''}`}
              onClick={() => setSelectedMode('visual')}
            >
              🖼️ Diagrams
            </button>
            <button
              className={`mode-btn ${selectedMode === 'text' ? 'selected' : ''}`}
              onClick={() => setSelectedMode('text')}
            >
              📝 Text
            </button>
          </div>
        </div>

        {error && (
          <p style={{ color: 'var(--red, #c0392b)', fontSize: '13px', marginBottom: '12px', textAlign: 'center' }}>
            ⚠️ {error}
          </p>
        )}

        <div className="start-row">
          <button
            className="start-btn primary"
            onClick={handleStartSession}
            disabled={isDisabled}
            style={isDisabled ? { opacity: 0.4, cursor: 'not-allowed', pointerEvents: 'none' } : {}}
          >
            <span className="t">{loading ? 'Starting…' : 'Start session →'}</span>
            <span className="d">Begin NBCOT prep</span>
          </button>
          <button
            className="start-btn"
            onClick={() => router.push('/pilot')}
          >
            <span className="t">Pilot study</span>
            <span className="d">Survey + progress tracking</span>
          </button>
        </div>
      </div>
    </div>
  );
}
