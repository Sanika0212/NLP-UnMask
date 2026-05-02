export const TOPICS = [
  { key: 'brachial_plexus',    label: 'Brachial Plexus',                          desc: 'Formation, roots, trunks, cords, branches' },
  { key: 'rotator_cuff',       label: 'Rotator Cuff',                             desc: 'SITS muscles, innervation, clinical tears' },
  { key: 'peripheral_nerves',  label: 'Peripheral Nerves',                        desc: 'Axillary, radial, median, ulnar nerves' },
  { key: 'shoulder_joint',     label: 'Shoulder Joint',                           desc: 'Glenohumeral, AC joint, stabilisers' },
  { key: 'elbow_joint',        label: 'Elbow Joint',                              desc: 'Carrying angle, cubital tunnel, ligaments' },
  { key: 'wrist_hand',         label: 'Wrist & Hand',                             desc: 'Carpal bones, thenar eminence, intrinsics' },
  { key: 'dermatomes',         label: 'Dermatomes (C5–T1)',                       desc: 'Sensory levels, clinical numbness patterns' },
  { key: 'nerve_injuries',     label: 'Nerve Injury Syndromes',                   desc: "Erb's, Klumpke's, wrist drop, claw hand" },
  { key: 'upper_limb_muscles', label: 'Upper Limb Muscles',                       desc: 'Flexors, extensors, rotators, innervation' },
  { key: 'spinal_cord',        label: 'Spinal Cord',                              desc: 'Conus, cauda equina, spinal levels' },
];

export type TopicKey = (typeof TOPICS)[number]['key'];
