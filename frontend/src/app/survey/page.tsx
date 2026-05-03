'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Avatar from '@/components/Avatar';
import { useSessionStore, apiBase } from '@/lib/store';

type Step = 'post_quiz' | 'likert' | 'done';

interface QuizQuestion {
  id: string;
  text: string;
  options: string[];
  correct: number;
}

const POST_QUIZ: QuizQuestion[] = [
  {
    id: 'q1',
    text: 'Saturday night palsy (arm draped over a chair back during sleep) compresses which nerve?',
    options: ['Median nerve', 'Radial nerve', 'Ulnar nerve', 'Axillary nerve'],
    correct: 1, // B. Radial nerve
  },
  {
    id: 'q2',
    text: "Erb's palsy (C5–C6) and Klumpke's palsy (C8–T1) are both injuries to which nerve network?",
    options: ['Lumbar plexus', 'Cervical plexus', 'Sacral plexus', 'Brachial plexus'],
    correct: 3, // D. Brachial plexus
  },
  {
    id: 'q3',
    text: 'Carpal tunnel syndrome compresses a nerve, causing weakness in thumb opposition. Which nerve?',
    options: ['Radial nerve', 'Ulnar nerve', 'Median nerve', 'Anterior interosseous nerve'],
    correct: 2, // C. Median nerve
  },
  {
    id: 'q4',
    text: 'An OT patient cannot externally rotate or abduct the shoulder after a fall. Which muscle group is most likely torn?',
    options: [
      'Long head of biceps brachii',
      'Rotator cuff',
      'Deltoid and trapezius',
      'Pectoralis major',
    ],
    correct: 1, // B. Rotator cuff
  },
  {
    id: 'q5',
    text: 'Cubitus valgus deformity stretches a nerve at the elbow, causing tingling in the ring and little fingers. Which nerve?',
    options: ['Median nerve', 'Radial nerve', 'Ulnar nerve', 'Musculocutaneous nerve'],
    correct: 2, // C. Ulnar nerve
  },
];

const EXPERIENCE_QUESTIONS = [
  'The tutor helped me understand anatomy concepts better.',
  'The Socratic questioning approach was effective for my learning.',
  'The tutor felt natural and easy to interact with.',
  'I would use this tool to study for the NBCOT exam.',
  'I would recommend this tool to other OT or anatomy students.',
];

