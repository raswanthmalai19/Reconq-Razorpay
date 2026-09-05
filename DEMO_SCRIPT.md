# ReconQ — 5-Minute Demo Video Script

**Tone:** Calm, confident, unhurried. Steve Jobs keynote pacing — let the numbers
breathe. No hype words ("revolutionary," "game-changing"). Let the ₹ figure and
the clean UI do the emotional work. Speak slower than feels natural; silence
after a big number is more powerful than the next sentence.

**Voice:** One narrator, mid-low register, minimal inflection swings. Think
the restrained cadence of an Apple keynote, not a hype-reel voiceover.

**Music:** Sparse, single sustained pad/piano note under the cold open. Introduce
a soft rhythmic pulse the moment the dashboard first appears. Let it build
almost imperceptibly toward the 3:40 mark, then drop out entirely for the
close so the last line lands in near-silence.

**Screen recording:** 1920x1080, cursor hidden or minimal, no visible mouse
jitter — use smooth scripted scroll/click, not live mouse-hunting. Record every
segment separately and cut; do not attempt one continuous take.

---

## SCENE 1 — Cold Open (0:00 – 0:25)

**Visual:** Black screen. No logo yet.

**On-screen text (white, centered, appears letter by letter, slow):**
> Every day, a Razorpay merchant downloads two files.

*(beat — 1.5s pause, text fades)*

> A settlement report. And a ledger.

*(beat)*

> They almost never match.

**Visual:** Cut to a fast, silent montage — two CSV files side by side, a
finance person visibly scrolling through rows (stock-style hands-on-keyboard
shot, or simple animated spreadsheet mockup). No voiceover yet. 3 seconds.

**On-screen text:**
> Most tools fix this with one rule: if confidence is above 85%, clear it.

*(beat)*

> A ₹200 mismatch and a ₹4,00,000 mismatch get treated exactly the same.

**Visual:** Screen goes black again. Single line of white text, largest text
in the whole video, center screen:

> **That's wrong.**

*(hold for 2 full seconds — let it sit)*

---

## SCENE 2 — The Number (0:25 – 0:55)

**Voiceover begins here — first spoken line of the video.**

> "The cost of being wrong scales with the amount. So we built a reconciliation
> engine that knows that."

**Visual:** Hard cut to the ReconQ dashboard, already mid-scroll to the
comparison banner. Don't show the upload screen yet — open on the payoff.

**On-screen:** The red hero card fills the frame:
### ₹15,59,636

**Voiceover:**
> "This is what a flat 85% threshold would have auto-cleared, wrongly, on a
> single day's settlements. Our engine — same machine learning model, same
> data — caught every single one of them."

*(beat, let the ₹ number sit on screen alone for 1.5s, no VO)*

**Visual:** Slow push-in on the naive-vs-risk-weighted comparison cards
(red "Flat 85%" card vs green "Risk-Weighted" card).

**Voiceover:**
> "124 auto-cleared instead of 135. Eleven transactions — including one
> at ninety percent confidence — held back for a human to look at first."

---

## SCENE 3 — What This Actually Is (0:55 – 1:30)

**Visual:** Cut to a clean title card. Simple, centered, no clutter:

### ReconQ
**Risk-Weighted Payment Reconciliation, built for Razorpay merchants.**

**Voiceover:**
> "ReconQ is a reconciliation engine. It takes your Razorpay settlements and
> your internal ledger, and instead of asking 'does this look like a match,'
> it asks 'how much would we lose if we're wrong — and does this confidence
> clear that bar.'"

**Visual:** A simple animated diagram builds on screen, left to right, one
stage lighting up at a time, in sync with the voiceover:

`Settlement CSV → Exact Match → ML Scoring → Risk-Weighted Policy → Decision`

**Voiceover:**
> "Exact matches clear instantly. Everything else gets scored by a trained
> model, then checked against a threshold that rises with the amount —
> seventy-five percent for small transactions, ninety-seven percent for
> anything over one lakh rupees."

---

## SCENE 4 — Live Demo: Running It (1:30 – 2:20)

**Visual:** Screen recording, Dashboard page, upload tab visible.

**Voiceover:**
> "Let's run it."

**Action on screen:** Click **"Use Sample Data."** Let the pipeline animation
play in full — don't cut it short, this is a genuinely satisfying visual
(stage-by-stage progress bar: Exact Match → Blocking → ML Scoring → Hungarian
Assignment → Risk Policy → Anomaly Detection → Done).

**Voiceover (during the animation, sparse, let it breathe):**
> "Exact matches first. Then bucketing, so it never compares every record
> against every other record. Group detection, for split payments. A trained
> logistic regression scores what's left. And a global optimal assignment —
> the Hungarian algorithm — makes sure no record gets claimed twice."

**Visual:** Results land. Cut immediately to KPI cards animating in
(Match Rate, Auto-Cleared, In Review, Unresolved, Bank Confirmed, Leakage).

