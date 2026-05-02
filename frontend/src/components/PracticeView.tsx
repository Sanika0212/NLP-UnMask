'use client';
import { useState } from 'react';
import { useSessionStore } from '@/lib/store';
import { TOPICS } from '@/lib/topics';

const FLASHCARDS: Record<string, { front: string; back: string }[]> = {
  brachial_plexus: [
    { front: 'What are the roots of the brachial plexus?', back: 'C5, C6, C7, C8, T1' },
    { front: "Erb's palsy affects which roots?", back: 'C5–C6: deltoid paralysis, biceps weakness ("waiter\'s tip" posture)' },
    { front: "Klumpke's palsy affects which roots?", back: 'C8–T1: intrinsic hand muscles, claw hand, Horner syndrome if T1 involved' },
    { front: 'What are the three trunks of the brachial plexus?', back: 'Upper (C5–C6), Middle (C7), Lower (C8–T1)' },
    { front: 'What are the three cords and what do they become?', back: 'Lateral → musculocutaneous + lateral median; Posterior → radial + axillary; Medial → ulnar + medial median' },
  ],
  rotator_cuff: [
    { front: 'What does SITS stand for?', back: 'Supraspinatus, Infraspinatus, Teres minor, Subscapularis' },
    { front: 'Which SITS muscle initiates abduction (0–15°)?', back: 'Supraspinatus' },
    { front: 'Which SITS muscle internally rotates the humerus?', back: 'Subscapularis' },
    { front: 'The "empty can" test assesses which muscle?', back: 'Supraspinatus (Jobe test: 90° abduction, 30° forward flex, thumb down)' },
    { front: 'Painful arc syndrome occurs between which degrees?', back: '60–120° of abduction — supraspinatus pinched under acromion' },
  ],
  peripheral_nerves: [
    { front: 'Which nerve innervates the deltoid?', back: 'Axillary nerve (C5–C6)' },
    { front: 'Wrist drop → which nerve injured?', back: 'Radial nerve (typically at humeral spiral groove)' },
    { front: 'Carpal tunnel syndrome compresses which nerve?', back: 'Median nerve — thenar wasting, loss of thumb opposition' },
    { front: 'Cubital tunnel syndrome compresses which nerve?', back: 'Ulnar nerve at the elbow — ring/pinky numbness, intrinsic weakness' },
    { front: 'Sensory innervation of the first web space (dorsum)?', back: 'Radial nerve (superficial sensory branch)' },
  ],
  shoulder_joint: [
    { front: 'Which type of joint is the glenohumeral joint?', back: 'Ball-and-socket (synovial) — most mobile joint in the body' },
    { front: 'What provides most glenohumeral stability?', back: 'Rotator cuff muscles + joint capsule (dynamic + static stabilizers)' },
    { front: 'Mechanism of anterior shoulder dislocation?', back: 'Abduction + external rotation — most common dislocation direction' },
    { front: 'AC joint separation grades — what separates?', back: 'Grade I–VI: acromioclavicular and coracoclavicular ligaments ruptured in sequence' },
    { front: 'What is a SLAP lesion?', back: 'Superior Labrum Anterior to Posterior tear — biceps anchor avulsion' },
  ],
  elbow_joint: [
    { front: 'Normal carrying angle of the elbow?', back: '5–15° valgus (cubitus valgus)' },
    { front: 'Which nerve is at risk in a medial epicondyle fracture?', back: 'Ulnar nerve — runs in the cubital tunnel behind the medial epicondyle' },
    { front: 'Tennis elbow affects which structure?', back: 'Lateral epicondyle — ECRB tendon origin (lateral epicondylitis)' },
    { front: "Golfer's elbow affects which structure?", back: 'Medial epicondyle — flexor-pronator mass origin (medial epicondylitis)' },
    { front: 'Posterior interosseous nerve injury causes?', back: 'Finger/thumb extension loss, wrist radial deviation (ECRL preserved)' },
  ],
  wrist_hand: [
    { front: 'Mnemonic for carpal bones proximal row?', back: 'Scaphoid, Lunate, Triquetrum, Pisiform — "She Likes The Pub"' },
    { front: 'Most commonly fractured carpal bone?', back: 'Scaphoid — risk of avascular necrosis if proximal pole involved' },
    { front: 'Thenar eminence muscles are innervated by?', back: 'Median nerve (LOAF: Lateral 2 lumbricals, Opponens pollicis, Abductor pollicis brevis, Flexor pollicis brevis)' },
    { front: 'Hypothenar muscles innervated by?', back: 'Ulnar nerve — abductor/flexor/opponens digiti minimi' },
    { front: 'Dupuytren\'s contracture affects which structures?', back: 'Palmar fascia — progressive flexion contracture of ring/little finger' },
  ],
  dermatomes: [
    { front: 'C5 dermatome covers which area?', back: 'Lateral shoulder/arm (regimental badge area)' },
    { front: 'C6 dermatome covers which area?', back: 'Lateral forearm, thumb, index finger' },
    { front: 'C7 dermatome covers which area?', back: 'Middle finger (dorsal and palmar)' },
    { front: 'C8 dermatome covers which area?', back: 'Ring and little finger, medial forearm' },
    { front: 'T1 dermatome covers which area?', back: 'Medial arm (axilla region)' },
  ],
  nerve_injuries: [
    { front: "Waiter's tip posture indicates?", back: "Erb's palsy (C5–C6): arm adducted, internally rotated, elbow extended, forearm pronated" },
    { front: 'Claw hand indicates which roots affected?', back: "Klumpke's palsy (C8–T1): intrinsics lost, MCP hyperextension, IP flexion" },
    { front: 'Saturday night palsy mechanism?', back: 'Radial nerve compression at spiral groove — wrist drop, no brachialis/biceps loss' },
    { front: 'Froment\'s sign tests which nerve?', back: 'Ulnar nerve — patient flexes IP joint to pinch (adductor pollicis lost)' },
    { front: 'Pope\'s blessing deformity indicates?', back: 'Anterior interosseous nerve palsy — FDP (index/middle) and FPL loss' },
  ],
  upper_limb_muscles: [
    { front: 'Primary shoulder abductors (0–15° vs 15–90°)?', back: 'Supraspinatus (0–15°), Deltoid (15–90°)' },
    { front: 'Scapular stabilizers (3 key muscles)?', back: 'Serratus anterior, Trapezius, Rhomboids' },
    { front: 'Serratus anterior palsy causes?', back: 'Winged scapula (long thoracic nerve, C5–C7)' },
    { front: 'Biceps brachii actions?', back: 'Elbow flexion, forearm supination (strongest in supinated position)' },
    { front: 'Which muscle pronates the forearm (main)?', back: 'Pronator teres (median nerve C6–C7)' },
  ],
  spinal_cord: [
    { front: 'Conus medullaris is at what vertebral level?', back: 'L1–L2 in adults' },
    { front: 'Cauda equina starts below?', back: 'L2 — nerve roots L2–S5 float in CSF' },
    { front: 'Central cord syndrome — what is preserved?', back: 'Sacral sensory sparing — arms weaker than legs (cervical somatotopy)' },
    { front: 'Brown-Séquard syndrome — ipsilateral losses?', back: 'Motor loss + dorsal column (proprioception, vibration)' },
    { front: 'Anterior cord syndrome spares what?', back: 'Dorsal columns — proprioception and vibration intact; motor + pain/temp lost' },
  ],
};

