# ReconQ — Recording Runsheet

One sheet, glanceable while you record. Left = what you say (verbatim from
`SPEAKING_SCRIPT.md` — don't retype it, this just tells you *when*). Right =
exactly what your hands do. Do the pre-flight first — recording with the app
in a messy state is the #1 way this goes wrong.

---

## PRE-FLIGHT — do this before you press record, not during

**1. Kill anything already running, start clean:**
```bash
lsof -ti:8000,3000 | xargs kill -9 2>/dev/null
```

**2. Start the backend** (own terminal tab, leave it running, minimize it):
```bash
cd /path/to/reconq
source .venv/bin/activate
uvicorn api.main:app --reload
```
Wait for `Application startup complete.` before moving on.

**3. Start the frontend** (second terminal tab):
```bash
cd /path/to/reconq/frontend
npm run dev
```

**4. Open a fresh browser window** — not a tab in your normal browsing
window. New window, nothing else in it. Go to `http://localhost:3000`.
- Zoom to 100% (`Cmd+0`) so text sizing looks right on recording.
- Resize the window to roughly 1600×900 or fullscreen it. Don't record a
  tiny window — it'll be unreadable once you upload/compress the video.
- Close DevTools if it's open. Judges don't need to see your console.

**5. Confirm the app is in its true empty state** — refresh the page once
(`Cmd+R`). You should see "No reconciliation run yet." If you see old
results from earlier testing, that's a stale state — refresh again or
restart the frontend dev server.

**6. Do one silent dry-run before recording for real** — click "Use Sample
Data," click into Exceptions, click "Get Suggested Fix" once. This is not
wasted time: it warms up the Gemini/Groq connection so your *real* take
doesn't have a longer-than-expected cold-start delay, and it lets you see
which exception item you'll click on so you're not hunting for one on camera.
Then refresh the page again to reset before your actual take.

**7. Recording software** — whatever you use (QuickTime screen recording,
OBS, Zoom's "record" if that's what you have access to), do a 10-second
test clip first and actually play it back. Check: is there audio, is the
screen sharp, is your mic loud enough. Do this once, not after your third
full take.

**8. Have `SPEAKING_SCRIPT.md` open on a second monitor or printed out.**
Do not try to read it on the same screen you're recording.

---

## THE TAKE — say / click, in order

Each row: what you say (from `SPEAKING_SCRIPT.md`, just the section name so
you can find it) → what your hands do, in the same beat.

| # | You're saying... | Your hands do this |
|---|---|---|
| 1 | **Opening** — "Every day, a Razorpay merchant downloads two files..." | Nothing on screen yet, or a black slide if you're inserting one. Face-to-camera or voice-over-black is fine here. |
| 2 | **The number** — "So here's what that actually costs..." | Cut to browser, already loaded on Dashboard, empty state. As you say "here's what that actually costs," click **"Use Sample Data."** Let the pipeline animation play fully — don't talk over the whole thing, let 2-3 seconds of it breathe silently. When the comparison banner lands, stop clicking anything — let the ₹15,59,636 number sit on screen while you deliver "Same model. Same data. Our engine caught every single one." |
| 3 | **What it actually is** — "I built ReconQ because of that gap..." | No new clicks. Either stay on the comparison banner or slowly scroll down to reveal the KPI cards as you talk — one slow scroll, not fidgety. |
| 4 | **Running it live** — "Let me just... show you." | You already ran it in step 2 — don't re-click "Use Sample Data" here, that would look repetitive. Instead: scroll to the KPI cards + charts (Match Rate, Auto-Cleared, donut, bar chart) and let your narration ("exact matches clear first, then bucketing...") play over you slowly panning across them. |
| 5 | **Exceptions — the human part** | Click the **Decisions** icon or nav item briefly is optional — the script goes straight to Exceptions, so click **Exceptions** in the left sidebar. Click into any item in the queue that's tagged `HUMAN_REVIEW` (pick one with a mid-range confidence, like 80-90% — it reads better on camera than a 20% one). Let the record detail panel render fully before you keep talking. |
| 6 | (continuing Exceptions) — "This is the part I was most careful about..." | Click **"Get Suggested Fix."** This is a real API call — it takes 3-8 seconds. Don't panic-fill the silence; the script already has you talking through the wait ("Most AI reconciliation tools just let a language model guess..."). When the panel appears, point your cursor at (don't click) the **"CROSS-CHECK PASSED"** badge while you say that line. |
| 7 | **Anomalies and the audit trail** | Click **Anomalies** in the sidebar. Let the leakage summary strip render, say the ₹12.7L line over it. Click **Audit Log** in the sidebar. Let the event table render — no need to click into anything, just let it sit on screen while you deliver the append-only line. |
| 8 | **The Razorpay API part** — "One more thing." | Click back to **Dashboard**. Click **"Re-run"** (top of the results bar) to get back to the upload screen. Click the **"Direct Razorpay API Sync"** tab. Let the "Connected to Razorpay Test API" box render — pause half a second so it's readable. Click **"Sync & Reconcile."** Whatever comes back (empty-state message, or real data if you've since gotten test settlements) — react to it honestly in the moment, the script has a line for either outcome. |
| 9 | **Copilot** | Click the **Copilot** button at the bottom of the sidebar. Click one of the suggested-question chips — **"What's my overall match rate?"** is the one the script assumes. Let the real response stream in fully before you say "It's reading your actual numbers." |
| 10 | **Close** | Either cut to black/a title card, or just let the Copilot response sit on screen. Say your last line, then **stop talking and stop clicking.** Let 2 full seconds of silence sit on the final frame before you cut the recording. This is the single most "professional video" thing you can do — resist the urge to say "okay that's it" or fumble for the stop button on camera. |

---

## IF SOMETHING GOES WRONG MID-TAKE

- **A click doesn't register / page looks wrong** — don't restart the whole
  recording. Pause, take a breath, say "let me try that again," redo the
  click. You'll cut the flub out in editing. One clean 5-minute take with
  zero mistakes is not realistic and looks worse when people can tell you're
  tense about it.
- **The LLM call takes longer than expected** — keep talking, use the
  filler lines already written for you in that section, or just let it be
  quiet for a couple extra seconds. A real wait is more convincing than a
  cut, not less.
- **Razorpay sync shows the empty-state message** — that's not a failure,
  that's the honest answer, and the script already has a line for it. Don't
  apologize on camera. Say it like you mean it.

---

## AFTER THE TAKE

1. Watch the whole thing back once, full screen, sound up, before you touch
   an editor. Note timestamps of anything genuinely broken (not just
   "I stumbled on a word" — that's fine, that's editable).
2. Trim dead air at the very start and very end, and cut any long pauses
   where you visibly got lost — but leave the *intentional* pauses from
   the script alone, those are doing real work.
3. Export at 1080p minimum. Don't compress it into oblivion for file size —
   a blurry demo undersells a working product.
