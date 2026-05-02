'use client';
import { useState, useEffect } from 'react';
import { useSessionStore } from '@/lib/store';
import { loadUser, saveQuizScore } from '@/lib/userStore';

interface MCQ {
  q: string;
  options: string[];
  correct: number;
  explanation: string;
}

const QUESTIONS: Record<string, MCQ[]> = {
  brachial_plexus: [
    {
      q: 'A 25yo presents with flaccid paralysis of shoulder abduction and elbow flexion after a motorcycle accident. Which nerve roots are most likely affected?',
      options: ['C5-C6', 'C7-C8', 'C8-T1', 'C5-T1'],
      correct: 0,
      explanation: 'C5-C6 injury (Erb\'s palsy) causes loss of deltoid (abduction) and biceps (flexion). "Waiter\'s tip" posture.',
    },
    {
      q: 'Which structure separates the anterior and posterior divisions of the brachial plexus?',
      options: ['Clavicle', 'Pectoralis minor', 'Scalene muscles', 'Subclavian artery'],
      correct: 0,
      explanation: 'The clavicle is the landmark — trunks are above, cords are below. Divisions are behind the clavicle.',
    },
    {
      q: 'Klumpke\'s palsy affects which muscles primarily?',
      options: ['Deltoid and biceps', 'Intrinsic hand muscles', 'Wrist extensors', 'Shoulder rotators'],
      correct: 1,
      explanation: 'C8-T1 (lower trunk) injury causes intrinsic hand muscle weakness — "claw hand" and Horner syndrome if T1 sympathetics involved.',
    },
  ],
  rotator_cuff: [
    {
      q: 'A 55yo OT patient cannot initiate arm abduction past 15°. Which muscle is most likely torn?',
      options: ['Infraspinatus', 'Supraspinatus', 'Subscapularis', 'Teres minor'],
      correct: 1,
      explanation: 'Supraspinatus initiates the first 15° of abduction. Complete tear = cannot start the motion.',
    },
    {
      q: 'The "empty can" test specifically assesses which muscle?',
      options: ['Infraspinatus', 'Teres minor', 'Supraspinatus', 'Subscapularis'],
      correct: 2,
      explanation: 'Empty can (Jobe test) — arm at 90° abduction, 30° forward flexion, thumb down — isolates supraspinatus.',
    },
    {
      q: 'Internal rotation deficit and pain on resisted external rotation suggests which muscle injury?',
      options: ['Supraspinatus', 'Subscapularis', 'Infraspinatus', 'Teres major'],
      correct: 2,
      explanation: 'Infraspinatus is the primary external rotator. Injury causes painful/weak external rotation and internal rotation deficit.',
    },
  ],
  elbow_joint: [
    {
      q: 'A child presents with medial elbow pain after a valgus stress injury. What is the most likely diagnosis?',
      options: ['Medial epicondyle avulsion', 'Lateral epicondylitis', 'Cubital tunnel syndrome', 'Radial head fracture'],
      correct: 0,
      explanation: 'Valgus stress on immature skeleton → medial epicondyle apophysis avulsion — the MCL and flexor-pronator attach here.',
    },
    {
      q: 'Which nerve is at risk in a lateral epicondyle fracture?',
      options: ['Ulnar nerve', 'Median nerve', 'Radial nerve (posterior interosseous)', 'Musculocutaneous'],
      correct: 2,
      explanation: 'The posterior interosseous nerve (deep branch of radial) winds around the radial head and can be compressed in lateral fractures.',
    },
    {
      q: 'Normal elbow carrying angle in adults is:',
      options: ['0–5° valgus', '5–15° valgus', '15–25° valgus', '5–10° varus'],
      correct: 1,
      explanation: '5–15° valgus (cubitus valgus) is normal. Higher in females (~13°) than males (~11°). >15° = pathological valgus.',
    },
  ],
  peripheral_nerves: [
    {
      q: 'Which nerve innervates the deltoid?',
      options: ['Axillary nerve', 'Radial nerve', 'Musculocutaneous', 'Suprascapular'],
      correct: 0,
      explanation: 'Axillary nerve (C5-C6) from posterior cord innervates deltoid and teres minor.',
    },
    {
      q: 'Wrist drop is a classic sign of which nerve injury?',
      options: ['Median nerve', 'Ulnar nerve', 'Radial nerve', 'Musculocutaneous'],
      correct: 2,
      explanation: 'Radial nerve palsy causes wrist drop — loss of wrist extensors. Posterior interosseous nerve branch affected.',
    },
    {
      q: 'Which nerve provides sensory innervation to the first web space (dorsal)?',
      options: ['Median nerve', 'Ulnar nerve', 'Radial nerve', 'Musculocutaneous'],
      correct: 2,
      explanation: 'Radial nerve (superficial sensory branch) supplies the dorsal first web space and dorsal thumb/index finger.',
    },
  ],
  shoulder_joint: [
    {
      q: 'The glenohumeral joint is stabilized primarily by:',
      options: ['Ligaments alone', 'Rotator cuff muscles and capsule', 'Deltoid', 'Scapular positioning'],
      correct: 1,
      explanation: 'Rotator cuff (SITS) and joint capsule provide dynamic and static stability. Deltoid assists in movement, not primary stabilizer.',
    },
    {
      q: 'Anterior shoulder dislocation typically occurs with:',
      options: ['Excessive adduction', 'Excessive abduction and external rotation', 'Excessive internal rotation', 'Excessive flexion'],
      correct: 1,
      explanation: 'Abduction + external rotation (throwing position) is the mechanism. Posterior dislocation is rare but associated with seizures.',
    },
    {
      q: 'The acromioclavicular joint primarily allows:',
      options: ['Horizontal abduction', 'Scapular rotation', 'Elbow flexion', 'Wrist pronation'],
      correct: 1,
      explanation: 'AC joint allows scapular rotation and positioning. Critical for full overhead reach. Distal clavicle instability affects this.',
    },
  ],
};