export default function PracticeView() {
  const currentTopic = useSessionStore((s) => s.currentTopic);
  const topicKey = (currentTopic && FLASHCARDS[currentTopic]) ? currentTopic : TOPICS[0].key;
  const cards = FLASHCARDS[topicKey] ?? [];

  const [cardIdx, setCardIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [selectedTopic, setSelectedTopic] = useState<string>(topicKey);

  const activeCards = FLASHCARDS[selectedTopic] ?? cards;
  const card = activeCards[cardIdx] ?? activeCards[0];
  const total = activeCards.length;

  const handleNext = () => {
    setFlipped(false);
    setCardIdx((i) => (i + 1) % total);
  };
  const handlePrev = () => {
    setFlipped(false);
    setCardIdx((i) => (i - 1 + total) % total);
  };
  const handleTopicChange = (key: string) => {
    setSelectedTopic(key);
    setCardIdx(0);
    setFlipped(false);
  };

  return (
    <div style={{ padding: '18px', overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Topic picker */}
      <div className="panel">
        <div className="panel-head">
          <h4>Flashcard Practice</h4>
          <span className="pmeta">{total} cards</span>
        </div>
        <div className="panel-body">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {TOPICS.map((t) => (
              <button
                key={t.key}
                className={`topic-btn${selectedTopic === t.key ? ' selected' : ''}`}
                onClick={() => handleTopicChange(t.key)}
                style={{ padding: '5px 10px', fontSize: '12px' }}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Flashcard */}
      {card && (
        <div
          onClick={() => setFlipped((f) => !f)}
          style={{
            cursor: 'pointer',
            minHeight: '180px',
            background: flipped ? 'var(--accent-soft)' : 'var(--paper-2)',
            border: `1px solid ${flipped ? 'var(--accent)' : 'var(--rule)'}`,
            borderRadius: 'var(--r)',
            padding: '28px 24px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            transition: 'background 200ms, border-color 200ms',
            userSelect: 'none',
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px' }}>
            {flipped ? 'Answer' : 'Question'} — {cardIdx + 1} / {total}
          </div>
          <div style={{ fontSize: '15px', color: 'var(--ink)', lineHeight: 1.6, fontWeight: flipped ? 400 : 600 }}>
            {flipped ? card.back : card.front}
          </div>
          {!flipped && (
            <div style={{ marginTop: '16px', fontSize: '12px', color: 'var(--ink-3)' }}>Tap to reveal →</div>
          )}
        </div>
      )}

      {/* Navigation */}
      <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', alignItems: 'center' }}>
        <button
          onClick={handlePrev}
          style={{ padding: '8px 16px', background: 'transparent', border: '1px solid var(--rule)', borderRadius: 'var(--r)', fontSize: '13px', color: 'var(--ink-2)', cursor: 'pointer' }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--ink)'; e.currentTarget.style.color = 'var(--ink)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--rule)'; e.currentTarget.style.color = 'var(--ink-2)'; }}
        >
          ← Prev
        </button>
        <span style={{ fontSize: '12px', color: 'var(--ink-3)', minWidth: '60px', textAlign: 'center' }}>{cardIdx + 1} / {total}</span>
        <button
          onClick={handleNext}
          style={{ padding: '8px 16px', background: 'transparent', border: '1px solid var(--rule)', borderRadius: 'var(--r)', fontSize: '13px', color: 'var(--ink-2)', cursor: 'pointer' }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--ink)'; e.currentTarget.style.color = 'var(--ink)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--rule)'; e.currentTarget.style.color = 'var(--ink-2)'; }}
        >
          Next →
        </button>
      </div>
    </div>
  );
}
