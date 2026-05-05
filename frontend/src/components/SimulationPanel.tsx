'use client';
import { useRef, useState, useCallback } from 'react';
import { useSessionStore } from '@/lib/store';
import { TOPICS } from '@/lib/topics';
import type { LearningMode } from '@/lib/types';

/* ─── Types ───────────────────────────────────────────────────────────────── */
type Tag = 'correct' | 'wrong' | 'idk' | 'diagram' | 'alt' | 'end';
interface Step { label: string; msg: string; tag: Tag }

/* ─── Shared non-content steps ────────────────────────────────────────────── */
const COMMON_END: Step[] = [
  { label: 'Diagram: explicit request',   msg: 'Show me a diagram of that',         tag: 'diagram' },
  { label: 'Diagram: alternate request',  msg: 'Can I see a different diagram?',    tag: 'alt'     },
  { label: 'IDK + explain request',       msg: "I don't know — can you explain?",   tag: 'idk'     },
  { label: 'End session',                 msg: 'end session',                        tag: 'end'     },
];

/* ─── Per-topic scripts ───────────────────────────────────────────────────── */
// Each topic has exactly 4 diagnostic steps (correct/idk/wrong/correct),
// 2 wrong tutoring steps, 3 correct tutoring steps, 2 assessment steps,
// plus the 4 shared steps injected from COMMON_END.
const TOPIC_SCRIPTS: Record<string, Step[]> = {

// Each topic: 4 diag + 2 tutoring wrongs + 5 tutoring corrects + 2 assessment = 13 steps.
// buildScript() inserts diagram/alt/idk after the 6th step (2nd wrong), before the corrects.
// 5 consecutive corrects satisfies consecutive_correct_for_advance = 5.

  brachial_plexus: [
    { label: 'Diag Q1 – levels (correct)',        msg: 'C5, C6, C7, C8 and T1',                                                      tag: 'correct' },
    { label: 'Diag Q2 – branches (IDK)',          msg: "I don't know all five terminal branches",                                      tag: 'idk'     },
    { label: 'Diag Q3 – trunks (wrong)',          msg: 'There are two trunks — upper and lower',                                       tag: 'wrong'   },
    { label: 'Diag Q4 – medial cord (correct)',   msg: 'Anterior divisions of the inferior trunk form the medial cord, mainly the ulnar nerve', tag: 'correct' },
    { label: 'Tutoring wrong #1',                 msg: 'I think the lateral cord gives rise to the radial nerve',                     tag: 'wrong'   },
    { label: 'Tutoring wrong #2 → auto-diagram',  msg: 'Maybe all anterior divisions combine into just the median nerve?',            tag: 'wrong'   },
    { label: 'Tutoring correct #1',               msg: 'The posterior cord gives rise to the axillary and radial nerves',             tag: 'correct' },
    { label: 'Tutoring correct #2',               msg: 'C5 and C6 roots join to form the superior trunk',                            tag: 'correct' },
    { label: 'Tutoring correct #3',               msg: 'Both medial and lateral cords contribute to the median nerve',                tag: 'correct' },
    { label: 'Tutoring correct #4',               msg: 'The musculocutaneous nerve arises from the lateral cord',                     tag: 'correct' },
    { label: 'Tutoring correct #5',               msg: 'C8 and T1 form the inferior trunk which splits into anterior and posterior divisions', tag: 'correct' },
    { label: 'Assessment wrong',                  msg: "The injury must be at T3 based on the patient's symptoms",                    tag: 'wrong'   },
    { label: 'Assessment correct',                msg: "Erb's palsy — C5 C6 injury causing waiter's tip posture",                     tag: 'correct' },
  ],

  rotator_cuff: [
    { label: 'Diag Q1 – SITS (correct)',          msg: 'Supraspinatus, infraspinatus, teres minor and subscapularis',                 tag: 'correct' },
    { label: 'Diag Q2 – nerve (IDK)',             msg: "I'm not sure which nerve innervates the supraspinatus",                       tag: 'idk'     },
    { label: 'Diag Q3 – internal rotation (wrong)', msg: 'The deltoid muscle handles internal rotation',                             tag: 'wrong'   },
    { label: 'Diag Q4 – critical zone (correct)', msg: 'The avascular zone 1 cm from insertion is prone to ischemic tears',          tag: 'correct' },
    { label: 'Tutoring wrong #1',                 msg: 'I think subscapularis causes external rotation',                             tag: 'wrong'   },
    { label: 'Tutoring wrong #2 → auto-diagram',  msg: 'Maybe supraspinatus handles all shoulder abduction?',                        tag: 'wrong'   },
    { label: 'Tutoring correct #1',               msg: 'Subscapularis on the anterior scapula causes internal rotation',             tag: 'correct' },
    { label: 'Tutoring correct #2',               msg: 'Supraspinatus initiates abduction 0 to 15 degrees via the suprascapular nerve', tag: 'correct' },
    { label: 'Tutoring correct #3',               msg: 'Both supraspinatus and infraspinatus are innervated by the suprascapular nerve', tag: 'correct' },
    { label: 'Tutoring correct #4',               msg: 'Infraspinatus causes external rotation and is tested with the external rotation lag sign', tag: 'correct' },
    { label: 'Tutoring correct #5',               msg: 'The empty-can test assesses supraspinatus integrity in the scapular plane',  tag: 'correct' },
    { label: 'Assessment wrong',                  msg: 'The biceps tendon is torn causing the painful arc',                          tag: 'wrong'   },
    { label: 'Assessment correct',                msg: 'Full thickness supraspinatus tear causes a painful arc from 60 to 120 degrees', tag: 'correct' },
  ],

  peripheral_nerves: [
    { label: 'Diag Q1 – axillary (correct)',      msg: 'The axillary nerve innervates the deltoid at C5 and C6',                     tag: 'correct' },
    { label: 'Diag Q2 – radial deficits (IDK)',   msg: "I'm not sure about all the radial nerve deficits",                           tag: 'idk'     },
    { label: 'Diag Q3 – flat thenar (wrong)',     msg: 'That must be the ulnar nerve causing the flat thenar eminence',              tag: 'wrong'   },
    { label: 'Diag Q4 – ulnar function (correct)',msg: 'The ulnar nerve controls the interossei and lumbricals causing claw hand when injured', tag: 'correct' },
    { label: 'Tutoring wrong #1',                 msg: 'I think the radial nerve controls finger flexion',                           tag: 'wrong'   },
    { label: 'Tutoring wrong #2 → auto-diagram',  msg: 'Maybe the median nerve innervates all intrinsic hand muscles?',              tag: 'wrong'   },
    { label: 'Tutoring correct #1',               msg: 'The radial nerve innervates all wrist and finger extensors',                 tag: 'correct' },
    { label: 'Tutoring correct #2',               msg: 'The axillary nerve passes through the quadrilateral space, injured in shoulder dislocation', tag: 'correct' },
    { label: 'Tutoring correct #3',               msg: 'The median nerve provides sensation to the lateral three and a half fingers', tag: 'correct' },
    { label: 'Tutoring correct #4',               msg: 'The ulnar nerve enters the hand via Guyon\'s canal lateral to the pisiform', tag: 'correct' },
    { label: 'Tutoring correct #5',               msg: 'The musculocutaneous nerve pierces coracobrachialis and becomes the lateral cutaneous nerve', tag: 'correct' },
    { label: 'Assessment wrong',                  msg: 'Wrist drop is caused by ulnar nerve injury at the elbow',                   tag: 'wrong'   },
    { label: 'Assessment correct',                msg: 'Wrist drop is caused by radial nerve injury at the spiral groove',           tag: 'correct' },
  ],

  shoulder_joint: [
    { label: 'Diag Q1 – glenohumeral (correct)',  msg: 'Ball and socket stabilised by the labrum, rotator cuff, and glenohumeral ligaments', tag: 'correct' },
    { label: 'Diag Q2 – AC joint (IDK)',          msg: "I don't know the clinical significance of the AC joint",                    tag: 'idk'     },
    { label: 'Diag Q3 – labrum (wrong)',          msg: 'The labrum is just a cartilage cushion with no role in stability',          tag: 'wrong'   },
    { label: 'Diag Q4 – bursa (correct)',         msg: 'The subacromial bursa is most commonly inflamed in impingement syndrome',   tag: 'correct' },
    { label: 'Tutoring wrong #1',                 msg: 'I think a Bankart lesion is a rotator cuff tear',                          tag: 'wrong'   },
    { label: 'Tutoring wrong #2 → auto-diagram',  msg: 'Maybe the AC joint is the same as the glenohumeral joint?',                tag: 'wrong'   },
    { label: 'Tutoring correct #1',               msg: 'A Bankart lesion is a tear of the anterior glenoid labrum after anterior dislocation', tag: 'correct' },
    { label: 'Tutoring correct #2',               msg: 'The AC joint is between the acromion and clavicle and is injured in falls on the shoulder', tag: 'correct' },
    { label: 'Tutoring correct #3',               msg: 'The glenohumeral joint relies on the rotator cuff for dynamic stability', tag: 'correct' },
    { label: 'Tutoring correct #4',               msg: 'A Hill-Sachs lesion is a compression fracture of the humeral head after anterior dislocation', tag: 'correct' },
    { label: 'Tutoring correct #5',               msg: 'The inferior glenohumeral ligament is the primary restraint against anterior instability', tag: 'correct' },
    { label: 'Assessment wrong',                  msg: 'Shoulder impingement is caused by subscapularis tearing',                  tag: 'wrong'   },
    { label: 'Assessment correct',                msg: 'Neer impingement involves the supraspinatus under the coracoacromial arch during elevation', tag: 'correct' },
  ],

  elbow_joint: [
    { label: 'Diag Q1 – carrying angle (correct)',msg: 'The carrying angle is the valgus angle; cubitus valgus increases it',       tag: 'correct' },
    { label: 'Diag Q2 – ulnar at elbow (IDK)',    msg: "I know the ulnar nerve passes there but not its exact location",            tag: 'idk'     },
    { label: 'Diag Q3 – MCL complex (wrong)',     msg: 'The medial collateral ligament is a single cord-like structure',            tag: 'wrong'   },
    { label: 'Diag Q4 – pitcher UCL (correct)',   msg: 'The UCL is injured by valgus stress and may need Tommy John surgery',      tag: 'correct' },
    { label: 'Tutoring wrong #1',                 msg: 'I think the radial nerve passes through the cubital tunnel',                tag: 'wrong'   },
    { label: 'Tutoring wrong #2 → auto-diagram',  msg: 'Maybe cubitus varus increases the carrying angle?',                        tag: 'wrong'   },
    { label: 'Tutoring correct #1',               msg: 'The ulnar nerve passes posterior to the medial epicondyle through the cubital tunnel', tag: 'correct' },
    { label: 'Tutoring correct #2',               msg: 'Cubitus varus decreases the carrying angle, typically after supracondylar fracture', tag: 'correct' },
    { label: 'Tutoring correct #3',               msg: 'Tardy ulnar nerve palsy can result from chronic cubitus valgus compression', tag: 'correct' },
    { label: 'Tutoring correct #4',               msg: 'The anterior bundle of the UCL is the primary restraint against valgus stress', tag: 'correct' },
    { label: 'Tutoring correct #5',               msg: 'The radial nerve divides into superficial and deep posterior interosseous branches at the elbow', tag: 'correct' },
    { label: 'Assessment wrong',                  msg: 'Medial epicondylitis is caused by radial nerve entrapment',                 tag: 'wrong'   },
    { label: 'Assessment correct',                msg: "Golfer's elbow involves the flexor-pronator mass origin at the medial epicondyle", tag: 'correct' },
  ],

  wrist_hand: [
    { label: 'Diag Q1 – carpal rows (correct)',   msg: 'Proximal: scaphoid, lunate, triquetrum, pisiform. Distal: trapezium, trapezoid, capitate, hamate', tag: 'correct' },
    { label: 'Diag Q2 – thenar muscles (IDK)',    msg: "I don't know all the thenar muscles by name",                               tag: 'idk'     },
    { label: 'Diag Q3 – carpal tunnel (wrong)',   msg: 'Carpal tunnel syndrome compresses the ulnar nerve',                        tag: 'wrong'   },
    { label: 'Diag Q4 – snuffbox (correct)',      msg: 'The anatomical snuffbox tenderness indicates possible scaphoid fracture with AVN risk', tag: 'correct' },
    { label: 'Tutoring wrong #1',                 msg: 'I think the hypothenar muscles are innervated by the median nerve',        tag: 'wrong'   },
    { label: 'Tutoring wrong #2 → auto-diagram',  msg: 'Maybe the opponens pollicis is supplied by the ulnar nerve?',             tag: 'wrong'   },
    { label: 'Tutoring correct #1',               msg: 'The thenar muscles — abductor pollicis brevis, opponens, flexor pollicis brevis — are innervated by the median nerve', tag: 'correct' },
    { label: 'Tutoring correct #2',               msg: 'The hypothenar muscles are supplied by the deep branch of the ulnar nerve', tag: 'correct' },
    { label: 'Tutoring correct #3',               msg: "Hook of hamate fractures compress the ulnar nerve in Guyon's canal",       tag: 'correct' },
    { label: 'Tutoring correct #4',               msg: 'The lumbricals flex the MCP joints and extend the IP joints of the fingers', tag: 'correct' },
    { label: 'Tutoring correct #5',               msg: 'Interossei abduct and adduct fingers, plus flex MCPs — supplied by ulnar nerve', tag: 'correct' },
    { label: 'Assessment wrong',                  msg: 'Scaphoid fractures always show up clearly on X-ray immediately',           tag: 'wrong'   },
    { label: 'Assessment correct',                msg: 'Scaphoid fractures are X-ray occult initially; MRI is needed and proximal pole fractures have the highest AVN risk', tag: 'correct' },
  ],

  dermatomes: [
    { label: 'Diag Q1 – C6/C8 (correct)',         msg: 'C6 supplies the thumb and index finger, C8 supplies the little finger',    tag: 'correct' },
    { label: 'Diag Q2 – lateral forearm (IDK)',   msg: "I'm not sure which level covers the lateral forearm",                      tag: 'idk'     },
    { label: 'Diag Q3 – nipple (wrong)',          msg: 'The nipple line is at T2',                                                 tag: 'wrong'   },
    { label: 'Diag Q4 – medial arm (correct)',    msg: 'T1 and C8 cover the medial arm and forearm via the medial cutaneous nerves', tag: 'correct' },
    { label: 'Tutoring wrong #1',                 msg: 'I think C7 supplies the thumb',                                            tag: 'wrong'   },
    { label: 'Tutoring wrong #2 → auto-diagram',  msg: 'Maybe dermatomes and peripheral nerve territories are the same thing?',    tag: 'wrong'   },
    { label: 'Tutoring correct #1',               msg: 'C6 covers the lateral forearm and thumb via the musculocutaneous nerve distribution', tag: 'correct' },
    { label: 'Tutoring correct #2',               msg: 'Dermatomes and peripheral nerve territories differ because one nerve can carry multiple root levels', tag: 'correct' },
    { label: 'Tutoring correct #3',               msg: 'C5 covers the regimental badge area on the lateral shoulder',             tag: 'correct' },
    { label: 'Tutoring correct #4',               msg: 'T4 covers the nipple line and is a key landmark in spinal injury assessment', tag: 'correct' },
    { label: 'Tutoring correct #5',               msg: 'C7 supplies the middle finger and posterior forearm',                     tag: 'correct' },
    { label: 'Assessment wrong',                  msg: 'A C6 disc prolapse would cause numbness in the little finger',             tag: 'wrong'   },
    { label: 'Assessment correct',                msg: 'C6 radiculopathy causes thumb and index finger numbness with biceps reflex loss', tag: 'correct' },
  ],

  nerve_injuries: [
    { label: 'Diag Q1 – Saturday night palsy (correct)', msg: 'Radial nerve compressed in the spiral groove causing wrist drop',  tag: 'correct' },
    { label: 'Diag Q2 – Erb\'s posture (IDK)',    msg: "I know it's upper roots but I can't recall the exact posture",            tag: 'idk'     },
    { label: 'Diag Q3 – Klumpke\'s (wrong)',      msg: "Klumpke's palsy is a C5 C6 injury with waiter's tip posture",             tag: 'wrong'   },
    { label: 'Diag Q4 – ulnar claw level (correct)', msg: 'Distal ulnar injury causes claw hand because ring and little finger lumbricals are denervated', tag: 'correct' },
    { label: 'Tutoring wrong #1',                 msg: "I think Erb's palsy causes claw hand",                                    tag: 'wrong'   },
    { label: 'Tutoring wrong #2 → auto-diagram',  msg: 'Maybe a proximal ulnar injury causes worse clawing than a distal one?',  tag: 'wrong'   },
    { label: 'Tutoring correct #1',               msg: "Erb's palsy injures C5 C6 causing waiter's tip — adduction, internal rotation, extended elbow", tag: 'correct' },
    { label: 'Tutoring correct #2',               msg: 'Proximal ulnar injury causes less clawing because FDP also fails — the ulnar paradox', tag: 'correct' },
    { label: 'Tutoring correct #3',               msg: "Klumpke's palsy injures C8 T1 causing intrinsic weakness and Horner syndrome if T1 is affected", tag: 'correct' },
    { label: 'Tutoring correct #4',               msg: 'Anterior interosseous nerve palsy causes loss of precision pinch — OK sign test is positive', tag: 'correct' },
    { label: 'Tutoring correct #5',               msg: 'Long thoracic nerve injury causes winging of the scapula due to serratus anterior paralysis', tag: 'correct' },
    { label: 'Assessment wrong',                  msg: 'Wrist drop in Saturday night palsy is caused by median nerve compression', tag: 'wrong'   },
    { label: 'Assessment correct',                msg: 'Radial nerve injury at the spiral groove causes wrist drop with sensory loss over the dorsum of the hand', tag: 'correct' },
  ],

  upper_limb_muscles: [
    { label: 'Diag Q1 – biceps (correct)',        msg: 'Biceps brachii is innervated by the musculocutaneous nerve C5 C6, causing flexion and supination', tag: 'correct' },
    { label: 'Diag Q2 – triceps level (IDK)',     msg: "I know the triceps extends the elbow but I'm not sure of the spinal level", tag: 'idk'   },
    { label: 'Diag Q3 – FDP (wrong)',             msg: 'The flexor digitorum profundus is entirely innervated by the median nerve', tag: 'wrong'  },
    { label: 'Diag Q4 – abduction (correct)',     msg: 'Supraspinatus 0 to 15 degrees, then deltoid 15 to 90 degrees via the axillary nerve', tag: 'correct' },
    { label: 'Tutoring wrong #1',                 msg: 'I think brachioradialis is innervated by the ulnar nerve',                 tag: 'wrong'   },
    { label: 'Tutoring wrong #2 → auto-diagram',  msg: 'Maybe the triceps is innervated by the musculocutaneous nerve?',          tag: 'wrong'   },
    { label: 'Tutoring correct #1',               msg: 'Brachioradialis is innervated by the radial nerve despite being on the lateral forearm', tag: 'correct' },
    { label: 'Tutoring correct #2',               msg: 'Triceps is innervated by the radial nerve at C7 and is the sole elbow extensor', tag: 'correct' },
    { label: 'Tutoring correct #3',               msg: 'FDP for index and middle is anterior interosseous nerve; ring and little is ulnar nerve', tag: 'correct' },
    { label: 'Tutoring correct #4',               msg: 'Brachialis is a pure elbow flexor innervated by musculocutaneous and a small radial branch', tag: 'correct' },
    { label: 'Tutoring correct #5',               msg: 'Pronator teres and pronator quadratus both cause forearm pronation, innervated by the median nerve', tag: 'correct' },
    { label: 'Assessment wrong',                  msg: 'Loss of supination always indicates a median nerve injury',                tag: 'wrong'   },
    { label: 'Assessment correct',                msg: 'Loss of supination points to musculocutaneous or posterior interosseous nerve injury depending on the level', tag: 'correct' },
  ],

  spinal_cord: [
    { label: 'Diag Q1 – conus (correct)',         msg: 'The spinal cord ends at L1 or L2; the cauda equina continues below',       tag: 'correct' },
    { label: 'Diag Q2 – central canal (IDK)',     msg: "I'm not sure about the central canal versus subarachnoid space",           tag: 'idk'     },
    { label: 'Diag Q3 – Brown-Séquard (wrong)',   msg: 'Brown-Séquard causes bilateral motor loss below the injury',               tag: 'wrong'   },
    { label: 'Diag Q4 – somatotopy (correct)',    msg: 'Sacral fibres are most lateral and cervical most medial in the corticospinal tract', tag: 'correct' },
    { label: 'Tutoring wrong #1',                 msg: 'I think the dorsal columns carry pain and temperature',                    tag: 'wrong'   },
    { label: 'Tutoring wrong #2 → auto-diagram',  msg: 'Maybe the spinothalamic tract decussates above the level of entry?',      tag: 'wrong'   },
    { label: 'Tutoring correct #1',               msg: 'Dorsal columns carry proprioception and fine touch; spinothalamic carries pain and temperature', tag: 'correct' },
    { label: 'Tutoring correct #2',               msg: 'The spinothalamic tract crosses within 1 to 2 segments of entry in the anterior commissure', tag: 'correct' },
    { label: 'Tutoring correct #3',               msg: 'Brown-Séquard causes ipsilateral motor and dorsal column loss with contralateral pain and temperature loss', tag: 'correct' },
    { label: 'Tutoring correct #4',               msg: 'Anterior cord syndrome spares dorsal column function but destroys motor and pain pathways', tag: 'correct' },
    { label: 'Tutoring correct #5',               msg: 'Posterior cord syndrome is rare — only vibration and proprioception are lost below the lesion', tag: 'correct' },
    { label: 'Assessment wrong',                  msg: 'Central cord syndrome primarily affects the lower limbs more than upper limbs', tag: 'wrong' },
    { label: 'Assessment correct',                msg: 'Central cord syndrome causes greater upper limb weakness because cervical fibres run most centrally', tag: 'correct' },
  ],
};

