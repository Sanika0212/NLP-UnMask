'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSessionStore } from '@/lib/store';
import { loadUser, LastSession } from '@/lib/userStore';
import Avatar from '@/components/Avatar';
import { TOPICS } from '@/lib/topics';

type LearningMode = 'visual' | 'text';

export default function WelcomePage() {
  const router = useRouter();
  const store = useSessionStore();
  const [step, setStep] = useState<1 | 2>(1);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<LearningMode | null>(null);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isResume, setIsResume] = useState(false);
  const [prevMastery, setPrevMastery] = useState<Record<string, number>>({});
  const [prevWeakTopics, setPrevWeakTopics] = useState<string[]>([]);
  const [prevMisconceptions, setPrevMisconceptions] = useState<{topic:string;note:string;turn:number}[]>([]);
  const [lastSession, setLastSession] = useState<LastSession | null>(null);
  const [showChat, setShowChat] = useState(false);

  useEffect(() => {
    if (!name.trim() || name.trim() === 'Student') {
      setPrevMastery({});
      setPrevWeakTopics([]);
      setPrevMisconceptions([]);
      return;
    }
    const userData = loadUser(name.trim());
    setPrevMastery(userData.mastery ?? {});
    setPrevWeakTopics(userData.weakTopics ?? []);
    setPrevMisconceptions(userData.misconceptions ?? []);
    setLastSession(userData.lastSession ?? null);
  }, [name]);

  const resumeTopics = TOPICS.filter(t => (prevMastery[t.key] ?? 0) > 0.05)
    .sort((a, b) => (prevMastery[b.key] ?? 0) - (prevMastery[a.key] ?? 0));

  const hasHistory = prevWeakTopics.length > 0 || prevMisconceptions.length > 0;

  const handleContinue = () => {
    if (!name.trim()) { setError('Please enter your name.'); return; }
    setError('');
    setStep(2);
  };

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

  // ── Step 1: name entry ────────────────────────────────────────────────────
  if (step === 1) {
    return (
      <div style={{ display:'flex', alignItems:'center', justifyContent:'center', minHeight:'100vh', padding:'40px 20px' }}>
        <div className="welcome-screen">
          <Avatar state="idle" size={96} />
          <h1>Welcome to <span className="accent serif">UnMask.</span></h1>
          <p className="lead">
            An NBCOT-prep tutor that <em>never hands you the answer.</em> We reveal concepts progressively, respecting your zone of proximal development.
          </p>

          <div style={{ marginBottom: '24px', width: '100%', maxWidth: '320px', textAlign:'center', margin: '0 auto 24px' }}>
            <label style={{ display:'block', fontSize:'11px', fontWeight:600, color:'var(--ink-3)', letterSpacing:'0.08em', textTransform:'uppercase', marginBottom:'8px', textAlign:'center' }}>
              Your name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => { setName(e.target.value); setError(''); }}
              onKeyDown={(e) => e.key === 'Enter' && handleContinue()}
              placeholder="e.g. Alex"
              autoFocus
              style={{ width:'100%', padding:'10px 14px', border:'1px solid var(--rule-2)', borderRadius:'var(--r)', fontSize:'15px', background:'var(--paper-2)', color:'var(--ink)', outline:'none', fontFamily:'inherit', textAlign:'center' }}
              onFocus={(e) => { e.currentTarget.style.borderColor='var(--ink)'; }}
              onBlur={(e) => { e.currentTarget.style.borderColor='var(--rule-2)'; }}
            />
          </div>

          {error && (
            <p style={{ color:'var(--red, #c0392b)', fontSize:'13px', marginBottom:'12px', textAlign:'center' }}>
              ⚠️ {error}
            </p>
          )}

          <button
            className="start-btn primary"
            onClick={handleContinue}
            style={{ width:'100%', maxWidth:'320px', margin:'0 auto', display:'block' }}
          >
            <span className="t">Continue →</span>
            <span className="d">Choose your topic</span>
          </button>
        </div>
      </div>
    );
  }

  // ── Step 2: topic / resume / history ─────────────────────────────────────
  return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', minHeight:'100vh', padding:'40px 20px' }}>
      <div className="welcome-screen">

        {/* back + greeting */}
        <div style={{ display:'flex', alignItems:'center', gap:'10px', marginBottom:'24px', width:'100%' }}>
          <button
            onClick={() => setStep(1)}
            style={{ background:'none', border:'none', cursor:'pointer', color:'var(--ink-3)', fontSize:'13px', padding:'4px 0' }}
          >
            ← Back
          </button>
          <span style={{ flex:1 }} />
          <span style={{ fontSize:'13px', color:'var(--ink-2)' }}>Hi, <strong>{name}</strong></span>
        </div>

        {/* ── Previous session history ── */}
        {(hasHistory || lastSession) && (
          <div style={{ marginBottom:'28px', width:'100%', background:'var(--paper-2)', border:'1px solid var(--rule-2)', borderRadius:'var(--r)', padding:'14px 16px' }}>
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'10px' }}>
              <div style={{ fontSize:'11px', fontWeight:600, color:'var(--ink-3)', letterSpacing:'0.08em', textTransform:'uppercase' }}>
                Last session notes
                {lastSession && (
                  <span style={{ fontWeight:400, textTransform:'none', letterSpacing:0, marginLeft:'8px', color:'var(--ink-3)' }}>
                    · {lastSession.topic.replace(/_/g,' ')} · {new Date(lastSession.date).toLocaleDateString()}
                  </span>
                )}
              </div>
              {lastSession && lastSession.messages.length > 0 && (
                <button
                  onClick={() => setShowChat(true)}
                  style={{ fontSize:'12px', color:'var(--accent)', background:'none', border:'none', cursor:'pointer', padding:'2px 0', fontWeight:600 }}
                >
                  View chat →
                </button>
              )}
            </div>
            {prevWeakTopics.length > 0 && (
              <div style={{ marginBottom:'8px' }}>
                <span style={{ fontSize:'11px', color:'var(--ink-3)', fontWeight:600 }}>Weak topics: </span>
                <span style={{ fontSize:'12px', color:'var(--ink-2)' }}>
                  {prevWeakTopics.map(t => t.replace(/_/g, ' ')).join(' · ')}
                </span>
              </div>
            )}
            {prevMisconceptions.length > 0 && (
              <div>
                <div style={{ fontSize:'11px', color:'var(--ink-3)', fontWeight:600, marginBottom:'4px' }}>Misconceptions to revisit:</div>
                <div style={{ display:'flex', flexDirection:'column', gap:'4px' }}>
                  {prevMisconceptions.slice(0, 4).map((m, i) => (
                    <div key={i} style={{ fontSize:'12px', color:'var(--ink-2)', paddingLeft:'8px', borderLeft:'2px solid var(--accent)' }}>
                      <span style={{ fontWeight:600 }}>{m.topic.replace(/_/g, ' ')}: </span>{m.note}
                    </div>
                  ))}
                  {prevMisconceptions.length > 4 && (
                    <div style={{ fontSize:'11px', color:'var(--ink-3)' }}>+{prevMisconceptions.length - 4} more</div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Chat history overlay ── */}
        {showChat && lastSession && (
          <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.45)', zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center', padding:'20px' }}
            onClick={() => setShowChat(false)}>
            <div style={{ background:'var(--paper)', borderRadius:'var(--r)', width:'100%', maxWidth:'560px', maxHeight:'80vh', display:'flex', flexDirection:'column', overflow:'hidden' }}
              onClick={e => e.stopPropagation()}>
              {/* header */}
              <div style={{ padding:'14px 18px', borderBottom:'1px solid var(--rule-2)', display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0 }}>
                <div>
                  <span style={{ fontSize:'14px', fontWeight:600, color:'var(--ink)' }}>
                    {lastSession.topic.replace(/_/g,' ')}
                  </span>
                  <span style={{ fontSize:'12px', color:'var(--ink-3)', marginLeft:'10px' }}>
                    {new Date(lastSession.date).toLocaleDateString(undefined, { month:'short', day:'numeric', year:'numeric' })}
                  </span>
                </div>
                <button onClick={() => setShowChat(false)} style={{ background:'none', border:'none', cursor:'pointer', fontSize:'18px', color:'var(--ink-3)', lineHeight:1 }}>✕</button>
              </div>
              {/* messages */}
              <div style={{ overflowY:'auto', padding:'16px 18px', display:'flex', flexDirection:'column', gap:'10px' }}>
                {lastSession.messages.map((m, i) => (
                  <div key={i} style={{ display:'flex', flexDirection:'column', alignItems: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                    {m.role === 'bot' && m.author && (
                      <span style={{ fontSize:'10px', color:'var(--ink-3)', marginBottom:'2px', paddingLeft:'2px' }}>{m.author}</span>
                    )}
                    <div style={{
                      maxWidth:'85%',
                      padding:'8px 12px',
                      borderRadius: m.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                      background: m.role === 'user' ? 'var(--accent)' : 'var(--paper-2)',
                      color: m.role === 'user' ? 'var(--accent-ink)' : 'var(--ink)',
                      fontSize:'13px',
                      lineHeight:'1.5',
                      border: m.role === 'bot' ? '1px solid var(--rule-2)' : 'none',
                    }}>
                      {m.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── Resume section ── */}
        {resumeTopics.length > 0 && (
          <div style={{ marginBottom:'28px', width:'100%' }}>
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
                    style={{ display:'flex', alignItems:'center', gap:'12px', padding:'10px 14px', borderRadius:'var(--r)', border: isSelected ? '1.5px solid var(--accent)' : '1px solid var(--rule-2)', background: isSelected ? 'var(--accent-soft)' : 'var(--paper-2)', cursor:'pointer', textAlign:'left', transition:'all .15s' }}
                  >
                    <div style={{ position:'relative', width:'40px', height:'40px', flexShrink:0 }}>
                      <svg width="40" height="40" style={{ transform:'rotate(-90deg)' }}>
                        <circle cx="20" cy="20" r="16" fill="none" stroke="var(--rule)" strokeWidth="4" />
                        <circle cx="20" cy="20" r="16" fill="none"
                          stroke={pct >= 70 ? '#10b981' : pct >= 40 ? 'var(--accent)' : '#f59e0b'}
                          strokeWidth="4"
                          strokeDasharray={`${2 * Math.PI * 16}`}
                          strokeDashoffset={`${2 * Math.PI * 16 * (1 - pct / 100)}`}
                          strokeLinecap="round"
                        />
                      </svg>
                      <span style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', fontSize:'10px', fontWeight:700, color:'var(--ink-2)' }}>{pct}%</span>
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

        {/* ── Topic grid ── */}
        <div style={{ marginBottom:'28px', width:'100%' }}>
          <label style={{ display:'block', fontSize:'12px', fontWeight:'600', color:'var(--ink-3)', letterSpacing:'0.08em', textTransform:'uppercase', marginBottom:'12px' }}>
            {resumeTopics.length > 0 ? 'Or start a new topic' : 'Choose a topic'}
          </label>
          <div className="topic-grid">
            {TOPICS.map((topic) => (
              <button
                key={topic.key}
                className={`topic-btn ${selectedTopic === topic.key && !isResume ? 'selected' : ''}`}
                onClick={() => handleSelectTopic(topic.key)}
              >
                <div style={{ marginBottom:'4px' }}>{topic.label}</div>
                <div className="muted" style={{ fontSize:'12px' }}>{topic.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* ── Learning mode ── */}
        <div style={{ marginBottom:'28px', width:'100%' }}>
          <label style={{ display:'block', fontSize:'12px', fontWeight:'600', color:'var(--ink-3)', letterSpacing:'0.08em', textTransform:'uppercase', marginBottom:'12px' }}>
            Learning mode
          </label>
          <div className="mode-row">
            <button className={`mode-btn ${selectedMode === 'visual' ? 'selected' : ''}`} onClick={() => setSelectedMode('visual')}>🖼️ Diagrams</button>
            <button className={`mode-btn ${selectedMode === 'text' ? 'selected' : ''}`} onClick={() => setSelectedMode('text')}>📝 Text</button>
          </div>
        </div>

        {error && (
          <p style={{ color:'var(--red, #c0392b)', fontSize:'13px', marginBottom:'12px', textAlign:'center' }}>⚠️ {error}</p>
        )}

        <div className="start-row">
          <button
            className="start-btn primary"
            onClick={handleStartSession}
            disabled={isDisabled}
            style={isDisabled ? { opacity:0.4, cursor:'not-allowed', pointerEvents:'none' } : {}}
          >
            <span className="t">{loading ? 'Starting…' : isResume ? 'Resume session →' : 'Start session →'}</span>
            <span className="d">{isResume ? 'Skip diagnostic, continue tutoring' : 'Begin NBCOT prep'}</span>
          </button>
          <button className="start-btn" onClick={() => router.push('/pilot')}>
            <span className="t">Pilot study</span>
            <span className="d">Survey + progress tracking</span>
          </button>
        </div>

      </div>
    </div>
  );
}
