'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Avatar from '@/components/Avatar';
import { useSessionStore } from '@/lib/store';
import { TOPICS } from '@/lib/topics';

type LearningMode = 'visual' | 'text';

interface Question {
  id: string;
  text: string;
  options: string[];
  correct: number;
}

const QUESTIONS: Question[] = [
  {
    id: 'q1',
    text: 'Which nerve innervates the deltoid muscle?',
    options: ['Axillary', 'Radial', 'Musculocutaneous', 'Ulnar'],
    correct: 0,
  },
  {
    id: 'q2',
    text: 'What does SITS stand for in the rotator cuff?',
    options: [
      'Supraspinatus, Infraspinatus, Teres minor, Subscapularis',
      'Supraspinatus, Infraspinatus, Trapezius, Serratus',
      'Spinal, Intramuscular, Thoracic, Shoulder',
      'Superior, Inferior, Thoracic, Scapular',
    ],
    correct: 0,
  },
  {
    id: 'q3',
    text: 'Which spinal roots form the brachial plexus?',
    options: ['C3–C8', 'C4–T2', 'C5–T1', 'C5–C8'],
    correct: 2,
  },
];

export default function PilotPage() {
  const router = useRouter();
  const store = useSessionStore();
  const [name, setName] = useState('');
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<LearningMode | null>(null);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allAnswered = QUESTIONS.every((q) => q.id in answers);
  const canStart = allAnswered && selectedTopic && selectedMode && selectedRole && name.trim();

  const handleStartStudy = async () => {
    if (!canStart) return;
    setLoading(true);
    setError(null);
    try {
      store.setStudentName(name.trim());
      store.setParticipantInfo(name.trim(), selectedRole!);
      store.setPreQuizResults(
        Object.values(answers),
        QUESTIONS.filter((q) => answers[q.id] === q.correct).length
      );
      await store.createSession();
      const result = await store.setupSession(selectedTopic!, selectedMode!);
      store.addMessage({
        role: 'bot',
        content: result.firstQuestion,
        avatarState: 'asking',
      });
      router.push('/chat');
    } catch (e) {
      setError('Failed to start session — is the backend running?');
      setLoading(false);
    }
  };

  const score = QUESTIONS.filter((q) => answers[q.id] === q.correct).length;
  const scoreReady = allAnswered;

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', padding: '40px 20px' }}>
      <div className="welcome-screen">
        <Avatar state={loading ? 'thinking' : 'idle'} size={80} />

        <h1 style={{ marginBottom: '8px' }}>
          Pilot Study <span className="accent serif">Pre-Quiz</span>
        </h1>
        <p className="lead" style={{ marginBottom: '28px' }}>
          Help us calibrate your baseline. Answer 3 questions, then pick a topic to study.
        </p>

        {/* Name input */}
        <div style={{ maxWidth: '520px', margin: '0 auto 20px', textAlign: 'left' }}>
          <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--ink-3)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '6px' }}>
            Your name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter your name"
            style={{ width: '100%', padding: '9px 12px', background: 'var(--paper-2)', border: '1px solid var(--rule)', borderRadius: 'var(--r)', fontSize: '14px', color: 'var(--ink)', outline: 'none', boxSizing: 'border-box' }}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--rule)'; }}
          />
        </div>

        {/* Pre-quiz questions */}
        <div style={{ maxWidth: '520px', margin: '0 auto 28px', display: 'flex', flexDirection: 'column', gap: '16px', textAlign: 'left' }}>
          {QUESTIONS.map((question, idx) => (
            <div key={question.id} style={{ background: 'var(--paper-2)', border: '1px solid var(--rule)', borderRadius: 'var(--r)', padding: '14px' }}>
              <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--ink)', marginBottom: '10px' }}>
                <span style={{ color: 'var(--accent)' }}>Q{idx + 1}.</span> {question.text}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {question.options.map((option, optIdx) => {
                  const isSelected = answers[question.id] === optIdx;
                  const isCorrect = scoreReady && optIdx === question.correct;
                  const isWrong = scoreReady && isSelected && optIdx !== question.correct;
                  return (
                    <button
                      key={optIdx}
                      onClick={() => !scoreReady && setAnswers((p) => ({ ...p, [question.id]: optIdx }))}
                      className={`topic-btn ${isSelected && !scoreReady ? 'selected' : ''}`}
                      style={{
                        padding: '8px 12px', fontSize: '13px', textAlign: 'left',
                        background: isCorrect ? 'var(--good-soft)' : isWrong ? 'var(--warn-soft)' : isSelected && !scoreReady ? 'var(--accent-soft)' : undefined,
                        borderColor: isCorrect ? 'var(--good)' : isWrong ? 'var(--warn)' : undefined,
                        cursor: scoreReady ? 'default' : 'pointer',
                      }}
                    >
                      <span style={{ marginRight: '8px', color: 'var(--ink-3)' }}>{String.fromCharCode(65 + optIdx)}.</span>
                      {option}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Score badge after all answered */}
        {scoreReady && (
          <div style={{ marginBottom: '24px', padding: '10px 16px', background: 'var(--paper-2)', border: '1px solid var(--rule)', borderRadius: '999px', display: 'inline-flex', gap: '8px', alignItems: 'center', fontSize: '13px', color: 'var(--ink-2)' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: score === 3 ? 'var(--good)' : score >= 1 ? 'var(--accent)' : 'var(--warn)', display: 'inline-block' }} />
            Pre-quiz: {score} / {QUESTIONS.length} correct
          </div>
        )}

        {/* Topic + mode selection — shown after quiz is answered */}
        {scoreReady && (
          <>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--ink-3)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '10px' }}>
                Choose a topic to study
              </label>
              <div className="topic-grid">
                {TOPICS.map((topic) => (
                  <button
                    key={topic.key}
                    className={`topic-btn ${selectedTopic === topic.key ? 'selected' : ''}`}
                    onClick={() => setSelectedTopic(topic.key)}
                  >
                    <div style={{ marginBottom: '2px' }}>{topic.label}</div>
                    <div className="muted" style={{ fontSize: '11px' }}>{topic.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--ink-3)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '10px' }}>
                Learning mode
              </label>
              <div className="mode-row">
                <button className={`mode-btn ${selectedMode === 'visual' ? 'selected' : ''}`} onClick={() => setSelectedMode('visual')}>🖼️ Diagrams</button>
                <button className={`mode-btn ${selectedMode === 'text' ? 'selected' : ''}`} onClick={() => setSelectedMode('text')}>📝 Text</button>
              </div>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--ink-3)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '10px' }}>
                Your role
              </label>
              <div className="mode-row">
                <button className={`mode-btn ${selectedRole === 'OT Student' ? 'selected' : ''}`} onClick={() => setSelectedRole('OT Student')}>Occupational Therapist Student</button>
                <button className={`mode-btn ${selectedRole === 'CS Student' ? 'selected' : ''}`} onClick={() => setSelectedRole('CS Student')}>Computer Science Student</button>
                <button className={`mode-btn ${selectedRole === 'Other' ? 'selected' : ''}`} onClick={() => setSelectedRole('Other')}>Other</button>
              </div>
            </div>
          </>
        )}

        {error && <p style={{ color: 'var(--warn)', fontSize: '13px', marginBottom: '12px' }}>{error}</p>}

        <div className="start-row" style={{ marginBottom: '14px' }}>
          <button
            className="start-btn primary"
            onClick={handleStartStudy}
            disabled={!canStart || loading}
            style={!canStart || loading ? { opacity: 0.5, cursor: 'not-allowed' } : { minWidth: '220px' }}
          >
            <span className="t">{loading ? 'Starting…' : 'Continue to Study →'}</span>
            <span className="d">
              {!name.trim() ? 'Enter your name above' : !allAnswered ? 'Answer all questions first' : !selectedTopic ? 'Select a topic above' : !selectedMode ? 'Select a learning mode above' : !selectedRole ? 'Select your role above' : ''}
            </span>
          </button>
        </div>

        <button
          onClick={() => router.back()}
          style={{ background: 'none', border: 'none', color: 'var(--ink-3)', fontSize: '13px', cursor: 'pointer', transition: 'color 120ms' }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--ink)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--ink-3)'; }}
        >
          ← Back
        </button>
      </div>
    </div>
  );
}
