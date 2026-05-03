export const TOPICS = [
  { key: 'brachial_plexus',    label: 'Brachial Plexus',        dagLabel: 'Br.Plexus', desc: 'Formation, roots, trunks, cords, branches' },
  { key: 'rotator_cuff',       label: 'Rotator Cuff',           dagLabel: 'Rot.Cuff',  desc: 'SITS muscles, innervation, clinical tears' },
  { key: 'peripheral_nerves',  label: 'Peripheral Nerves',      dagLabel: 'P.Nerves',  desc: 'Axillary, radial, median, ulnar nerves' },
  { key: 'shoulder_joint',     label: 'Shoulder Joint',         dagLabel: 'Shoulder',  desc: 'Glenohumeral, AC joint, stabilisers' },
  { key: 'elbow_joint',        label: 'Elbow Joint',            dagLabel: 'Elbow',     desc: 'Carrying angle, cubital tunnel, ligaments' },
  { key: 'wrist_hand',         label: 'Wrist & Hand',           dagLabel: 'Wrist',     desc: 'Carpal bones, thenar eminence, intrinsics' },
  { key: 'dermatomes',         label: 'Dermatomes (C5–T1)',     dagLabel: 'Dermato.',  desc: 'Sensory levels, clinical numbness patterns' },
  { key: 'nerve_injuries',     label: 'Nerve Injury Syndromes', dagLabel: 'N.Injury',  desc: "Erb's, Klumpke's, wrist drop, claw hand" },
  { key: 'upper_limb_muscles', label: 'Upper Limb Muscles',     dagLabel: 'UL Musc.', desc: 'Flexors, extensors, rotators, innervation' },
  { key: 'spinal_cord',        label: 'Spinal Cord',            dagLabel: 'Sp.Cord',   desc: 'Conus, cauda equina, spinal levels' },
];

export type TopicKey = (typeof TOPICS)[number]['key'];

export function getTopicMastery(mastery: Record<string, number>, topicKey: string): number {
  const entries = Object.entries(mastery).filter(([k]) => k.startsWith(topicKey + '.'));
  if (entries.length === 0) return mastery[topicKey] ?? 0;
  return entries.reduce((s, [, v]) => s + v, 0) / entries.length;
}

export function isWeakTopic(weakTopics: string[], topicKey: string): boolean {
  return weakTopics.some((wt) => wt === topicKey || wt.startsWith(topicKey + '.'));
}