export default function SurveyPage() {
  const router = useRouter();
  const store = useSessionStore();
  const [step, setStep] = useState<Step>('post_quiz');
  const [postAnswers, setPostAnswers] = useState<Record<string, number>>({});
  const [ratings, setRatings] = useState<Record<number, number>>({});
  const [openFeedback, setOpenFeedback] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allPostAnswered = POST_QUIZ.every((q) => q.id in postAnswers);
  const allRated = Object.keys(ratings).length === EXPERIENCE_QUESTIONS.length;

  const postScore = POST_QUIZ.filter((q) => postAnswers[q.id] === q.correct).length;
  const avgRating = allRated
    ? (Object.values(ratings).reduce((a, b) => a + b, 0) / EXPERIENCE_QUESTIONS.length).toFixed(1)
    : '—';

  const handleSubmitSurvey = async () => {
    if (!allPostAnswered || !allRated) return;
    setLoading(true);
    setError(null);

    try {
      const answerLetters = Object.keys(postAnswers)
        .sort()
        .map((qid) => {
          const idx = postAnswers[qid];
          return ['A', 'B', 'C', 'D'][idx];
        });

      const body = {
        participant_id: store.participantId,
        role: store.participantRole,
        pre_score: store.preQuizScore,
        pre_answers: store.preQuizAnswers.map((i: number) => ['A', 'B', 'C', 'D'][i]),
        post_answers: answerLetters,
        exp_ratings: Object.values(ratings),
        open_feedback: openFeedback,
        topics_covered: store.currentTopic || '',
        session_duration_min: 0,
      };

      const res = await fetch(`${apiBase()}/api/sessions/${store.sessionId}/survey`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to submit survey');
      }

      setStep('done');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit survey');
      setLoading(false);
    }
  };

  const handleBackHome = () => {
    store.reset();
    router.push('/');
  };

  if (step === 'done') {
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
          <Avatar state="celebrate" size={80} />

          <h1 style={{ marginBottom: '8px' }}>
            Thank you for <span className="accent serif">participating!</span>
          </h1>
          <p className="lead" style={{ marginBottom: '28px' }}>
            Your responses help us improve the anatomy tutor.
          </p>

          {/* Results summary */}
          <div
            style={{
              maxWidth: '520px',
              margin: '0 auto 28px',
              padding: '20px',
              background: 'var(--paper-2)',
              border: '1px solid var(--rule)',
              borderRadius: 'var(--r)',
              textAlign: 'left',
            }}
          >
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', color: 'var(--ink-3)', fontWeight: 600, marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Your Results
              </div>
              <div style={{ display: 'flex', gap: '16px', fontSize: '15px' }}>
                <div>
                  <span style={{ color: 'var(--ink-2)' }}>Pre-Quiz:</span>{' '}
                  <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{store.preQuizScore}/5</span>
                </div>
                <div>
                  <span style={{ color: 'var(--ink-2)' }}>Post-Quiz:</span>{' '}
                  <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{postScore}/5</span>
                </div>
                <div>
                  <span style={{ color: 'var(--ink-2)' }}>Gain:</span>{' '}
                  <span
                    style={{
                      fontWeight: 600,
                      color: postScore > store.preQuizScore ? 'var(--good)' : postScore === store.preQuizScore ? 'var(--accent)' : 'var(--warn)',
                    }}
                  >
                    {postScore > store.preQuizScore ? '+' : ''}{postScore - store.preQuizScore}
                  </span>
                </div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '12px', color: 'var(--ink-3)', fontWeight: 600, marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Experience Rating
              </div>
              <div style={{ fontSize: '15px' }}>
                <span style={{ color: 'var(--ink-2)' }}>Average:</span>{' '}
                <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{avgRating}/5</span>
              </div>
            </div>
          </div>

          <div className="start-row">
            <button
              className="start-btn primary"
              onClick={handleBackHome}
              style={{ minWidth: '220px' }}
            >
              <span className="t">← Back to Home</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

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
        <Avatar state={loading ? 'thinking' : 'idle'} size={80} />

        <h1 style={{ marginBottom: '8px' }}>
          Post-Session <span className="accent serif">Survey</span>
        </h1>

        {step === 'post_quiz' && (
          <>
            <p className="lead" style={{ marginBottom: '28px' }}>
              Answer 5 questions about the concepts you just studied.
            </p>

            {/* Post-quiz questions */}
            <div style={{ maxWidth: '520px', margin: '0 auto 28px', display: 'flex', flexDirection: 'column', gap: '16px', textAlign: 'left' }}>
              {POST_QUIZ.map((question, idx) => (
                <div key={question.id} style={{ background: 'var(--paper-2)', border: '1px solid var(--rule)', borderRadius: 'var(--r)', padding: '14px' }}>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--ink)', marginBottom: '10px' }}>
                    <span style={{ color: 'var(--accent)' }}>Q{idx + 1}.</span> {question.text}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {question.options.map((option, optIdx) => {
                      const isSelected = postAnswers[question.id] === optIdx;
                      const isCorrect = allPostAnswered && optIdx === question.correct;
                      const isWrong = allPostAnswered && isSelected && optIdx !== question.correct;
                      return (
                        <button
                          key={optIdx}
                          onClick={() => !allPostAnswered && setPostAnswers((p) => ({ ...p, [question.id]: optIdx }))}
                          className={`topic-btn ${isSelected && !allPostAnswered ? 'selected' : ''}`}
                          style={{
                            padding: '8px 12px',
                            fontSize: '13px',
                            textAlign: 'left',
                            background: isCorrect ? 'var(--good-soft)' : isWrong ? 'var(--warn-soft)' : isSelected && !allPostAnswered ? 'var(--accent-soft)' : undefined,
                            borderColor: isCorrect ? 'var(--good)' : isWrong ? 'var(--warn)' : undefined,
                            cursor: allPostAnswered ? 'default' : 'pointer',
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

            {/* Score badge */}
            {allPostAnswered && (
              <div
                style={{
                  marginBottom: '24px',
                  padding: '10px 16px',
                  background: 'var(--paper-2)',
                  border: '1px solid var(--rule)',
                  borderRadius: '999px',
                  display: 'inline-flex',
                  gap: '8px',
                  alignItems: 'center',
                  fontSize: '13px',
                  color: 'var(--ink-2)',
                }}
              >
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: postScore === 5 ? 'var(--good)' : postScore >= 3 ? 'var(--accent)' : 'var(--warn)',
                    display: 'inline-block',
                  }}
                />
                Post-quiz: {postScore} / {POST_QUIZ.length} correct
              </div>
            )}

            {error && (
              <p style={{ color: 'var(--warn)', fontSize: '13px', marginBottom: '12px' }}>
                {error}
              </p>
            )}

            <div className="start-row" style={{ marginBottom: '14px' }}>
              <button
                className="start-btn primary"
                onClick={() => setStep('likert')}
                disabled={!allPostAnswered || loading}
                style={!allPostAnswered || loading ? { opacity: 0.5, cursor: 'not-allowed' } : { minWidth: '220px' }}
              >
                <span className="t">Continue to Experience Survey →</span>
                <span className="d">{!allPostAnswered ? 'Answer all questions first' : ''}</span>
              </button>
            </div>
          </>
        )}

        {step === 'likert' && (
          <>
            <p className="lead" style={{ marginBottom: '28px' }}>
              Rate your experience with the tutor on a scale of 1–5.
            </p>

            {/* Likert grid */}
            <div style={{ maxWidth: '600px', margin: '0 auto 28px', textAlign: 'left' }}>
              {EXPERIENCE_QUESTIONS.map((question, idx) => (
                <div key={idx} style={{ marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid var(--rule)' }}>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--ink)', marginBottom: '12px' }}>
                    Q{idx + 1}. {question}
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', color: 'var(--ink-3)', minWidth: '80px' }}>Disagree</span>
                    <div style={{ display: 'flex', gap: '6px', flex: 1, justifyContent: 'space-around' }}>
                      {[1, 2, 3, 4, 5].map((val) => {
                        const isSelected = ratings[idx] === val;
                        return (
                          <label key={val} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', cursor: 'pointer' }}>
                            <input
                              type="radio"
                              name={`q${idx}`}
                              value={val}
                              checked={isSelected}
                              onChange={() => setRatings((p) => ({ ...p, [idx]: val }))}
                              style={{ margin: '0 0 4px 0', cursor: 'pointer' }}
                            />
                            <span style={{ fontSize: '11px', color: 'var(--ink-3)' }}>{val}</span>
                          </label>
                        );
                      })}
                    </div>
                    <span style={{ fontSize: '11px', color: 'var(--ink-3)', minWidth: '80px', textAlign: 'right' }}>Agree</span>
                  </div>
                </div>
              ))}

              {/* Open feedback */}
              <div style={{ marginTop: '24px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--ink-3)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px' }}>
                  Additional feedback (optional)
                </label>
                <textarea
                  value={openFeedback}
                  onChange={(e) => setOpenFeedback(e.target.value)}
                  placeholder="Any other thoughts about the tutor or your learning experience?"
                  style={{
                    width: '100%',
                    minHeight: '100px',
                    padding: '10px 12px',
                    background: 'var(--paper-2)',
                    border: '1px solid var(--rule)',
                    borderRadius: 'var(--r)',
                    fontSize: '13px',
                    color: 'var(--ink)',
                    fontFamily: 'inherit',
                    outline: 'none',
                    boxSizing: 'border-box',
                    transition: 'border-color 120ms',
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent)';
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = 'var(--rule)';
                  }}
                />
              </div>
            </div>

            {error && (
              <p style={{ color: 'var(--warn)', fontSize: '13px', marginBottom: '12px' }}>
                {error}
              </p>
            )}

            <div className="start-row" style={{ gap: '10px', marginBottom: '14px' }}>
              <button
                className="start-btn"
                onClick={() => setStep('post_quiz')}
                disabled={loading}
                style={{ minWidth: '200px' }}
              >
                <span className="t">← Back</span>
              </button>
              <button
                className="start-btn primary"
                onClick={handleSubmitSurvey}
                disabled={!allRated || loading}
                style={!allRated || loading ? { opacity: 0.5, cursor: 'not-allowed' } : { minWidth: '220px' }}
              >
                <span className="t">{loading ? 'Submitting…' : 'Submit Survey'}</span>
                <span className="d">{!allRated ? 'Rate all questions first' : ''}</span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
