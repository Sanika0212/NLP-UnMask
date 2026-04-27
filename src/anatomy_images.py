"""
Anatomical diagrams for visual hints.

Each entry may have:
  caption      — shown above the visual
  diagram      — ASCII/Unicode fallback (always present)
  image_file   — filename in public/anatomy/ (Gray's Anatomy, public domain); shown when present
"""

import os as _os
_IMG_DIR = _os.path.join(_os.path.dirname(__file__), "..", "public", "anatomy")

ANATOMY_DIAGRAMS: dict[str, dict] = {

    # ── Spinal cord ──────────────────────────────────────────────────────────
    "spinal_cord.anatomy": {
        "caption": "Spinal cord cross-section — dorsal/ventral horns, rami, grey/white matter",
        "image_file": "spinal_cord.png",
        "diagram": """\
 SPINAL CORD CROSS-SECTION

        Dorsal (posterior)
              │
   ┌──────────┴──────────┐
   │   Dorsal horn  ●    │  ← Sensory (afferent) neurons
   │                     │
   │   ●  Grey matter ●  │
   │                     │
   │   Ventral horn ●    │  ← Motor (efferent) neurons
   └──────────┬──────────┘
              │
        Ventral (anterior)

 ROOTS:
  Dorsal root (sensory) ─┐
                          ├─► Spinal nerve ─► Anterior ramus ─► Brachial plexus
  Ventral root (motor)  ─┘

 Each spinal nerve = dorsal + ventral root combined
 Anterior rami (C5–T1) → form the brachial plexus
 Posterior rami → innervate back muscles (NOT part of brachial plexus)""",
    },

    "spinal_cord.anterior_rami": {
        "caption": "Anterior rami C5–T1 — origin of the brachial plexus",
        "diagram": """\
 ANTERIOR RAMI → BRACHIAL PLEXUS CONTRIBUTION

 Vertebra  │  Spinal Level  │  Contribution
 ──────────┼────────────────┼──────────────────────────────
    C5     │  Cervical 5    │  Upper trunk (with C6)
    C6     │  Cervical 6    │  Upper trunk (with C5)
    C7     │  Cervical 7    │  Middle trunk (alone)
    C8     │  Cervical 8    │  Lower trunk (with T1)
    T1     │  Thoracic 1    │  Lower trunk (with C8)
 ──────────┴────────────────┴──────────────────────────────

 Each spinal nerve exits through the INTERVERTEBRAL FORAMEN
 then immediately splits:
   • Posterior ramus → back muscles / skin
   • Anterior ramus  → limbs / anterior trunk

 KEY CLINICAL NOTE:
  Erb's palsy  → C5–C6 injury  (upper trunk, waiter's tip)
  Klumpke's   → C8–T1 injury  (lower trunk, claw hand)
  Total plexus→ C5–T1 injury  (flail arm)""",
    },

    # ── Brachial plexus sub-diagrams ─────────────────────────────────────────
    "brachial_plexus.origin": {
        "caption": "Brachial plexus origins — C5–T1 anterior rami and first branches",
        "image_file": "brachial_plexus.png",
        "diagram": """\
 BRACHIAL PLEXUS ORIGINS

 Cervical vertebrae C5–C8 + Thoracic T1 contribute via anterior rami

         C5 ─────────────────────────────────────────►
         C6 ─────────────────────────────────────────►  Upper trunk
         C7 ─────────────────────────────────────────►  Middle trunk
         C8 ─────────────────────────────────────────►  Lower trunk
         T1 ─────────────────────────────────────────►

 Mnemonic: 5 ROOTS (five fingers spread = C5 C6 C7 C8 T1)

 BRANCHES DIRECTLY FROM ROOTS (before trunks):
  C5–C7  → Long thoracic nerve → Serratus anterior
  C5     → Dorsal scapular nerve → Rhomboids, Levator scapulae
  C5–C8  → Phrenic nerve (partial) → Diaphragm

 EXIT POINT: Scalene triangle (between anterior + middle scalene muscles)
 ⚠️  Compression here → Thoracic outlet syndrome""",
    },

    "brachial_plexus.trunks": {
        "caption": "Brachial plexus trunks — upper, middle, lower and Erb's/Klumpke's point",
        "image_file": "brachial_plexus.png",
        "diagram": """\
 BRACHIAL PLEXUS — TRUNKS

 Root    ──► Trunk          Common injury
 ─────────────────────────────────────────────────────
 C5 + C6 ──► UPPER trunk   ← Erb's point (Erb's palsy)
   C7    ──► MIDDLE trunk
 C8 + T1 ──► LOWER trunk   ← Klumpke's (C8/T1 stretch)
 ─────────────────────────────────────────────────────

 Each trunk immediately divides into:
   • ANTERIOR division → supply flexor compartments
   • POSTERIOR division → supply extensor compartments

 BRANCHES FROM TRUNKS:
  Upper trunk → Suprascapular nerve (C5-C6)
                  → Supraspinatus + Infraspinatus

 ERB'S PALSY (C5-C6 / upper trunk):
  • Loss: shoulder ABduction, external rotation, elbow flexion
  • Posture: "Waiter's tip" — arm adducted, internally rotated
  • Mechanism: lateral flexion away + shoulder depression

 KLUMPKE'S PALSY (C8-T1 / lower trunk):
  • Loss: intrinsic hand muscles
  • Posture: Claw hand
  • Mechanism: upward traction of arm (birth, overhead grab)""",
    },

    "brachial_plexus.divisions": {
        "caption": "Brachial plexus divisions — anterior vs posterior, flexor vs extensor",
        "image_file": "brachial_plexus.png",
        "diagram": """\
 BRACHIAL PLEXUS — DIVISIONS

 Each trunk splits into ANTERIOR and POSTERIOR divisions:

 Trunk          │ Division    │ → Cord
 ───────────────┼─────────────┼───────────────
 Upper trunk    │ Anterior  ──┤──► Lateral cord
                │ Posterior ──┤──┐
 Middle trunk   │ Anterior  ──┤──► Lateral cord
                │ Posterior ──┤  │
 Lower trunk    │ Anterior  ──┤──► Medial cord
                │ Posterior ──┴──► Posterior cord
 ───────────────┴─────────────┴───────────────

 RULE: Anterior divisions → LATERAL and MEDIAL cords
                           → innervate FLEXORS
       Posterior divisions → POSTERIOR cord
                           → innervate EXTENSORS

 EXAM TIP:
  All 3 posterior divisions combine → POSTERIOR cord
  This explains why radial + axillary nerves (posterior cord)
  innervate all extensors of the arm""",
    },

    "brachial_plexus.cords": {
        "caption": "Brachial plexus cords — lateral, medial, posterior and their branches",
        "image_file": "brachial_plexus.png",
        "diagram": """\
 BRACHIAL PLEXUS — CORDS
 (named by position relative to axillary artery)

 LATERAL CORD (C5–C7):
   Musculocutaneous N. ──► Biceps, Brachialis, Coracobrachialis
   Lateral root of Median N. ──┐
                                ├──► Median nerve (C5–T1)
 MEDIAL CORD (C8–T1):          │
   Medial root of Median N. ───┘
   Ulnar N. ──► intrinsic hand, medial 1½ fingers
   Medial cutaneous N. (arm + forearm)

 POSTERIOR CORD (C5–T1):
   Axillary N.  ──► Deltoid, Teres minor, lateral arm sensation
   Radial N.    ──► All extensors upper limb, lateral dorsal hand

 Memory: LUMBAR (Lateral=Upper, Medial=BrAchial, Ropes)
         or: "My Aunt Raped Uncle Robert"
         (Median, Axillary, Radial, Ulnar, musculocutaneous)

 CORD BRANCHES SUMMARY:
  Lateral  → Musculocutaneous + lateral Median
  Medial   → Ulnar + medial Median + cutaneous branches
  Posterior→ Axillary + Radial (+ upper/lower subscapular, thoracodorsal)""",
    },

    "brachial_plexus.terminal_branches": {
        "caption": "5 terminal branches — roots, motor targets and key injury patterns",
        "image_file": "brachial_plexus.png",
        "diagram": """\
 BRACHIAL PLEXUS — TERMINAL BRANCHES

 Nerve              │ Roots    │ Key Motors        │ Injury Pattern
 ───────────────────┼──────────┼───────────────────┼──────────────────────
 Musculocutaneous   │ C5–C7   │ Biceps, Brachialis│ Weak elbow flexion
 Axillary           │ C5–C6   │ Deltoid, T. minor │ Flat shoulder, no ABd
 Radial             │ C5–T1   │ All extensors     │ Wrist drop
 Median             │ C5–T1   │ LOAF + forearm Fx │ Ape hand, CTS
 Ulnar              │ C8–T1   │ Intrinsics, Hypo  │ Claw hand (4th/5th)
 ───────────────────┴──────────┴───────────────────┴──────────────────────

 SPLINT GUIDE (OT critical):
  Radial injury → Cock-up (wrist extension) splint
  Ulnar injury  → Anti-claw splint (MCP block ring+little)
  Median injury → Thumb abduction/opposition splint
  Combined      → Resting hand splint (all injured)

 Memory: "My Aunt Really Missed Uncle"
         (Musculocutaneous, Axillary, Radial, Median, Ulnar)""",
    },

    # ── Rotator cuff sub-diagrams ────────────────────────────────────────────
    "rotator_cuff.muscles": {
        "caption": "Rotator cuff SITS muscles — origins, insertions, nerves, OT tests",
        "image_file": "shoulder_joint.png",
        "diagram": """\
 ROTATOR CUFF — SITS OVERVIEW

 Muscle          │ Origin              │ Insert   │ Action       │ Nerve
 ────────────────┼─────────────────────┼──────────┼──────────────┼────────────
 Supraspinatus   │ Supraspinous fossa  │ Greater  │ ABd 0–15°    │ Suprascp
 Infraspinatus   │ Infraspinous fossa  │ tubercle │ Lat. rot.    │ Suprascp
 Teres Minor     │ Lateral border scp  │ Greater  │ Lat. rot.    │ Axillary
 Subscapularis   │ Subscapular fossa   │ Lesser   │ Med. rot.    │ Subscplar
 ────────────────┴─────────────────────┴──────────┴──────────────┴────────────

 ALL FOUR: arise from scapula → insert on humerus → stabilise GH joint

 CLINICAL TEST QUICK-REFERENCE:
  Empty Can (Jobe's)     → Supraspinatus
  External Rotation Lag  → Infraspinatus
  Hornblower's Sign      → Teres Minor (can't externally rotate in ABd)
  Lift-off / Belly Press → Subscapularis

 MOST COMMON TEAR:
  Supraspinatus (impingement under coracoacromial arch at 60–120° ABd arc)""",
    },

    "rotator_cuff.infraspinatus": {
        "caption": "Infraspinatus — external rotation, suprascapular nerve, OT relevance",
        "image_file": "shoulder_joint.png",
        "diagram": """\
 INFRASPINATUS

 Origin:    Infraspinous fossa (posterior scapula, below spine)
 Insertion: Middle facet of GREATER tubercle of humerus
 Action:    LATERAL (external) rotation of humerus
            Weak horizontal abduction
 Nerve:     Suprascapular nerve (C5–C6) — same as supraspinatus

 ┌────────────────────────────────────────────┐
 │ Posterior view — scapula                   │
 │                                            │
 │  ─── Spine of scapula ─────────────────── │
 │                                            │
 │  Infraspinous fossa [INFRASPINATUS origin] │
 │                              ↘             │
 │                        Greater tubercle    │
 └────────────────────────────────────────────┘

 CLINICAL TESTS:
  • External Rotation Lag Sign: arm at 90° ABd, examiner passively
    externally rotates → release → arm falls = infraspinatus tear
  • External rotation resisted test at 0° (Patte test)
  • Hornblower's sign tests TERES MINOR (not infraspinatus)

 OT RELEVANCE:
  • Handshake, turning a doorknob, reaching to the side
  • Loss → difficulty with most lateral rotation ADLs
  • Post-op: avoid medial rotation for 6 weeks (protects repair)""",
    },

    "rotator_cuff.teres_minor": {
        "caption": "Teres Minor — lateral rotation, axillary nerve, Hornblower's sign",
        "image_file": "shoulder_joint.png",
        "diagram": """\
 TERES MINOR

 Origin:    Upper 2/3 of LATERAL BORDER of scapula
 Insertion: Inferior facet of GREATER tubercle of humerus
 Action:    LATERAL (external) rotation of humerus
            Weak adduction, weak extension
 Nerve:     AXILLARY nerve (C5–C6)  ← different from infraspinatus!

 RELATIONSHIP TO INFRASPINATUS:
  Both: lateral rotation + greater tubercle
  Difference: teres minor = axillary nerve; infraspin = suprascapular

 CLINICAL TEST:
  • Hornblower's Sign: arm in 90° ABd, 90° elbow flex → examiner
    releases → patient cannot hold position = teres minor + infraspinatus
  • Specifically tests COMBINED external rotation in abduction

 QUADRILATERAL SPACE:
  Teres minor forms the SUPERIOR BORDER of the quadrilateral space
  → Axillary nerve and posterior circumflex artery pass through here
  → Quadrilateral space syndrome: compression of axillary N.

 OT RELEVANCE:
  • Assists any lateral rotation activity (reaching, grooming)
  • Often torn alongside infraspinatus in massive cuff tears
  • Small muscle — rarely torn in isolation""",
    },

    "brachial_plexus": {
        "caption": "Brachial Plexus — trace C5→T1 through trunks, divisions, cords to terminal branches",
        "image_file": "brachial_plexus.png",
        "diagram": """\
ROOTS   TRUNKS     DIVS    CORDS        TERMINAL BRANCHES
                   ┌ Ant ─────────────┐
C5 ─┬─ Upper ─────┤                   Lateral ──┬─ Musculocutaneous (C5-C7)
C6 ─┘             └ Post ─────────┐              └─ Median (lateral head)
                   ┌ Ant ─────────│──────────────── (joins medial head)
C7 ──── Middle ───┤               │
                   └ Post ────────┤  Posterior ──┬─ Axillary N. (C5-C6)
                   ┌ Ant ─────────│              └─ Radial N. (C5-T1)
C8 ─┬─ Lower ─────┤               │
T1 ─┘             └ Post ─────────┘  Medial ───┬─ Ulnar N. (C8-T1)
                                                ├─ Median (medial head)
                                                ├─ Medial cutaneous (arm)
                                                └─ Medial cutaneous (forearm)
Memory: Robert Taylor Drinks Cold Beer
        (Roots Trunks Divisions Cords Branches)""",
    },

    "rotator_cuff": {
        "caption": "Rotator Cuff — SITS muscles, attachments, movements, and clinical tests",
        "image_file": "shoulder_joint.png",
        "diagram": """\
┌──────────────────────────────────────────────────────────────┐
│            ROTATOR CUFF — SITS Mnemonic                      │
├──────────────┬──────────────────────┬────────────────────────┤
│ Muscle       │ Action               │ Clinical Test          │
├──────────────┼──────────────────────┼────────────────────────┤
│ Supraspinatus│ Abduction (0–15°)    │ Empty Can Test         │
│              │ Greater tubercle     │ Drop Arm Test          │
├──────────────┼──────────────────────┼────────────────────────┤
│ Infraspinatus│ Lateral rotation     │ External Rotation Lag  │
│              │ Greater tubercle     │ Palpate infraspinous   │
├──────────────┼──────────────────────┼────────────────────────┤
│ Teres Minor  │ Lateral rotation     │ Hornblower's Sign      │
│              │ Greater tubercle     │                        │
├──────────────┼──────────────────────┼────────────────────────┤
│ Subscapularis│ Medial rotation      │ Lift-off Test          │
│              │ Lesser tubercle      │ Bear Hug Test          │
└──────────────┴──────────────────────┴────────────────────────┘
All arise from scapula → insert on humerus → stabilise GH joint""",
    },

    "peripheral_nerves": {
        "caption": "Upper limb peripheral nerve territories — sensory and motor",
        "image_file": "peripheral_nerves.png",
        "diagram": """\
         PERIPHERAL NERVE TERRITORIES — Upper Limb

 PALMAR SURFACE              DORSAL SURFACE
 ┌─────────────────┐         ┌─────────────────┐
 │  M  M  M  M     │         │  R  R  R        │
 │ (1)(2)(3)(4½)   │         │ (1½)(2)(3)      │
 │                 │         │                 │
 │        U  U  U  │         │  U  U  U        │
 │       (4½)(5)   │         │ (4½)(5)         │
 └─────────────────┘         └─────────────────┘
 M = Median  U = Ulnar  R = Radial  (finger numbers)

 Thenar eminence = Median    Hypothenar = Ulnar
 Lateral forearm = Musculocutaneous
 Medial arm/forearm = Medial cord cutaneous branches

 KEY INJURY PATTERNS:
 Median (carpal tunnel) → Ape hand, thenar wasting, loss of pinch
 Ulnar (cubital tunnel) → Claw hand (ring+little), Froment's sign
 Radial (spiral groove) → Wrist drop, loss of finger extension""",
    },

    "peripheral_nerves.median": {
        "caption": "Median nerve — course, motor, sensory and CTS clinical features",
        "image_file": "median_nerve.png",
        "diagram": """\
 MEDIAN NERVE (C6–T1) — Lateral + Medial cords

 Origin: Medial + Lateral cord of brachial plexus
    │
    ▼
 Medial to brachial artery → cubital fossa
    │
    ├── Anterior Interosseous N. (AIN) ──► FPL, FDP (index/middle), Pronator quadratus
    │
    ▼
 CARPAL TUNNEL (under flexor retinaculum)
    │
    ├── Motor: LOAF muscles
    │    L — Lumbricals 1 & 2
    │    O — Opponens pollicis     ← Opposition of thumb
    │    A — Abductor pollicis brevis
    │    F — Flexor pollicis brevis
    │
    └── Sensory: Lateral 3½ fingers (palmar) + thenar eminence

 COMPRESSION SIGNS:
  • Phalen's test (wrist flexion 60s → tingling)
  • Tinel's sign (tap carpal tunnel → tingling)
  • Ape hand deformity (thenar wasting)""",
    },

    "peripheral_nerves.ulnar": {
        "caption": "Ulnar nerve — course, cubital tunnel, claw hand and Froment's sign",
        "image_file": "ulnar_nerve.png",
        "diagram": """\
 ULNAR NERVE (C8–T1) — Medial cord

 Origin: Medial cord → medial to axillary artery
    │
    ▼
 Posterior to medial epicondyle ← CUBITAL TUNNEL
    │                              (common compression site)
    ▼
 Guyon's Canal at wrist (2nd compression site)
    │
    ├── Motor: Hypothenar muscles (ADM, FDM, ODM)
    │          Interossei (all 4)
    │          Lumbricals 3 & 4
    │          Adductor pollicis ← FROMENT'S SIGN
    │
    └── Sensory: Medial 1½ fingers + hypothenar eminence

 INJURY PATTERNS:
  • Claw hand — ring + little fingers (lumbricals 3,4 lost)
  • Froment's sign — FPL compensates for lost adductor pollicis
  • Wartenberg's sign — little finger abducted at rest
  • Cubital tunnel → ulnar nerve decompression / transposition""",
    },

    "peripheral_nerves.radial": {
        "caption": "Radial nerve — spiral groove, wrist drop and cock-up splint",
        "image_file": "radial_nerve.png",
        "diagram": """\
 RADIAL NERVE (C5–T1) — Posterior cord

 Origin: Posterior cord → posterior to axillary artery
    │
    ▼
 Winds around SPIRAL GROOVE of humerus ← Fracture risk!
    │
    ├── Motor (above elbow): Triceps, Brachioradialis, ECRL
    │
    ▼
 Bifurcates at lateral epicondyle:
    │
    ├── Superficial branch → Sensory: Lateral dorsal hand (1½ fingers)
    │
    └── Deep branch = PIN (Posterior Interosseous N.)
         └── Motor: Finger/wrist extensors, Supinator
                    EDC, EIP, EPL, EPB, APL

 INJURY AT SPIRAL GROOVE (Saturday night palsy / humeral #):
  • Wrist drop (cannot extend wrist)
  • Loss of finger extension (MCP joints drop)
  • Sensory loss — lateral dorsal hand (small area)
  • SPLINT: Cock-up (wrist extension) splint""",
    },

    "peripheral_nerves.axillary": {
        "caption": "Axillary nerve — deltoid, surgical neck fracture",
        "image_file": "axillary_nerve.png",
        "diagram": """\
 AXILLARY NERVE (C5–C6) — Posterior cord

 Origin: Posterior cord of brachial plexus
    │
    ▼
 Passes through Quadrilateral Space with posterior circumflex artery
    │
    ├── Motor: Deltoid (all three heads) ← ABduction 15–90°
    │          Teres Minor ← Lateral rotation
    │
    └── Sensory: Regimental badge area (lateral arm)

 ⚠️ INJURY RISK:
  • Surgical neck of humerus fracture
  • Anterior shoulder dislocation
  • Result: Loss of shoulder abduction, flat shoulder contour

 OT RELEVANCE:
  • ADL re-training for reaching overhead
  • Deltoid sling for positioning
  • Passive ROM to prevent adhesive capsulitis""",
    },

    "rotator_cuff.subscapularis": {
        "caption": "Subscapularis — medial rotation, lesser tubercle, lift-off test",
        "image_file": "shoulder_joint.png",
        "diagram": """\
 SUBSCAPULARIS

 Origin:   Subscapular fossa (anterior scapula surface)
 Insertion: Lesser tubercle of humerus
 Action:   MEDIAL (internal) rotation of humerus
           Adduction, extension assistance
 Nerve:    Upper + Lower subscapular nerves (C5-C6)

 CLINICAL TESTS:
  • Lift-off test: Back of hand off lumbar region → tests subscapularis
  • Bear hug test: Palm on opposite shoulder, resist pull-off
  • Belly press: Press abdomen keeping wrist straight

 OT CONTEXT:
  • Reach behind back (dressing, hygiene)
  • Tucking in shirt, fastening bra strap
  • Tears cause lateral rotation contracture
  • Post-op: avoid lateral rotation for 6 weeks

 Mnemonic: SubSCAPularis → Scapula (anterior) → Medial rotation""",
    },

    "rotator_cuff.supraspinatus": {
        "caption": "Supraspinatus — initiates abduction, empty can test, impingement",
        "image_file": "shoulder_joint.png",
        "diagram": """\
 SUPRASPINATUS

 Origin:   Supraspinous fossa
 Insertion: Superior facet of greater tubercle
 Action:   INITIATES abduction 0–15°
           (Deltoid takes over 15–90°, trapezius >90°)
 Nerve:    Suprascapular nerve (C5-C6)

 IMPINGEMENT ZONE: Passes under coracoacromial arch
  → Compression between acromion + greater tubercle
  → Most common rotator cuff tear site

 CLINICAL TESTS:
  • Empty Can (Jobe's): Arm 90° abd, 30° horiz flex, thumb down
    → Pain/weakness = supraspinatus tear/impingement
  • Drop Arm Test: Arm falls from 90° abduction
  • Neer's Sign: Passive forward flexion → impingement pain

 OT CONTEXT:
  • Any overhead activity (reaching, dressing)
  • Avoid painful arc 60–120°
  • Strengthening in pain-free range""",
    },

    "shoulder_joint": {
        "caption": "Glenohumeral joint — ball-and-socket, rotator cuff stabilisation",
        "image_file": "shoulder_joint.png",
        "diagram": """\
 GLENOHUMERAL (Shoulder) JOINT

 Type: Ball-and-socket (most mobile joint in body)
 Bones: Humeral head (ball) + Glenoid fossa (shallow socket)
 Labrum: Fibrocartilage ring that deepens socket

 STATIC STABILISERS:           DYNAMIC STABILISERS:
  • Glenohumeral ligaments       • Rotator cuff (SITS)
  • Glenoid labrum               • Long head biceps
  • Joint capsule                • Deltoid

 MOVEMENTS & PRIMARY MOVERS:
  Flexion (0–180°)    → Anterior deltoid, Pec major
  Extension (0–60°)   → Posterior deltoid, Latissimus
  Abduction (0–180°)  → Supraspinatus (0–15°), Deltoid (15–90°)
  Lateral rotation    → Infraspinatus, Teres minor
  Medial rotation     → Subscapularis, Pec major, Latissimus

 COMMON OT CONDITIONS:
  • Rotator cuff tear → impaired reaching/overhead ADLs
  • Adhesive capsulitis (frozen shoulder) → progressive ROM loss
  • Anterior instability/dislocation → axillary nerve risk""",
    },

    # ── Elbow joint ───────────────────────────────────────────────────────────
    "elbow_joint.anatomy": {
        "caption": "Elbow joint — humeroulnar/humeroradial articulations, carrying angle",
        "image_file": "elbow_joint.png",
        "diagram": """\
 ELBOW JOINT (Gray329)

 ARTICULATIONS (all share one synovial cavity):
  • Humeroulnar — hinge, primary flexion/extension (trochlea + trochlear notch)
  • Humeroradial — hinge + glide (capitulum + radial head)
  • Proximal radioulnar — pivot, pronation/supination

 CARRYING ANGLE: 5–15° valgus (females tend higher)
  • Cubitus valgus (increased) → tardy ulnar nerve palsy
  • Cubitus varus (decreased, "gunstock") → supracondylar fracture sequela

 MOVEMENTS:
  Flexion 0–145°   → Biceps (C5-C6), Brachialis (C5-C6), Brachioradialis (C6)
  Extension 0°      → Triceps (C7), Anconeus (C7-C8)
  Pronation 0–80°  → Pronator teres, Pronator quadratus (median, C6-C8)
  Supination 0–80° → Biceps brachii, Supinator (radial, C6)

 OT CONTEXT:
  • Elbow flexion contracture → limits self-care, reaching
  • Lateral epicondylitis (tennis elbow) → extensor origin pain""",
    },

    "elbow_joint.ligaments": {
        "caption": "Elbow ligaments — MCL, LCL, annular ligament",
        "image_file": "elbow_joint.png",
        "diagram": """\
 ELBOW LIGAMENTS

 MEDIAL (ULNAR) COLLATERAL LIGAMENT (MCL/UCL):
  • Anterior band — primary valgus stabiliser; most commonly torn
  • Posterior band — taut in flexion
  • Transverse band
  Injury: Valgus stress (throwing athletes), medial elbow pain

 LATERAL (RADIAL) COLLATERAL LIGAMENT (LCL):
  • Lateral UCL — posterolateral rotatory instability if torn
  • Radial collateral ligament
  • Annular ligament — encircles radial head (pivot for pronation/supination)

 ANNULAR LIGAMENT:
  • Holds radial head in radial notch of ulna
  • Nursemaid's elbow (pulled elbow) = subluxation of radial head through annular lig
    → Common in children <5 yrs, forced forearm pronation/traction
    → Reduce: supination + flexion or hyperpronation""",
    },

    "elbow_joint.cubital_tunnel": {
        "caption": "Cubital tunnel — ulnar nerve compression at medial elbow",
        "image_file": "elbow_joint.png",
        "diagram": """\
 CUBITAL TUNNEL SYNDROME

 ANATOMY:
  • Ulnar nerve passes posterior to medial epicondyle
  • Cubital tunnel = between medial epicondyle and olecranon
  • Nerve crosses into forearm under Osborne's ligament (arcuate ligament)

 SYMPTOMS:
  • Paraesthesia: medial 1½ fingers (ring + little), medial forearm
  • Weakness: intrinsic hand muscles, flexor carpi ulnaris, FDP (4th/5th)
  • Clawing: ring + little fingers (intrinsic minus posture)
  • Froment's sign: thumb IP flexes when pinching paper (compensates adductor pollicis)

 PROVOCATIVE TESTS:
  • Elbow flexion test: >60 sec flexion reproduces symptoms
  • Tinel's sign: percussion at medial epicondyle

 OT MANAGEMENT:
  • Night elbow extension splint (prevent full flexion)
  • Avoid prolonged elbow flexion, lean-on-elbow postures
  • Ulnar nerve gliding exercises""",
    },

    # ── Wrist and hand ────────────────────────────────────────────────────────
    "wrist_hand.carpals": {
        "caption": "Carpal bones — two rows, scaphoid fracture, DISI/VISI instability",
        "image_file": "carpal_bones.png",
        "diagram": """\
 CARPAL BONES (Gray219)

 PROXIMAL ROW (radial→ulnar): Scaphoid, Lunate, Triquetrum, Pisiform
 DISTAL ROW (radial→ulnar):   Trapezium, Trapezoid, Capitate, Hamate

 Mnemonic: "Some Lovers Try Positions That They Can't Handle"

 SCAPHOID:
  • Most commonly fractured carpal (fall on outstretched hand)
  • Waist fracture → avascular necrosis risk (blood supply distal→proximal)
  • Tenderness in anatomical snuffbox
  • OT: thumb spica splint 8–12 weeks

 LUNATE:
  • Most commonly dislocated carpal
  • DISI (dorsal intercalated segment instability): scapholunate ligament tear
  • VISI: lunotriquetral tear

 HAMATE:
  • Hook fracture → ulnar nerve/artery compression in Guyon's canal
  • Cyclists, racket sports

 CLINICAL: Carpal tunnel = flexor retinaculum roof
  Contents: 9 flexor tendons + median nerve""",
    },

    "wrist_hand.intrinsic_muscles": {
        "caption": "Intrinsic hand muscles — thenar, hypothenar, lumbricals, interossei",
        "image_file": "carpal_bones.png",
        "diagram": """\
 INTRINSIC HAND MUSCLES

 THENAR (median nerve, C8-T1 recurrent branch):
  • Abductor pollicis brevis — abducts thumb (NBCOT key muscle)
  • Flexor pollicis brevis — flexes thumb MCP (dual: median + ulnar)
  • Opponens pollicis — opposition (rotates 1st metacarpal)
  Damage → ape hand: loss of opposition, thenar wasting

 HYPOTHENAR (ulnar nerve, C8-T1 deep branch):
  • Abductor digiti minimi
  • Flexor digiti minimi
  • Opponens digiti minimi

 LUMBRICALS (4):
  • 1st + 2nd: median nerve
  • 3rd + 4th: ulnar nerve
  Action: MCP flexion + IP extension (intrinsic plus position)

 INTEROSSEI:
  • Dorsal (4): ABduct fingers (DAB), ulnar nerve
  • Palmar (3): ADduct fingers (PAD), ulnar nerve
  Damage (ulnar) → claw hand (ring + little), Wartenberg's sign

 OT: Intrinsic plus splint = MCP flexed, IP extended""",
    },

    "wrist_hand.flexor_tendons": {
        "caption": "Flexor tendons — zones, pulleys, FDS vs FDP, Jersey finger",
        "image_file": "carpal_bones.png",
        "diagram": """\
 FLEXOR TENDONS

 FDS (Flexor Digitorum Superficialis):
  • Flexes PIP joint (and MCP)
  • Median nerve (C7-T1)
  • Splits around FDP at Camper's chiasma

 FDP (Flexor Digitorum Profundus):
  • Flexes DIP joint (and PIP, MCP)
  • Digits 2-3: anterior interosseous (median)
  • Digits 4-5: ulnar nerve (C8-T1)
  • Jersey finger = avulsion of FDP from distal phalanx

 FLEXOR PULLEY SYSTEM (A1-A5 annular + C cruciate):
  • A2 (proximal phalanx) and A4 (middle phalanx) — most important
  • Pulley loss → bowstringing

 ZONES (I-V for repair prognosis):
  • Zone II ("no man's land") — FDS + FDP in fibro-osseous tunnel
    → Poorest surgical outcome, adhesion risk

 OT POST-OP PROTOCOLS:
  • Early active: Kleinert (modified) or place-and-hold
  • Dorsal blocking splint: wrist 20° flex, MCP 50° flex, IPs extended""",
    },

    # ── Dermatomes ────────────────────────────────────────────────────────────
    "dermatomes.upper_limb": {
        "caption": "Upper limb dermatomes C5–T1 — key landmarks for NBCOT",
        "image_file": "dermatomes.png",
        "diagram": """\
 UPPER LIMB DERMATOMES (C5–T1)

 C5 — Lateral arm (deltoid badge area, axillary nerve)
 C6 — Lateral forearm + thumb + index finger (musculocutaneous)
 C7 — Middle finger (median nerve territory)
 C8 — Ring + little fingers + medial forearm
 T1 — Medial arm (above elbow medial surface)

 QUICK MEMORY:
  C6 = thumb (6 looks like a thumb up)
  C7 = middle (C7 is the middle of the series)
  C8 = little (C8, small number → little finger)

 CLINICAL USES:
  • Dermatome testing → localise nerve root compression level
  • Spinal cord injury sensory level = most caudal intact dermatome
  • Peripheral vs radiculopathy: follows nerve vs dermatome distribution

 NERVE → DERMATOME CROSSWALK:
  Axillary N.         → C5 (lateral arm)
  Musculocutaneous N. → C6 (lateral forearm = lateral cutaneous nerve of forearm)
  Median N.           → C6 thumb, C7 middle
  Ulnar N.            → C8 little finger
  Medial cutaneous    → T1 medial arm""",
    },

    "dermatomes.clinical": {
        "caption": "Dermatomes clinical — radiculopathy vs peripheral nerve distribution",
        "image_file": "dermatomes.png",
        "diagram": """\
 DERMATOMES: CLINICAL DIFFERENTIATION

 RADICULOPATHY (nerve root):
  • C5 root compression → shoulder/lateral arm pain + weakness deltoid/biceps
  • C6 root → thumb/index numbness, biceps reflex diminished
  • C7 root → middle finger, triceps reflex diminished
  • C8 root → ring/little, intrinsic hand weakness

 PERIPHERAL NERVE INJURY (distinct from dermatomes):
  • Median nerve CTS → palmar surface 1st–3rd + half 4th finger (not proximal)
  • Ulnar nerve → medial palm + 4th–5th fingers (entire finger, not split)
  • Radial nerve → dorsal web space 1st–2nd finger (not as extensive as C7)

 KEY DIFFERENCE: Peripheral nerve = fixed anatomical field
                 Dermatome = variable, overlapping strips

 NBCOT FAVOURITES:
  • "Numbness over anatomical snuffbox" → radial nerve/superficial branch (C6-C7)
  • "Pins and needles at night in thumb/index" → CTS (median, C6)
  • "Numbness medial forearm after elbow surgery" → medial cutaneous (T1)""",
    },

    # ── Nerve injuries ────────────────────────────────────────────────────────
    "nerve_injuries.radial": {
        "caption": "Radial nerve injuries — wrist drop, spiral groove, PIN palsy",
        "image_file": "nerve_injury_syndromes.png",
        "diagram": """\
 RADIAL NERVE INJURIES

 HIGH (axilla / spiral groove):
  Wrist drop — loss of all wrist + finger extension
  Sensory: dorsum hand, 1st web space
  Cause: crutch palsy, Saturday night palsy (arm over chair), humeral shaft #

 POSTERIOR INTEROSSEOUS NERVE (PIN) (below elbow):
  Finger drop only — wrist extension preserved (ECRL intact)
  No sensory loss (PIN is pure motor)
  Cause: radial head fracture, radial tunnel syndrome

 OT SPLINTING:
  High radial palsy → wrist cock-up splint (keep wrist extended 30°)
  PIN palsy → MCP extension splint

 SPIRAL GROOVE (most common high injury):
  • Humerus mid-shaft fracture → nerve tethered at spiral groove
  • LOAF muscles not affected (median nerve)
  • Triceps spared if injury is in mid-shaft groove (branch above)

 RECOVERY: Radial nerve regenerates ~1mm/day
  • Brachioradialis returns first (most proximal muscle below injury)""",
    },

    "nerve_injuries.ulnar": {
        "caption": "Ulnar nerve injuries — claw hand, cubital tunnel, Guyon's canal",
        "image_file": "nerve_injury_syndromes.png",
        "diagram": """\
 ULNAR NERVE INJURIES

 HIGH (above elbow):
  • Loss: FDP 4th-5th, FCU + all intrinsics
  • Paradox: LESS claw at high injury (FDP paralysed too)

 LOW (wrist — Guyon's canal):
  • Loss: all intrinsics EXCEPT LOAF
  • Claw hand: ring + little fingers (hyperextended MCP, flexed IP)
    → "Intrinsic minus" due to loss of lumbrical + interosseous
  • Froment's sign: thumb IP flexion on pinch (FPL compensates)
  • Wartenberg's sign: little finger abducted at rest

 CAUSES:
  • Cubital tunnel: most common site, elbow flexion compresses
  • Guyon's canal: cyclists, hamate hook fracture
  • Medial epicondyle fracture (in children)

 OT SPLINTING:
  • Wrist splint in neutral + MCP block (anti-claw splint)
  • Prevent MCP hyperextension → IP extension becomes possible
  • Tip: splint only ring + little fingers""",
    },

    "nerve_injuries.median": {
        "caption": "Median nerve injuries — ape hand, CTS, anterior interosseous nerve",
        "image_file": "nerve_injury_syndromes.png",
        "diagram": """\
 MEDIAN NERVE INJURIES

 HIGH (above elbow — pronator teres or higher):
  Loss: LOAF + all FDS/FDP 2-3, FCR, pronators
  Ape hand: loss of opposition + thenar wasting
  Pointing index on fist (FDP 2-3 paralysed) — "Benediction sign"
  OK sign failure (anterior interosseous nerve — FPL + FDP 2-3)

 LOW (wrist — carpal tunnel syndrome):
  Spared: extrinsic forearm muscles (innervated above wrist)
  Lost: LOAF muscles (Lumbricals 1-2, Opponens, Abductor pollicis brevis, Flexor pollicis brevis)
  Symptoms: nocturnal paraesthesia, positive Phalen's, Tinel's at wrist

 LOAF MEMORY:
  L — Lumbricals 1 + 2
  O — Opponens pollicis
  A — Abductor pollicis brevis
  F — Flexor pollicis brevis (superficial head)

 OT:
  • CTS → wrist neutral splint (night use), nerve glides, ergonomic modification
  • High median → opponens splint to restore pinch""",
    },

    "nerve_injuries.brachial_plexus": {
        "caption": "Brachial plexus injuries — Erb's palsy, Klumpke's palsy, avulsion",
        "image_file": "brachial_plexus.png",
        "diagram": """\
 BRACHIAL PLEXUS INJURIES

 ERB'S PALSY (C5–C6, upper trunk):
  Cause: shoulder dystocia (birth), violent lateral neck stretch
  Posture: "Waiter's tip" — arm adducted, internally rotated, extended, forearm pronated
  Loss: Deltoid, supraspinatus, biceps, brachialis, brachioradialis
  Preserved: Hand intrinsics (C8-T1 intact)

 KLUMPKE'S PALSY (C8–T1, lower trunk):
  Cause: forceful arm abduction (grabbing overhead, birth)
  Loss: All intrinsic hand muscles, finger flexors
  Posture: Claw hand (intrinsic minus)
  If T1 sympathetics involved → Horner's syndrome (ptosis, miosis, anhidrosis)

 TOTAL PLEXUS INJURY (C5–T1):
  Flail anaesthetic limb

 OT MANAGEMENT:
  • Serial splinting to prevent contracture
  • Erb's: prevent shoulder ER/ABd contracture; assist hand-to-mouth
  • Klumpke: anti-claw splint, maintain passive ROM
  • Sensory re-education when reinnervation begins""",
    },

    # ── Upper limb muscles ────────────────────────────────────────────────────
    "upper_limb_muscles.shoulder": {
        "caption": "Shoulder muscles — deltoid, pectoralis major, latissimus dorsi",
        "image_file": "upper_limb_muscles.png",
        "diagram": """\
 SHOULDER MUSCLES (Gray408)

 DELTOID (axillary nerve, C5-C6):
  • Anterior: flexion + medial rotation
  • Middle: abduction 15–90°
  • Posterior: extension + lateral rotation
  Injection site; denervation → flat shoulder contour

 PECTORALIS MAJOR (medial + lateral pectoral nerves, C5-T1):
  • Clavicular head: flexion
  • Sternocostal head: extension from flexed position, adduction, medial rotation
  • Large fan-shaped; mastectomy → major functional loss

 LATISSIMUS DORSI (thoracodorsal nerve, C6-C8):
  • Extension, adduction, medial rotation of humerus
  • "Swimmer's muscle" / "crutch-walking muscle"
  • Key for transfers: powers shoulder depression + arm push

 TERES MAJOR (lower subscapular nerve, C5-C6):
  • Extension, adduction, medial rotation (mirrors lat dorsi)
  • "Little lat" — same actions, assists latissimus""",
    },

    "upper_limb_muscles.elbow_flexors": {
        "caption": "Elbow flexors — biceps, brachialis, brachioradialis innervations",
        "image_file": "upper_limb_muscles.png",
        "diagram": """\
 ELBOW FLEXORS

 BICEPS BRACHII (musculocutaneous nerve, C5-C6):
  • Long head: origin at supraglenoid tubercle (intra-articular)
  • Short head: coracoid process
  • Insertion: radial tuberosity + bicipital aponeurosis
  Actions: Elbow FLEXION + SUPINATION (most powerful supinator when elbow flexed)
  Test: flex elbow against resistance in supination

 BRACHIALIS (musculocutaneous nerve C5-C6; small radial contribution):
  • Pure elbow flexor regardless of forearm position
  • Strongest elbow flexor (larger cross-section than biceps)
  • Origin: distal half of anterior humerus

 BRACHIORADIALIS (radial nerve, C6):
  • Flexes elbow from mid-pronation/supination to neutral
  • "Handshake muscle" — acts in neutral forearm
  • Survives high radial nerve injury if below spiral groove
  • First muscle to show EMG activity after radial nerve repair

 REFLEXES: Biceps reflex → C5-C6""",
    },

    "upper_limb_muscles.elbow_extensors": {
        "caption": "Elbow extensors — triceps, anconeus; C7 radial nerve",
        "image_file": "upper_limb_muscles.png",
        "diagram": """\
 ELBOW EXTENSORS

 TRICEPS BRACHII (radial nerve, C6-C8, mainly C7):
  • Long head: infraglenoid tubercle of scapula
  • Lateral head: posterior humerus above spiral groove
  • Medial head: posterior humerus below spiral groove
  Insertion: olecranon process
  Action: elbow EXTENSION; long head assists shoulder extension + adduction
  Reflex: triceps reflex → C7

 ANCONEUS (radial nerve, C7-C8):
  • Small muscle, lateral to olecranon
  • Assists triceps in extension; stabilises elbow joint
  • Abducts ulna during pronation

 CLINICAL:
  • C7 radiculopathy → weak triceps, diminished triceps reflex
  • Spiral groove radial nerve injury → triceps usually spared
    (branch to long + medial heads arise proximal to groove)
  • Olecranon bursitis: superficial bursa over olecranon, not muscle injury

 OT CONTEXT:
  • Elbow extension powers push in transfers, dressing, weight-bearing
  • Triceps grade 3+ needed for functional transfers in SCI""",
    },
}


def get_image_for_topic(topic: str) -> dict | None:
    """Return best matching diagram dict for a topic/concept ID."""
    if not topic:
        return None
    if topic in ANATOMY_DIAGRAMS:
        return ANATOMY_DIAGRAMS[topic]
    # Try top-level prefix
    top = topic.split(".")[0]
    if top in ANATOMY_DIAGRAMS:
        return ANATOMY_DIAGRAMS[top]
    # Keyword scan
    topic_lower = topic.lower()
    for key, val in ANATOMY_DIAGRAMS.items():
        if key in topic_lower or topic_lower in key:
            return val
    return None
