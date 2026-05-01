# UnMask — Socratic OT Anatomy Tutor

**CSE 635: NLP & Text Mining · University at Buffalo · Spring 2026**

---

## How the AI works

UnMask is a **multi-agent tutoring system**. Every message goes through an AI supervisor that decides which specialist to invoke:

| Agent | When | What it does |
|-------|------|--------------|
| 🩺 **Diagnostic** | First 2 min | Asks 4 calibration questions to map your prior knowledge |
| 📖 **Tutor** | Main session | Retrieves textbook chunks → asks Socratic questions grounded in the source |
| 🧪 **Assessment** | ~12 min in | Presents a clinical NBCOT-style scenario for free-text reasoning |
| 📋 **Wrap-up** | Final 1 min | Generates a personalised report: mastery breakdown, flashcards, study plan |

The supervisor's routing decision is shown **live** in each turn — not a black-box response.

---

## Session flow (~15 min)

```
Diagnostic (0–2 min)
  ↓  mastery priors calibrated
Tutoring (2–12 min)
  ↓  Socratic loop · visual aids · weak-topic revisit at ~8 min
Assessment (12–14 min)
  ↓  clinical scenario · free-text reasoning
Wrap-up (14–15 min)
  → session report · flashcards · diagram suggestions
```

---

## Progressive Context Revelation (PCR)

The tutor retrieves the correct answer from OpenStax A&P 2e — then **hides it** using a schema-level knowledge mask. As your mastery rises, more context is gradually revealed.

---

## Tips

- Type a number (1–10) or topic name to start
- Say **"show me a diagram"** for a visual aid at any time
- Say **"just tell me"** if you're stuck — the tutor explains directly
- Say **"I'm done"** to end early and get your report
