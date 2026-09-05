# ReconQ — The One Script You Actually Use

This replaces `SPEAKING_SCRIPT.md` and `RECORDING_RUNSHEET.md` — those still
exist if you want the split-out version, but this is the single file to have
open while you record. Every beat has three things: **SAY** (read it like you
mean it, not word-for-word), **SCREEN** (exactly what your hands do), and
**TIME** (roughly where you should be — if you're way off by the demo section,
you're talking too much in the intro).

This follows the structure that actually wins pitches — verified against how
YC Demo Day pitches and winning hackathon demos are built: **hook → problem →
the struggle → the turn → solution/demo → proof → close.** Most people skip
"the struggle" because it feels like admitting weakness. It's the opposite —
it's the single most human, most memorable part of the whole thing, and it's
also literally one of the things the judges said they read *instead of* your
resume. So it's not a footnote here anymore. It's load-bearing.

Total runtime target: **5 minutes.** Rough budget: 30s hook, 30s problem, 45s
struggle, 20s turn, 2 min demo, 45s proof, 30s close.

---

## BEAT 1 — The Hook (0:00 – 0:30)

**SCREEN:** Nothing yet. Face to camera, or a plain black screen if you're
doing voiceover-first. Don't open the app yet — the biggest mistake is
leading with your product before anyone cares about the problem.

**SAY:**

"So a few weeks ago I sat down and actually did what a Razorpay merchant does
every single day.

**(pause)**

I opened their settlement report. I opened their internal ledger. And I tried
to match them up by hand.

**(pause — let this be a little uncomfortable)**

It took me twenty minutes to do what should've taken twenty seconds. And I
kept thinking — somebody at a real company does this every single morning,
before their coffee's even done."

---

## BEAT 2 — The Problem (0:30 – 1:00)

**SCREEN:** Still no app. If you want a visual here, this is where the two
CSVs side-by-side, or the two demo files from `demo-script/` opened in a text
editor, could flash up for a second — optional, not required.

**SAY:**

"Here's the actual problem. Every day, a merchant gets a settlement file from
the gateway — what actually got paid out, after fees. And they've got their
own ledger — what their systems think was sold. These two never match
perfectly. Fees, timing delays, split payments, duplicates.

Most tools handle that with one rule: if the model's more than eighty-five
percent confident, just auto-clear it.

**(pause, then slower, more direct)**

But a two-hundred rupee mismatch and a four-lakh rupee mismatch are not the
same kind of wrong. Getting the small one wrong costs you nothing. Getting
the big one wrong could be a real financial mess. Every tool I looked at
treats them exactly the same anyway."

---

## BEAT 3 — The Struggle (0:45 – 1:30)

*This is the beat most people cut. Don't cut it. This is your actual answer
to "what broke and how did you get out" — and it's true, which is why it'll
land better than anything scripted.*

**SCREEN:** Still face-to-camera or a simple slide. No app yet.

**SAY:**

"So I built the obvious version first. Confidence score, one threshold,
done. And it worked — right up until I ran it twice on the exact same data
and got two different sets of matches.

**(pause)**

Same input. Different output. For a financial reconciliation tool, that's
not a small bug — that's the kind of thing that makes an auditor never trust
your system again. I dug into it and found a non-deterministic hash function
buried in how I was ordering match candidates. It wasn't caught by a single
test I'd written, because none of my tests checked for run-to-run
consistency — I'd only tested that it got the *right* answer once, not that
it got the *same* answer every time.

**(beat)**

That was the moment I almost just shipped the naive version and called it
done. Instead I sat with it, fixed the ordering to be fully deterministic,
and then — more importantly — wrote the test that would've caught it in the
first place. That test's still in the suite today."

---

## BEAT 4 — The Turn (1:30 – 1:50)

**SCREEN:** This is where you can cut to the app for the first time — just
sitting on the empty Dashboard, nothing clicked yet.

**SAY:**

"And that's actually what pushed me toward the real idea. If I couldn't
trust a flat threshold to even be consistent, I definitely couldn't trust it
to make the *same* call on a ₹200 transaction and a ₹4,00,000 one.

So instead of one confidence bar, ReconQ uses one that rises with the amount.
Small transactions clear at seventy-five percent confidence. Anything over a
lakh needs ninety-seven."

---

## BEAT 5 — Live Demo (1:50 – 4:00)

*This is the longest section on purpose — judges said they want to see it
actually run, not hear you describe it.*

**5a — Run it (1:50–2:20)**

**SCREEN:** Click **"Use Sample Data."** Let the full pipeline animation
play — don't talk over all of it, let 2 seconds of it breathe in silence.
When the comparison banner lands, stop clicking. Let the number sit.

**SAY:**

"Let me just show you instead of describing it.

*(click)*

Exact matches clear first — free, instant. Everything else gets bucketed,
scored by a trained model, and run through an optimal assignment step so
nothing gets claimed twice.

*(results land — pause half a second before the next line)*

And here's the number that actually matters."

**5b — The proof number (2:20–2:45)**

**SCREEN:** Comparison banner is on screen, the red hero number visible.
Don't scroll yet.

**SAY:**

"Fifteen lakh, fifty-nine thousand, six hundred and thirty-six rupees.
That's what a flat eighty-five percent threshold would've auto-cleared —
wrongly — on this one run. Same model. Same data. My engine caught every
single one of those and held them for a human instead.

**(pause, let it sit)**

Eighty-four point four percent match rate. One point one six crore cleared
instantly. Twenty items held back on purpose."

**5c — Exceptions + the AI guardrail (2:45–3:20)**

**SCREEN:** Click **Exceptions** in the sidebar. Click into any
`HUMAN_REVIEW` item with a mid-range confidence (80-90% reads best on
camera). Let the detail panel render. Then click **"Get Suggested Fix"** —
this is a real API call, 3-8 seconds, keep talking through it.

**SAY:**

"Every one of those held-back items lands here, side by side with its ledger
record, with the exact reason it needed a human.

*(click Get Suggested Fix)*

This part I was the most careful about. Most AI reconciliation tools just
let a language model guess a fix. I didn't want that — not with real money.

*(panel appears — point at, don't click, the cross-check badge)*

Every number this proposes gets checked against the actual evidence before
it's ever shown to you. If it invents a figure — the whole thing gets
thrown out, you get an honest fallback instead. And even when it passes,
approving it only writes to an audit log. Nothing gets sent anywhere. A
human still executes the real fix."

**5d — Anomalies, audit trail, and the honest API (3:20–3:50)**

**SCREEN:** Click **Anomalies**, let the leakage strip render. Click
**Audit Log**, let the table render. Click back to **Dashboard**, click
**Re-run**, click the **"Direct Razorpay API Sync"** tab, click **Sync**.

**SAY:**

"It's also watching for leakage — fee overcharges, duplicates, missing
payouts. Twelve point seven lakh flagged, just in this run. And every
decision, system or human, gets written to an append-only log. There's no
update route, no delete route, anywhere in this codebase for that table. I
genuinely can't go back and quietly rewrite a financial audit trail. So I
didn't build a way to.

*(click into Razorpay sync tab)*

One more thing — this isn't a mockup of talking to Razorpay. This calls the
real Settlements API, with real credentials, right now.

*(click Sync — react honestly to whatever comes back)*

If there's live data, it runs through this exact same pipeline. If there
isn't — like on a fresh test account — it tells you that, honestly, instead
of quietly faking something to look good. I'd rather show you something true
than something perfect."

**5e — Copilot (3:50–4:00)**

**SCREEN:** Open Copilot, click a suggested question. Let the real response
stream in fully.

**SAY:**

"And if you don't want to dig through any of it — you can just ask.

*(response streams in)*

It's reading your actual numbers. Not guessing."

---

## BEAT 6 — Proof / Why This Matters (4:00 – 4:30)

**SCREEN:** Cut back to the comparison banner or a simple recap slide.

**SAY:**

"To be clear about what this is and isn't — this ran on a synthetic dataset,
because I don't have a live merchant's real ledger. But the model, the
scoring, the risk policy, the audit log — every one of those runs exactly the
same way on real Razorpay settlement data, because I built it against
Razorpay's actual Settlements API from day one, not bolted on after."

---

## BEAT 7 — Close (4:30 – 5:00)

**SCREEN:** Either let the last screen sit, or cut to a plain title card:
**ReconQ.**

**SAY:**

"I didn't build this to look impressive in a demo. I built it because a
₹200 mistake and a ₹4,00,000 mistake are not the same problem, and I think
that's the first thing any real reconciliation tool should know.

**(pause)**

That's ReconQ."

**(Stop talking. Stop clicking. Let 2 full seconds of silence sit on the
final frame before you cut. Don't say "okay that's it" on camera — that one
habit undoes more good demos than any script mistake.)**

---

## Fast reference — if you only remember five things

1. **Don't skip Beat 3.** The struggle story is not optional filler — it's
   your real, true answer to "what broke and how did you get out," and it's
   the most human 45 seconds in the whole video.
2. **Let silence do work.** After the ₹15,59,636 number, after "that's
   ReconQ" — stop. The pause is not dead air, it's the point.
3. **Never apologize on camera.** If the Razorpay sync shows the empty
   state, or you fumble a click, that's not a failure moment — react like
   you meant it to happen, because functionally, the honesty *is* the
   feature.
4. **Don't re-explain what's on screen.** If the UI already shows "84.4%
   match rate" in giant text, don't just read it back — say what it *means*
   instead.
5. **Do one full silent dry-run first** (see `RECORDING_RUNSHEET.md`'s
   pre-flight section) so the LLM calls are warm and you already know which
   exception item you're clicking into — you should never be hunting for
   something on camera.
