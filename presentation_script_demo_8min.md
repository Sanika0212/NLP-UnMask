# UnMask — 8-Minute Demo Script
# UI walkthrough + conversation flow only. No background. Simulate button drives the convo.

**Pacing note:** Spoken words are sparse — most time is watching the simulation run.
Italics = action cue. Plain text = what you say out loud.

---

## [0:00 – 0:30] Open the app, orient the audience

*Open UnMask. Let the landing page sit for a second.*

So this is UnMask — an AI tutor for OT students prepping for the NBCOT exam.

*Point to the three panels.*

Left rail is the topic progress tracker. Center is the conversation. Right panel is the instructor view — mastery scores, retrieval mode, and the misconception log. In the real student build that right panel is hidden. We've surfaced it for the demo so you can see what's happening under the hood.

---

## [0:30 – 1:00] Show the Simulation Panel, configure it

*Click the 🤖 FAB button in the bottom-right corner. The panel expands.*

That robot button opens the Auto-Simulate panel. This is what drives the demo — it plays a scripted student through a full tutoring session so you can watch the whole conversation flow without me typing.

*Set topic to "Brachial Plexus". Set mode to "Visual".*

I'm picking Brachial Plexus and Visual mode. Visual mode means the system will inject anatomy diagrams at the right moments.

*Click "Load fresh session for this topic". Wait for "Session ready".*

That sets up a clean session — new session ID, mastery reset to zero, empty misconception log.

*Set Msg delay to 2s, Typing to 38ms/c, Start delay to 3s.*

Two-second gap between messages so you can read what's happening. Three-second countdown before it starts.

*Click "▶ Run simulation". Panel auto-minimizes.*

---

## [1:00 – 2:00] Rapport phase + first diagnostic questions

*Countdown ticks 3…2…1. First message types in: "Let's start →"*

The session opens with a short rapport exchange — the system asks for the student's weak topic and learning style. That's already baked into the session setup we just ran, so it skips straight to diagnostics.

*Watch Q1: student types "C5, C6, C7, C8 and T1" — correct answer.*

First diagnostic question. Student answers the spinal levels correctly.

*Watch the left rail. The Brachial Plexus bar ticks up slightly.*

See the mastery bar on the left nudge up. That's Bayesian Knowledge Tracing — each correct response shifts the probability estimate.

*Watch Q2: student types "I don't know all five terminal branches" — IDK.*

Student doesn't know the terminal branches. The system doesn't give the answer. Watch what it does instead — it asks a targeted sub-question to scaffold.

*Watch the right panel — misconception log gets an entry.*

A misconception just logged: terminal branches unknown. That entry will come back later when the system decides to revisit.

*Watch Q3: student types "There are two trunks — upper and lower" — wrong.*

Wrong answer on trunks. The system responds with a Socratic question — it doesn't correct outright. It redirects.

*Watch Q4: student answers correctly.*

Correct. Mastery bar ticks up again.

---

## [2:00 – 3:15] Tutoring phase — misconceptions and the auto-diagram trigger

*Watch Q5: student types "I think the lateral cord gives rise to the radial nerve" — wrong.*

Now we're in the tutoring phase. Student makes a wrong claim about cord origins.

*Watch the bot response — a question, not a correction.*

The system asks: what structure sits between the cords and the terminal nerves? Still Socratic even when the student is wrong.

*Watch Q6: student types "Maybe all anterior divisions combine into just the median nerve?" — wrong.*

Second wrong answer in a row. This is the trigger for the automatic diagram.

*Watch — an anatomy diagram renders inline in the chat.*

There it is. The brachial plexus diagram animates in directly inside the conversation. That's not an image file — it's an SVG-based HTML block that highlights the relevant structure. The system injects it automatically after two consecutive wrong answers.

*Watch Q7: student types "Show me a diagram of that".*

Student explicitly asks for a diagram too. The system serves a different view of the same structure.

*Watch Q8: student types "Can I see a different diagram?"*

And a third variant. We have 22 local diagrams per topic — the system rotates through them.

*Watch Q9: student types "I don't know — can you explain?"*

Student asks for an explanation. Watch — the bot explains, but framed as another question at the end. It can't fully stop being Socratic.

---

## [3:15 – 4:30] Five correct answers — watch mastery unlock

*Watch Q10 through Q14 — five consecutive correct answers.*

Now the student is getting it right, one after another. Watch the mastery bar on the left.

*Point to the rail as it fills.*

Each correct answer compounds. The BKT model is tracking consecutive correct responses specifically — five in a row is the threshold to advance the mastery gating. Once it crosses 0.7, the retrieval planner starts allowing answer chunks through.

*Watch retrieval mode label in right panel — should flip from "prerequisite_first" to "full".*

Right panel just flipped retrieval mode from "prerequisite first" to "full." That means the vector DB filter is now open — the model can retrieve answer-containing context. The student earned it.

---

## [4:30 – 5:30] Assessment phase + misconception revisit

*Watch Q15: student types the wrong assessment answer.*

Assessment phase now. The question is clinical: here's a patient with a specific deficit, what's the lesion level? Student gets it wrong.

*Watch bot response — still a question, more targeted now.*

The bot narrows in. It's not asking "what do you know about the brachial plexus" anymore — it's referencing the specific misconception from earlier. That's the stored misconception being injected back into the generator prompt.

*Watch Q16: student types the correct answer — "Erb's palsy — C5 C6 injury causing waiter's tip posture".*

Correct. Full clinical reasoning — structure, level, presentation. Mastery at or near 1.0 now.

*Watch the right panel mastery row for Brachial Plexus hit green.*

---

## [5:30 – 6:30] End session — wrapup, summary, YouTube recs

*Watch Q17: student types "end session".*

Student ends the session. Watch the wrapup trigger.

*Watch the center panel transition to the wrapup/progress view.*

The system generates a structured session summary: per-concept mastery status, list of misconceptions encountered during the session, and...

*Point to the YouTube recommendations section.*

...two to four YouTube video recommendations, personalized to the weakest concepts from this session. These are generated by the same Socratic generator using the mastery state at wrapup time.

*Click through to the Progress view on the left rail if it switched there.*

The left rail now shows the full mastery breakdown across all 16 concepts in the prerequisite DAG — not just brachial plexus. Concepts the student touched are colored; untouched are grey.

---

## [6:30 – 7:15] Instructor view walkthrough

*Open or point to the right Aside panel.*

Let me walk through the instructor panel quickly. 

Top section: current PCR mode — this is what I just showed flipping from "prerequisite first" to "full" during the session.

Middle: per-concept mastery scores, live. These are the same BKT floats the retrieval filter reads.

Bottom: the misconception log. Every entry here is a structured object — topic, the specific wrong claim, and the turn it was captured on. This fed directly back into the assessment phase you just watched.

This panel exists so instructors or researchers can monitor a session in real time. Students never see it.

---

## [7:15 – 8:00] Wrap up and close

*Return to the chat panel. The session summary is visible.*

So what you just watched was a full diagnostic-to-assessment loop: the system started with zero knowledge of this student, ran Bayesian mastery estimation across the session, gated what context the model could see based on demonstrated understanding, caught and logged misconceptions as they happened, revisited them at assessment, and generated a personalized summary at the end.

The student never got the answer handed to them. The model couldn't give it even if it tried — until the filter opened.

That's UnMask. Thank you.

---

*Total spoken: ~900 words. Remaining ~5–6 min is the simulation running. 
If the sim finishes early, slow down on the instructor panel walkthrough or replay one topic. 
If running long, cut [6:30–7:15] entirely and go straight to the close.*
