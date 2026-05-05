'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSessionStore } from '@/lib/store';
import { loadUser } from '@/lib/userStore';
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
  const [isResume, setIsResume] = useState(false);
  const [prevMastery, setPrevMastery] = useState<Record<string, number>>({});

  // Load previous mastery whenever name changes
  useEffect(() => {
    if (!name.trim() || name.trim() === 'Student') {
      setPrevMastery({});
      return;
    }
    const userData = loadUser(name.trim());
    setPrevMastery(userData.mastery ?? {});
  }, [name]);

  // Topics with meaningful prior mastery (>5%)
  const resumeTopics = TOPICS.filter(t => (prevMastery[t.key] ?? 0) > 0.05)
    .sort((a, b) => (prevMastery[b.key] ?? 0) - (prevMastery[a.key] ?? 0));

  const handleResumeTopic = (topicKey: string) => {
    setSelectedTopic(topicKey);
    setIsResume(true);
  };

  const handleSelectTopic = (topicKey: string) => {
    setSelectedTopic(topicKey);
    setIsResume(false);
  };

  const handleStartSession = async () => {
    if (!selectedTopic) { setError('Please select a topic first.'); return; }
    if (!selectedMode)  { setError('Please select a learning mode.'); return; }
    setError('');
    setLoading(true);
    try {
      store.setStudentName(name || 'Student');
      await store.createSession();
      const result = await store.setupSession(selectedTopic, selectedMode, isResume);
      store.addMessage({
        role: 'bot',
        content: result.welcomeMessage,
        avatarState: 'speaking',
        quickReplies: isResume ? ["Let's continue →"] : ["Let's start →"],
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

        {/* ── Resume section ── */}
        {resumeTopics.length > 0 && (
          <div style={{ marginBottom: '28px', width: '100%' }}>
            <label style={{ display:'block', fontSize:'11px', fontWeight:600, color:'var(--ink-3)', letterSpacing:'0.08em', textTransform:'uppercase', marginBottom:'10px' }}>
              Continue where you left off
            </label>
            <div style={{ display:'flex', flexDirection:'column', gap:'8px' }}>
              {resumeTopics.map(t => {
                const pct = Math.round((prevMastery[t.key] ?? 0) * 100);
                const isSelected = selectedTopic === t.key && isResume;
                return (
                  <button
                    key={t.key}
                    onClick={() => handleResumeTopic(t.key)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '10px 14px',
                      borderRadius: 'var(--r)',
                      border: isSelected ? '1.5px solid var(--accent)' : '1px solid var(--rule-2)',
                      background: isSelected ? 'var(--accent-soft)' : 'var(--paper-2)',
                      cursor: 'pointer',
                      textAlign: 'left',
                      transition: 'all .15s',
                    }}
                  >
                    {/* mastery bar */}
                    <div style={{ position:'relative', width:'40px', height:'40px', flexShrink:0 }}>
                      <svg width="40" height="40" style={{ transform:'rotate(-90deg)' }}>
                        <circle cx="20" cy="20" r="16" fill="none" stroke="var(--rule)" strokeWidth="4" />
                        <circle
                          cx="20" cy="20" r="16" fill="none"
                          stroke={pct >= 70 ? '#10b981' : pct >= 40 ? 'var(--accent)' : '#f59e0b'}
                          strokeWidth="4"
                          strokeDasharray={`${2 * Math.PI * 16}`}
                          strokeDashoffset={`${2 * Math.PI * 16 * (1 - pct / 100)}`}
                          strokeLinecap="round"
                        />
                      </svg>
                      <span style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', fontSize:'10px', fontWeight:700, color:'var(--ink-2)' }}>
                        {pct}%
                      </span>
                    </div>
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ fontSize:'13px', fontWeight:600, color: isSelected ? 'var(--accent-ink)' : 'var(--ink)', marginBottom:'2px' }}>{t.label}</div>
                      <div style={{ fontSize:'11px', color:'var(--ink-3)' }}>{t.desc}</div>
                    </div>
                    <span style={{ fontSize:'12px', color: isSelected ? 'var(--accent)' : 'var(--ink-3)', fontWeight: isSelected ? 700 : 400, flexShrink:0 }}>
                      {isSelected ? 'Selected ✓' : 'Resume →'}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

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
            {resumeTopics.length > 0 ? 'Or start a new topic' : 'Choose a topic'}
          </label>
          <div className="topic-grid">
            {TOPICS.map((topic) => (
              <button
                key={topic.key}
                className={`topic-btn ${selectedTopic === topic.key && !isResume ? 'selected' : ''}`}
                onClick={() => handleSelectTopic(topic.key)}
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
            <span className="t">
              {loading ? 'Starting…' : isResume ? 'Resume session →' : 'Start session →'}
            </span>
            <span className="d">
              {isResume ? 'Skip diagnostic, continue tutoring' : 'Begin NBCOT prep'}
            </span>
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