/* ─── Assemble full script for a given topic ─────────────────────────────── */
function buildScript(topic: string): Step[] {
  const base = TOPIC_SCRIPTS[topic] ?? TOPIC_SCRIPTS['brachial_plexus'];
  // Insert diagram/alt/idk steps after the 2nd wrong tutoring step (index 5 = 4 diag + 2 wrong)
  const pre    = base.slice(0, 6);   // 4 rapport + 2 tutoring wrongs
  const post   = base.slice(6);      // 3 corrects + 2 assessment
  return [
    ...pre,
    COMMON_END[0], // show me diagram
    COMMON_END[1], // different diagram
    COMMON_END[2], // IDK + explain
    ...post,
    COMMON_END[3], // end session
  ];
}

/* ─── Badge meta ─────────────────────────────────────────────────────────── */
const TAG_META: Record<Tag, { bg: string; color: string; label: string }> = {
  correct: { bg: '#d1fae5', color: '#065f46', label: '✓ correct'   },
  wrong:   { bg: '#fee2e2', color: '#991b1b', label: '✗ wrong'     },
  idk:     { bg: '#fef3c7', color: '#92400e', label: '? idk'       },
  diagram: { bg: '#dbeafe', color: '#1e40af', label: '🖼 diagram'  },
  alt:     { bg: '#ede9fe', color: '#5b21b6', label: '🔄 alt-diag' },
  end:     { bg: '#f1f5f9', color: '#475569', label: '⏹ end'       },
};

