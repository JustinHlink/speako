# Speako

Local Django prototype for guided beginner English speaking practice. First milestone: one restaurant scenario, five successful exchanges, transcript confirmation, real Gemini feedback, browser playback and a local summary.

## Run on Windows

Project folder: `C:\Users\Justin\Desktop\SE\speako`.

1. Create the isolated environment if not already present:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` if `.env` does not already exist. In Google AI Studio create an API key for a project with **no Cloud Billing enabled**. Enter it only in the local `.env` file. Set `GEMINI_FREE_TIER_CONFIRMED=true` after checking that project's free-tier status. Do not paste keys into chat or commit them.
3. Double-click `start.bat`, or run `powershell -NoProfile -File .\start.ps1`.
4. Open `http://127.0.0.1:8001/` in current Chrome or Edge. Allow the microphone when you choose Record. Keep the terminal open. Stop with Ctrl+C. Restart after changing `.env`.

## Run on macOS

1. Create the isolated environment if not already present. Use Python 3.10 or newer (for example Homebrew `python3`); the system `/usr/bin/python3` may be too old for Django 5.2:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```
   With the python.org installer, run its "Install Certificates.command" once, otherwise Gemini requests fail with SSL certificate errors.
2. Copy `.env.example` to `.env` (`cp .env.example .env`) and fill it in exactly as in Windows step 2.
3. Run `./start.sh` from the project folder.
4. Open `http://127.0.0.1:8001/` in current Chrome. Allow the microphone when you choose Record. In System Settings > Privacy & security > Microphone, enable access for your browser, then quit and reopen it if it was already running. Keep the terminal open. Stop with Ctrl+C. Restart after changing `.env`.

Verify with `.venv/bin/python manage.py check` and `.venv/bin/python manage.py test`.

Without a key the real application opens and explains setup; it never substitutes scripted AI responses. There is no login, deployment, reviewer dashboard or curator editor in this milestone. Browser-local sessions persist in SQLite; this is not account-based progress.

## Practice

- Start the lesson, listen, click Record, then Stop. Recordings stop automatically after 30 seconds.
- Review the recognized text. Continue submits it; Try again discards it and never evaluates or summarizes it.
- A failed API request keeps the turn unchanged. Retry explicitly. There is no automatic extra API call.
- Repeat slower replays the last AI line without advancing a turn.
- At five successful exchanges, completion is stored before the summary appears. The summary lists used/unused target words and every correction; no extra Gemini summary call is made.
- Early exit creates no summary. Restart begins from the opening question.

## API use and $10 budget

Gemini is used **only for transcription and conversational replies/corrections**. No image generation, search, translation, summary generation or UI creation calls. Playback uses browser speech synthesis. Audio is sent to Gemini for transcription and is not stored in project files.

Default model: `gemini-3.1-flash-lite`. No paid models or automatic billing fallback. Your subscription to the Gemini app is separate from API billing. The app cannot inspect or disable your Google Cloud billing account; you must confirm the API project is unbilled. Official free-tier services may have data-use conditions; check the provider terms before recording personal information.

The budget is **$10 total across development, testing and instructor review**, not per session. SQLite records all network attempts, including failed/invalid ones, across local sessions. Each attempt reserves at least $0.02 from a conservative local guard. Successful token counts use paid-price-equivalent rates of $0.50/M input tokens (audio rate used conservatively for all input) and $1.50/M output tokens. This is **not an invoice or a claim of actual spending**. Model rates were checked against official documentation on October 10, 2026.

`RECORDED_EXTERNAL_SPEND_USD` can account for usage outside this app. Calls stop before the next local reservation would exceed $10 or the configured attempt limit. Do not delete `db.sqlite3` to reset the ledger. If teammates use separate copies, their ledgers are separate: consolidate exported measurements and actual provider usage for the whole project. Verify actual charges in AI Studio; a local guard cannot guarantee a provider-wide billing cap.

## Timing comparison

Every relevant step shows actual elapsed time beside a suggested target. These are prototype comparison targets, not measured promises or approved course acceptance criteria:

