export const TOPIC_MENU = [
  { label: 'Brachial Plexus',                          key: 'brachial_plexus' },
  { label: 'Rotator Cuff',                             key: 'rotator_cuff' },
  { label: 'Peripheral Nerves (median, ulnar, radial)', key: 'peripheral_nerves' },
  { label: 'Shoulder Joint',                           key: 'shoulder_joint' },
  { label: 'Elbow Joint',                              key: 'elbow_joint' },
  { label: 'Wrist & Hand',                             key: 'wrist_hand' },
  { label: 'Dermatomes (C5–T1)',                       key: 'dermatomes' },
  { label: 'Nerve Injury Syndromes',                   key: 'nerve_injuries' },
  { label: 'Upper Limb Muscles',                       key: 'upper_limb_muscles' },
  { label: 'Spinal Cord',                              key: 'spinal_cord' },
];

export const PHASES = [
  { key: 'rapport',    label: 'Diagnostic', time: '0–2m',   desc: 'Diagnostic probes calibrated your starting mastery.' },
  { key: 'tutoring',   label: 'Tutoring',   time: '2–12m',  desc: 'Socratic loop with progressive context revelation.' },
  { key: 'assessment', label: 'Assessment', time: '12–14m', desc: 'Clinical NBCOT-style scenario.' },
  { key: 'wrapup',     label: 'Wrap-up',    time: '14–15m', desc: 'Report card · misconceptions · study tips.' },
];

export const AVATAR_STATE_FOR_AGENT = {
  diagnostic:  'asking',
  tutor:       'speaking',
  assessment:  'assess',
  wrapup:      'idle',
};