const DEFAULT_KEY = 'brachial_plexus';

export default function AssessView() {
  const currentTopic = useSessionStore((s) => s.currentTopic) || DEFAULT_KEY;
  const studentName = useSessionStore((s) => s.studentName);
  const questions = QUESTIONS[currentTopic as keyof typeof QUESTIONS] || QUESTIONS[DEFAULT_KEY];

  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [submitted, setSubmitted] = useState(false);
  const [history, setHistory] = useState<number[]>([]);

  useEffect(() => {
    const userData = loadUser(studentName);
    setHistory(userData.quizScores[currentTopic] ?? []);
  }, [studentName, currentTopic]);

  const allAnswered = questions.length > 0 && Object.keys(answers).length === questions.length;
  const canSubmit = allAnswered && !submitted;

  const handleSelectOption = (qIdx: number, optIdx: number) => {
    if (!submitted) setAnswers((p) => ({ ...p, [qIdx]: optIdx }));
  };

  const handleSubmit = () => {
    if (!canSubmit) return;
    setSubmitted(true);
    const s = questions.filter((q, idx) => answers[idx] === q.correct).length;
    saveQuizScore(studentName, currentTopic, s, questions.length);
    setHistory((h) => [...h, Math.round((s / questions.length) * 100)]);
  };

  const score = submitted
    ? questions.filter((q, idx) => answers[idx] === q.correct).length
    : 0;
  const bestPct = history.length > 0 ? Math.max(...history) : null;

  return (
    <div style={{ padding: '18px', overflow: 'auto', height: '100%' }}>
      <div className="panel">
        <div className="panel-head">
          <h4>Self-Assessment Quiz</h4>
          <span className="pmeta">
            {bestPct !== null ? `Best: ${bestPct}% · ${history.length} attempt${history.length !== 1 ? 's' : ''}` : 'NBCOT-style'}
          </span>
        </div>
      </div>

      {/* Questions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '20px' }}>
        {questions.map((question, qIdx) => {
          const isAnswered = qIdx in answers;
          const selectedOpt = answers[qIdx];
          const isCorrect = submitted && selectedOpt === question.correct;
          const isWrong = submitted && isAnswered && selectedOpt !== question.correct;

          return (
            <div key={qIdx} className="panel">
              <div className="panel-body">
                <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--ink)', marginBottom: '12px', lineHeight: 1.5 }}>
                  <span style={{ color: 'var(--accent)' }}>Q{qIdx + 1}.</span> {question.q}
                </div>

                {/* Options */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {question.options.map((opt, optIdx) => {
                    const selected = selectedOpt === optIdx;
                    const correct = isCorrect && optIdx === question.correct;
                    const wrong = isWrong && selected;
                    const unselectedCorrect = submitted && optIdx === question.correct && !selected;

                    return (
                      <button
                        key={optIdx}
                        onClick={() => handleSelectOption(qIdx, optIdx)}
                        className="topic-btn"
                        disabled={submitted}
                        style={{
                          padding: '10px 12px',
                          fontSize: '13px',
                          textAlign: 'left',
                          background: correct
                            ? 'var(--good-soft)'
                            : wrong
                              ? 'var(--warn-soft)'
                              : unselectedCorrect
                                ? 'var(--good-soft)'
                                : selected && !submitted
                                  ? 'var(--accent-soft)'
                                  : undefined,
                          borderColor: correct || unselectedCorrect ? 'var(--good)' : wrong ? 'var(--warn)' : undefined,
                          cursor: submitted ? 'default' : 'pointer',
                          opacity: submitted && !selected && optIdx !== question.correct ? 0.5 : 1,
                        }}
                      >
                        <span style={{ marginRight: '8px', color: 'var(--ink-3)', fontWeight: '500' }}>
                          {String.fromCharCode(65 + optIdx)}.
                        </span>
                        {opt}
                        {correct && <span style={{ marginLeft: '8px', color: 'var(--good)' }}>✓</span>}
                        {unselectedCorrect && submitted && (
                          <span style={{ marginLeft: '8px', color: 'var(--good)', fontSize: '12px' }}>← correct</span>
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* Explanation shown after submit */}
                {submitted && (isCorrect || isWrong) && (
                  <blockquote
                    style={{
                      marginTop: '12px',
                      paddingLeft: '12px',
                      borderLeft: `3px solid ${isCorrect ? 'var(--good)' : 'var(--warn)'}`,
                      color: 'var(--ink-2)',
                      fontSize: '13px',
                      lineHeight: 1.5,
                      margin: '12px 0 0 0',
                    }}
                  >
                    {question.explanation}
                  </blockquote>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Score badge */}
      {submitted && (
        <div
          style={{
            marginBottom: '16px',
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
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: score === questions.length ? 'var(--good)' : score > questions.length / 2 ? 'var(--accent)' : 'var(--warn)',
              display: 'inline-block',
            }}
          />
          Score: {score} / {questions.length} correct
        </div>
      )}

      {/* Submit button */}
      {!submitted && (
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="start-btn primary"
          style={{
            marginTop: '12px',
            minWidth: '140px',
            opacity: !canSubmit ? 0.5 : 1,
            cursor: !canSubmit ? 'not-allowed' : 'pointer',
          }}
        >
          <span className="t">Submit Answers</span>
          <span className="d">{allAnswered ? 'All answered' : `${questions.length - Object.keys(answers).length} remaining`}</span>
        </button>
      )}

      {/* Reset button after submit */}
      {submitted && (
        <button
          onClick={() => {
            setAnswers({});
            setSubmitted(false);
            const userData = loadUser(studentName);
            setHistory(userData.quizScores[currentTopic] ?? []);
          }}
          style={{
            marginTop: '12px',
            padding: '8px 14px',
            background: 'transparent',
            border: '1px solid var(--rule)',
            borderRadius: 'var(--r)',
            fontSize: '13px',
            color: 'var(--ink-3)',
            cursor: 'pointer',
            transition: 'all 120ms',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--ink)';
            e.currentTarget.style.color = 'var(--ink)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--rule)';
            e.currentTarget.style.color = 'var(--ink-3)';
          }}
        >
          Try Again
        </button>
      )}
    </div>
  );
}