| Step | Suggested target | What is measured |
|---|---:|---|
| Page ready | ≤ 1.5 s | Navigation start through initial state rendering |
| Microphone ready | ≤ 1 s | Record click through permission/device acquisition; first permission wait included |
| Speech recognition | ≤ 5 s | Stop processing through upload, Gemini transcription and returned transcript |
| AI response | ≤ 5 s | Continue click through Gemini feedback and saved state |
| Playback start | ≤ 1 s | Speech request through the browser's actual `onstart` event |
| Summary | ≤ 0.5 s | Local summary calculation and completion save; does not make an API call |
| System wait | ≤ 11 s | Successful transcription + AI reply + playback startup; excludes learner speaking and review |

Human speaking and transcript-review times are shown without a pass/fail target. Browser timings include network round trips; exported server timings are separate. Speaking duration itself is not a latency defect. Targets turn amber if exceeded; failed steps are recorded as failures. Browser timing history is local; API history is in the project database. Export test measurements to JSON for comparison. Refreshing shows the saved session but does not replay audio automatically.

## Verify

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Tests mock the provider and make no API calls. They verify discard behavior, retries, duplicates, silence, completion, early exit, access isolation and budget guards. They do not prove real speech accuracy, AI correction correctness or latency. Live verification requires your key and microphone. See `docs/test-plan.md` and `docs/prototype-plan.md`.

## Version management

- `main`: validated local milestones; features are developed on a separate branch.
- Focused commits separate project setup, core conversation, UI/measurement and verification.
- `v0.1.0`: initial code-complete prototype before live API validation.
- `v0.1.1`: configured free-tier model, working local port, real five-exchange API validation and feedback checks. Human microphone and broad latency validation remain pending.
- `.env`, `.django-secret`, recordings, databases and virtual environments never enter Git.
- To inspect a version without losing changes: `git status`, then `git switch -c inspect-v0.1.0 v0.1.0` with a clean working tree.
- To undo a published commit, use `git revert <commit>` and push the new undo commit. Avoid force-pushing shared history.

## Requirements boundaries

This is the one-scenario spike, not the full requirements MVP. US-11 and US-12 are central. US-04 slower replay and a subset of US-05/09/10/18 are implemented. Account-based US-16, review US-06/13, help US-17, curator authoring US-19 and four additional scenarios remain. US-07 specifically names Customs; the restaurant scenario does not complete it. AI vocabulary screening blocks replies/examples outside the configured lists, but factual correction quality still requires human review. The full five-lesson 90% requirement has not been verified.

Sources: [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Generate content API](https://ai.google.dev/api/generate-content), [Django 5.2](https://docs.djangoproject.com/en/5.2/).

## Observed live results (October 10, 2026)

Five synthetic English sample recordings completed the real transcription -> confirmation endpoint -> AI feedback -> persisted summary flow. The summary correctly listed used and unused words. Recognition ranged from 1.54 to 13.93 seconds in that run: two of five recognition steps exceeded the 5-second comparison target. AI replies ranged from 0.73 to 1.16 seconds; local summary calculation/save took about 2 ms. This is a small controlled sample, not a 50-turn spike or a human microphone test.

Separate confirmed-text tests returned a short correction/example for "I would likes tea please" and gentle redirection without a correction for "I like football". The synthetic audio grammar-error sample was recognized in a corrected form, so preserving spoken grammatical errors is an unresolved transcription-quality risk. The transcription prompt was strengthened, but that change has not yet been verified against human recordings. Do not present transcription as reliably verbatim until measured.

See `docs/live-api-check.json` and `docs/live-feedback-check.json` for non-personal test fixtures and measurements. These results record real generation calls. The API ledger remains local and includes development failures; exported reports are not billing invoices.


## Microphone troubleshooting

If site permission is allowed but recording fails, compare the same local URL (`http://127.0.0.1:8001/`) in a standalone Chrome or Edge window. Embedded browser access and Windows permission may differ from the site's permission. In Windows Settings > Privacy & security > Microphone, enable microphone access, app access and desktop app access. Check System > Sound > Input for the selected device. No audio or Gemini request is sent when microphone startup fails.

The page now distinguishes access blocking, missing devices and device startup failures. An access-blocked error alone cannot identify which permission layer rejected the request. Human microphone verification remains pending.

Supportive beginner language (for example, "No problem" and "Try") is allowed alongside lesson target words. Unsure learners should receive menu choices; off-topic answers should receive gentle redirection without being labeled incorrect. Output validation failures refer to the AI reply, not the learner’s English. This does not guarantee every generated reply will pass vocabulary validation.