**Voiceover:**
> "84.4% match rate. ₹1.16 crore auto-cleared, instantly. Twenty items held
> for review — not because the model failed, but because the policy did
> exactly what it was designed to do."

**Visual:** Slow pan across the two charts — status distribution donut,
volume-by-amount-band bar chart.

---

## SCENE 5 — Exceptions: The Human-in-the-Loop (2:20 – 3:10)

**Voiceover:**
> "Every transaction the system isn't confident about lands here."

**Action on screen:** Navigate to **Exceptions**. Click into one flagged item.
Let the two-column settlement/ledger comparison render.

**Voiceover:**
> "Side by side — the settlement record, the ledger record, and exactly why
> this one needed a human: confidence below the threshold for this amount band."

**Action on screen:** Click **"Get Suggested Fix."** Wait for the real Gemini
response to stream in — do not fake or speed this up, the 3-5 second wait is
part of the credibility.

**Voiceover (while it loads):**
> "This is where most AI reconciliation tools get dangerous. They let a
> language model guess. We don't."

**Visual:** The Suggested Fix panel appears — zoom in on the
**"CROSS-CHECK PASSED"** badge and the explanation text.

**Voiceover:**
> "Every number this model proposes is checked against the actual evidence
> before it's ever shown to you. If it invents a figure that isn't in the
> data, the proposal is thrown out and you get an honest template instead.
> And even when it passes — approving it only writes to an audit log. Nothing
> is sent externally. No ledger is touched. A human always executes the fix."

---

## SCENE 6 — Anomalies & the Audit Trail (3:10 – 3:50)

**Action on screen:** Navigate to **Anomalies**.

**Voiceover:**
> "Beyond matching, it's also watching for money leaking out quietly —
> fee overcharges, duplicate settlements, missing payouts."

**Visual:** Show the leakage summary strip, then expand one anomaly card.

**Voiceover:**
> "₹12.7 lakh flagged at risk in this run alone."

**Action on screen:** Navigate to **Audit Log**. Show the filterable event
table.

**Voiceover:**
> "And every decision — system or human — is written here, append-only.
> There is no update or delete route anywhere in this codebase. You cannot
> quietly rewrite history in a financial audit trail. So we didn't build
> a way to."

---

## SCENE 7 — The Razorpay API, For Real (3:50 – 4:25)

**Voiceover:**
> "One more thing."

*(intentional callback pause — let it land, then continue)*

**Action on screen:** Switch to **"Direct Razorpay API Sync"** tab. Show the
"Connected to Razorpay Test API" state with the real key prefix visible.

**Voiceover:**
> "This isn't a mockup of an integration. This calls Razorpay's real
> Settlements API, with real credentials, live."

**Action on screen:** Click **Sync & Reconcile**. Let the honest empty-state
message appear naturally (or, if you've generated test settlements by then,
show the real synced data instead — either is fine, both are true).

**Voiceover (adapt to whichever state is on screen):**
> "If your account has real settlements, they flow through this exact same
> pipeline — same scoring, same risk policy, same audit log. And if it
> doesn't — like a fresh test account — it tells you that honestly, instead
> of quietly making something up to look impressive. We think that's what
> a tool you'd actually trust with your money should do."

---

## SCENE 8 — Copilot (4:25 – 4:45)

**Action on screen:** Open the **Copilot** panel, type or click a suggested
question: *"What's my overall match rate?"*

**Voiceover:**
> "And if you just want the answer without digging — ask."

**Visual:** Let the real streamed response render, including the markdown
table.

**Voiceover:**
> "It's reading your actual results. Not guessing."

---

## SCENE 9 — Close (4:45 – 5:00)

**Visual:** Cut to black. Music drops out almost entirely — one held note.

**On-screen text, one line at a time, slow:**
> Reconciliation that knows the difference
> between a rounding error and a real problem.

*(beat, 2s)*

**Final card, centered, simple:**
### ReconQ
**Built for Razorpay merchants. Built to be trusted.**

*(hold 3 seconds, fade to black, no sound)*

---

## Production notes

- **Record screen segments separately** at each scene boundary — don't try
  one continuous take. Re-run "Use Sample Data" fresh for Scene 4 so the
  pipeline animation plays cleanly on camera.
- **Never speed up or trim the AI response waits** in Scenes 5 and 8 — a
  real 3-5 second pause while a live LLM call resolves is more convincing
  than an instant cut, because it visibly proves it isn't canned.
- **Do the Razorpay live sync take last**, right before recording Scene 7,
  so whatever state your account is actually in that day is what you narrate
  to — don't pre-script which outcome you'll get.
- **Keep zooms/pushes slow and few** — one per scene, max. Constant motion
  reads as amateur; stillness reads as confidence.
- **Total spoken word count is intentionally light** (~550 words across 5
  minutes) — most of this video is silence, visuals, and pacing, exactly
  like the keynotes it's modeled on. Resist the urge to fill every second
  with narration.