const REPLY_TIMEOUT_MS = 60_000;

/* ─── Component ──────────────────────────────────────────────────────────── */
export default function SimulationPanel() {
  const [open, setOpen]       = useState(false);
  const [running, setRunning] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [step, setStep]       = useState(-1);
  const [done, setDone]       = useState(false);
  const [speed, setSpeed]     = useState(2);
  const [typingSpeed, setTypingSpeed] = useState(38); // ms per character
  const [startDelay, setStartDelay]   = useState(5);  // seconds before first message
  const [topic, setTopic]     = useState('brachial_plexus');
  const [mode, setMode]       = useState<LearningMode>('visual');
  const [log, setLog]         = useState<{ idx: number; ok: boolean; note: string }[]>([]);
  const [setupStatus, setSetupStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');

  const abortRef = useRef(false);
  const phase    = useSessionStore((s) => s.phase);
  const script   = buildScript(topic);

  const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

  const waitReply = useCallback(() => new Promise<void>((resolve) => {
    const start = Date.now();
    const id = setInterval(() => {
      if (!useSessionStore.getState().isThinking || Date.now() - start > REPLY_TIMEOUT_MS) {
        clearInterval(id);
        resolve();
      }
    }, 200);
  }), []);

  /* ── type message into Composer textarea, then send ─────────────────────── */
  const typeAndSend = useCallback(async (msg: string, forceCorrect = false) => {
    const store = useSessionStore.getState();
    // Type characters one by one
    for (let i = 1; i <= msg.length; i++) {
      if (abortRef.current) return;
      store.setComposerDraft(msg.slice(0, i));
      await sleep(typingSpeed);
    }
    // Pause so the viewer can see the complete message
    await sleep(500);
    // Clear draft, then send
    store.setComposerDraft('');
    await store.sendMessage(msg, forceCorrect);
  }, [typingSpeed]);

  /* ── setup fresh session ─────────────────────────────────────────────── */
  const setupFreshSession = useCallback(async (t: string, m: LearningMode) => {
    setSetupStatus('loading');
    try {
      const store = useSessionStore.getState();
      useSessionStore.setState({
        messages: [], mastery: {}, currentTopic: null,
        diagnosticComplete: false, consecutiveIncorrect: 0,
        weakTopics: [], misconceptions: [], youtubeResources: [],
        phase: 'rapport', pcrMode: 'prerequisite_first',
        isThinking: false, avatarState: 'idle',
        sessionId: null, setupDone: true,
      } as any);
      await store.createSession();
      const result = await store.setupSession(t, m);
      useSessionStore.getState().addMessage({
        role: 'bot', content: result.welcomeMessage,
        avatarState: 'speaking', quickReplies: ["Let's start →"],
      });
      setSetupStatus('ready');
    } catch (e) {
      console.error(e);
      setSetupStatus('error');
    }
  }, []);

  /* ── run ─────────────────────────────────────────────────────────────── */
  const run = useCallback(async () => {
    if (setupStatus !== 'ready') {
      await setupFreshSession(topic, mode);
    }
    abortRef.current = false;
    setRunning(true);
    setDone(false);
    setLog([]);

    // Countdown before starting — lets you start recording first
    if (startDelay > 0) {
      for (let s = startDelay; s > 0; s--) {
        if (abortRef.current) { setRunning(false); setCountdown(null); return; }
        setCountdown(s);
        await sleep(1000);
      }
      setCountdown(null);
    }
    // Auto-minimize so the panel is hidden during the recording
    setOpen(false);

    // kick off first diagnostic question
    try {
      await typeAndSend("Let's start →");
      await sleep(300);
      await waitReply();
    } catch {/* ignore */}

    for (let i = 0; i < script.length; i++) {
      if (abortRef.current) break;
      setStep(i);

      const curPhase = useSessionStore.getState().phase;
      if (curPhase === 'wrapup' && script[i].tag !== 'end') {
        setLog((l) => [...l, { idx: i, ok: true, note: 'skipped (wrapup)' }]);
        continue;
      }

      try {
        await typeAndSend(script[i].msg, script[i].tag === 'correct');
        await sleep(300);
        await waitReply();
        setLog((l) => [...l, { idx: i, ok: true, note: 'ok' }]);
      } catch (e) {
        setLog((l) => [...l, { idx: i, ok: false, note: String(e) }]);
      }

      if (i < script.length - 1 && !abortRef.current) await sleep(speed * 1000);
    }

    setRunning(false);
    setDone(true);
    setStep(-1);
    setOpen(true); // re-open so you can see the done state
  }, [setupStatus, setupFreshSession, topic, mode, speed, startDelay, waitReply, script, typeAndSend]);

  const stop  = () => { abortRef.current = true; setRunning(false); setCountdown(null); };
  const reset = () => {
    abortRef.current = true;
    setRunning(false); setDone(false); setStep(-1); setLog([]);
    setCountdown(null);
    setSetupStatus('idle');
    useSessionStore.getState().setComposerDraft('');
  };

  /* ── collapsed FAB ───────────────────────────────────────────────────── */
  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        title="Open simulation panel"
        style={{
          position: 'fixed', bottom: '24px', right: '24px', zIndex: 9999,
          width: '48px', height: '48px', borderRadius: '50%',
          background: 'var(--accent)', color: '#fff', border: 'none',
          cursor: 'pointer', fontSize: '20px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 14px rgba(0,0,0,.25)', transition: 'transform .15s',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.1)')}
        onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
      >🤖</button>
    );
  }

  /* ── expanded panel ──────────────────────────────────────────────────── */
  return (
    <div style={{
      position: 'fixed', bottom: '24px', right: '24px', zIndex: 9999,
      width: '370px', maxHeight: '84vh',
      background: 'var(--paper)', border: '1px solid var(--rule)',
      borderRadius: '12px', boxShadow: '0 8px 32px rgba(0,0,0,.18)',
      display: 'flex', flexDirection: 'column',
      fontFamily: 'ui-sans-serif, system-ui, sans-serif', fontSize: '13px',
      overflow: 'hidden',
    }}>

      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 14px', borderBottom: '1px solid var(--rule)',
        background: 'var(--paper-2)', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '16px' }}>🤖</span>
          <span style={{ fontWeight: 600, color: 'var(--ink)' }}>Auto-Simulate</span>
          {countdown !== null && (
            <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '999px', background: '#fef3c7', color: '#92400e', fontFamily: 'ui-monospace, monospace', fontWeight: 700 }}>
              ⏱ {countdown}s
            </span>
          )}
          {running && countdown === null && <span style={{ fontSize: '10px', padding: '2px 7px', borderRadius: '999px', background: '#d1fae5', color: '#065f46', fontFamily: 'ui-monospace, monospace' }}>▶ running</span>}
          {done    && <span style={{ fontSize: '10px', padding: '2px 7px', borderRadius: '999px', background: '#dbeafe', color: '#1e40af', fontFamily: 'ui-monospace, monospace' }}>✓ done</span>}
        </div>
        <button onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-3)', fontSize: '18px', lineHeight: 1 }}>×</button>
      </div>

      {/* Topic + mode */}
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--rule)', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '8px', background: 'var(--paper-2)' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ color: 'var(--ink-2)', minWidth: '42px', fontSize: '12px' }}>Topic</span>
          <select
            value={topic}
            onChange={(e) => { setTopic(e.target.value); setSetupStatus('idle'); setLog([]); setStep(-1); setDone(false); }}
            disabled={running}
            style={{ flex: 1, padding: '5px 8px', borderRadius: '6px', border: '1px solid var(--rule)', background: 'var(--paper)', color: 'var(--ink)', fontSize: '12px', cursor: 'pointer' }}
          >
            {TOPICS.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
          </select>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ color: 'var(--ink-2)', minWidth: '42px', fontSize: '12px' }}>Mode</span>
          <div style={{ display: 'flex', gap: '6px' }}>
            {(['visual', 'text'] as LearningMode[]).map((m) => (
              <button key={m} onClick={() => { setMode(m); setSetupStatus('idle'); }} disabled={running}
                style={{ padding: '4px 12px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer', transition: 'all .15s',
                  border: mode === m ? '1.5px solid var(--accent)' : '1px solid var(--rule)',
                  background: mode === m ? 'var(--accent-soft)' : 'var(--paper)',
                  color: mode === m ? 'var(--accent-ink)' : 'var(--ink-2)',
                  fontWeight: mode === m ? 600 : 400,
                }}>
                {m === 'visual' ? '🖼 Visual' : '💬 Text'}
              </button>
            ))}
          </div>
        </div>

        {setupStatus === 'idle' && !running && (
          <button onClick={() => setupFreshSession(topic, mode)}
            style={{ padding: '6px', borderRadius: '7px', fontSize: '12px', background: 'var(--paper-3)', color: 'var(--ink-2)', border: '1px solid var(--rule)', cursor: 'pointer' }}>
            ⟳ Load fresh session for this topic
          </button>
        )}
        {setupStatus === 'loading' && <div style={{ color: 'var(--ink-3)', fontSize: '12px', textAlign: 'center' }}>Setting up session…</div>}
        {setupStatus === 'ready'   && (
          <div style={{ color: '#065f46', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span>✓</span>
            <span>Session ready — <strong>{TOPICS.find(t => t.key === topic)?.label}</strong> · {mode}</span>
          </div>
        )}
        {setupStatus === 'error' && <div style={{ color: '#991b1b', fontSize: '12px' }}>✗ Setup failed — is the backend running?</div>}
      </div>

      {/* Timing controls */}
      <div style={{ padding: '8px 14px', borderBottom: '1px solid var(--rule)', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--ink-2)', whiteSpace: 'nowrap', fontSize: '12px', minWidth: '72px' }}>Msg delay</span>
          <input type="range" min="0.5" max="6" step="0.5" value={speed} onChange={(e) => setSpeed(Number(e.target.value))} disabled={running} style={{ flex: 1 }} />
          <span style={{ color: 'var(--ink-2)', fontFamily: 'ui-monospace, monospace', fontSize: '12px', minWidth: '28px' }}>{speed}s</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--ink-2)', whiteSpace: 'nowrap', fontSize: '12px', minWidth: '72px' }}>Typing</span>
          <input type="range" min="20" max="120" step="10" value={typingSpeed} onChange={(e) => setTypingSpeed(Number(e.target.value))} disabled={running} style={{ flex: 1 }} />
          <span style={{ color: 'var(--ink-2)', fontFamily: 'ui-monospace, monospace', fontSize: '12px', minWidth: '42px' }}>{typingSpeed}ms/c</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--ink-2)', whiteSpace: 'nowrap', fontSize: '12px', minWidth: '72px' }}>Start in</span>
          <input type="range" min="0" max="15" step="1" value={startDelay} onChange={(e) => setStartDelay(Number(e.target.value))} disabled={running} style={{ flex: 1 }} />
          <span style={{ color: 'var(--ink-2)', fontFamily: 'ui-monospace, monospace', fontSize: '12px', minWidth: '28px' }}>{startDelay}s</span>
        </div>
      </div>

      {/* Step list */}
      <div style={{ overflowY: 'auto', flex: 1, padding: '6px 0' }}>
        {script.map((s, i) => {
          const entry = log.find((l) => l.idx === i);
          const isActive = step === i && running;
          const isDone = !!entry;
          const tag = TAG_META[s.tag];
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', padding: '5px 14px', background: isActive ? 'var(--accent-soft)' : 'transparent', transition: 'background .2s' }}>
              <div style={{ width: '7px', height: '7px', borderRadius: '50%', flexShrink: 0, marginTop: '5px',
                background: isActive ? 'var(--accent)' : isDone ? (entry?.ok ? '#10b981' : '#ef4444') : 'var(--rule)' }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ color: isActive ? 'var(--accent-ink)' : 'var(--ink)', lineHeight: '1.35', fontSize: '12px' }}>{s.label}</div>
                <div style={{ fontSize: '11px', color: 'var(--ink-3)', fontFamily: 'ui-monospace, monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: '1px' }}>
                  &ldquo;{s.msg.length > 52 ? s.msg.slice(0, 52) + '…' : s.msg}&rdquo;
                </div>
              </div>
              <span style={{ flexShrink: 0, fontSize: '10px', padding: '2px 6px', borderRadius: '999px', whiteSpace: 'nowrap', background: tag.bg, color: tag.color }}>
                {!isDone && isActive ? '▶ …'
                  : isDone && !entry?.ok ? '✗ err'
                  : isDone && entry?.note === 'skipped (wrapup)' ? '⏩ skip'
                  : tag.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{ padding: '10px 14px', borderTop: '1px solid var(--rule)', display: 'flex', gap: '8px', flexShrink: 0, background: 'var(--paper-2)' }}>
        {!running ? (
          <>
            <button onClick={run} disabled={setupStatus === 'loading'}
              style={{ flex: 1, padding: '8px', borderRadius: '7px',
                background: done ? '#d1fae5' : 'var(--accent)',
                color: done ? '#065f46' : '#fff',
                border: 'none', cursor: setupStatus === 'loading' ? 'wait' : 'pointer',
                fontWeight: 600, fontSize: '13px' }}>
              {done ? '✓ Complete' : setupStatus === 'ready' ? '▶ Run simulation' : '▶ Setup & Run'}
            </button>
            {(step >= 0 || done || setupStatus !== 'idle') && (
              <button onClick={reset}
                style={{ padding: '8px 12px', borderRadius: '7px', background: 'var(--paper-3)', color: 'var(--ink-2)', border: '1px solid var(--rule)', cursor: 'pointer', fontSize: '13px' }}>
                Reset
              </button>
            )}
          </>
        ) : (
          <button onClick={stop}
            style={{ flex: 1, padding: '8px', borderRadius: '7px', background: '#fee2e2', color: '#991b1b', border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '13px' }}>
            ⏹ Stop
          </button>
        )}
      </div>
    </div>
  );
}
