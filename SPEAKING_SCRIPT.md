# ReconQ — Just The Talking Part

This is only what comes out of your mouth. No camera directions, no scene
numbers, nothing technical to remember. Read it out loud to yourself twice
before you record — not to memorize word-for-word, but so it stops sounding
like something you're reading and starts sounding like something you know.

Where you see **( … )** — that's a pause. Actually pause. Longer than feels
natural. That's the part people mess up — they rush through silence because
it feels awkward to them, but it doesn't feel awkward to the person watching.

Where a line has a slash, like "so — here's the thing," that's a breath,
not a full stop. Let it run together like actual speech.

---

### Opening

"So — every day, a Razorpay merchant downloads two files.

**(pause)**

A settlement report. And their own ledger.

**(pause)**

And they almost never match.

Most tools deal with that with one rule — if the model's more than 85%
sure, just clear it. Done.

**(pause — let this land before the next line)**

But a two-hundred rupee mismatch and a four lakh rupee mismatch aren't the
same problem. They get treated like they are anyway.

**(pause, then, quieter, more direct)**

That's just... wrong."

---

### The number

"So here's what that actually costs.

*(cut to screen — dashboard visible)*

This right here — fifteen lakh, fifty-nine thousand, six hundred and
thirty-six rupees. That's what a flat eighty-five percent threshold would've
auto-cleared. Wrongly. On one day's worth of settlements.

**(pause, let the number sit)**

Same machine learning model. Same data. Our engine caught every single one."

---

### What it actually is

"I built ReconQ because of that gap.

It's a reconciliation engine — but instead of asking 'does this look like a
match,' it asks something closer to how an actual finance person thinks
about risk: how much do we lose if we're wrong, and does this confidence
level actually clear that bar for this amount.

So small transactions — seventy-five percent confidence is fine.
Anything over a lakh — it needs ninety-seven."

---

### Running it live

"Let me just... show you.

*(click 'Use Sample Data', let it run)*

Exact matches clear first — those are basically free. Then it buckets what's
left so it's not comparing every record against every other record. A
trained model scores the rest. And an optimal assignment step makes sure
nothing gets claimed twice.

*(results land)*

Eighty-four point four percent match rate. One point one six crore cleared,
instantly. Twenty items held back — not because the model failed, but
because the policy did exactly what it's supposed to do."

---

### Exceptions — the human part

"Now — every one of those held-back items lands here.

*(click into Exceptions, open one)*

Settlement record, ledger record, side by side. And right here it tells you
exactly why a human needs to look — confidence came in under the bar for
this amount band.

*(click 'Get Suggested Fix', let it actually load)*

This is the part I was most careful about. Most AI reconciliation tools
just let a language model guess. We don't do that.

*(fix appears — point at cross-check badge)*

Every number this thing proposes gets checked against the real evidence
before you ever see it. If it makes something up — the whole proposal gets
thrown out, you get an honest fallback instead. And even when it passes —
approving it only writes to an audit log. Nothing gets sent anywhere.
Nothing touches your actual ledger. A human still does that part."

---

### Anomalies and the audit trail

"It's also watching for money leaking out quietly — fee overcharges,
duplicate settlements, payouts that never showed up.

*(Anomalies page)*

Twelve point seven lakh flagged, just in this run.

*(Audit Log page)*

And every decision — the system's or a human's — gets written here.
Append-only. There's no update route, no delete route, anywhere in this
codebase for this table. You genuinely cannot go back and quietly rewrite
a financial audit trail. So — I didn't build a way to."

---

### The Razorpay API part

"One more thing.

**(pause — small callback, let it register)**

This isn't a mockup of talking to Razorpay. This is calling the real
Settlements API, with real credentials, right now.

*(click Sync)*

If there's live data, it runs through this exact same pipeline. And if
there isn't — like right now, on a fresh test account — it just tells you
that. Honestly. Instead of quietly faking something to look impressive.

I'd rather show you something true than something perfect."

---

### Copilot

"And if you don't want to dig through any of it —

*(open Copilot, ask the question)*

— you can just ask.

*(let the real response render)*

It's reading your actual numbers. Not guessing."

---

### Close

"Reconciliation that actually knows the difference between a rounding error
and a real problem.

**(pause)**

That's ReconQ."

**(stop talking. let the last screen hold. don't fill the silence.)**

---

## Two honest notes for you, not for the camera

**On stumbling:** if you flub a line while recording, don't restart the
whole take from scratch — pause, take a breath, say the sentence again.
You'll cut it in editing. Nobody needs to see you do this in one perfect
pass, they need the final cut to sound like one perfect pass.

**On "what broke and how you got out"** — if the judges ask this live, or
you want a beat for it in the video: you actually have a true, specific
answer, don't invent one. Say something like — *"the ugliest bug was a
non-deterministic hash function — the same input was producing different
match results on different runs, which for a financial audit trail is
about as bad as it gets. Found it during manual verification, not by a
test. Fixed it, and then wrote the test that would've caught it."* That's
real, it's specific, and it's exactly the kind of answer that lands better
than a rehearsed one.
