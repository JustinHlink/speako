# Speako

**For instructors:** start with the [step-by-step demo guide](docs/teacher-run.md): download, Windows/macOS setup, API configuration, login credentials and the complete walkthrough.

**Local demo login:** `learner1` / `SpeakoDemo2026!` after running the seed command below. Use `learner2` with the same password for account isolation.

Speako is a web app for beginner English learners. A learner signs in, starts a lesson and holds a short spoken conversation with an AI partner. The partner stays inside the lesson's word list and corrects important mistakes, and the lesson ends with a summary of the words used and the corrections made.

The app runs locally with Django and SQLite. Gemini turns the learner's speech into text and writes the partner's replies. The browser reads the replies aloud.

## Requirements

- Python 3.10 to 3.13
- Chrome or Edge, and a microphone
- A Gemini API key from Google AI Studio, on a project with no billing
- Node.js 18 or newer, only for the frontend tests

## 1. Install

Windows (PowerShell):

```powershell
git clone https://github.com/JustinHlink/speako.git
cd speako
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS or Linux:

```bash
git clone https://github.com/JustinHlink/speako.git
cd speako
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### Optional: Conda

Instead of venv, run `conda env create -f environment.yml` and
`conda activate speako`. Use `python manage.py ...` in the activated environment
in place of the .venv Python paths below. Windows users can use
`start_conda.bat` or `start_conda.ps1`. The recommended assessment path is venv;
Conda scripts have been reviewed but not executed on this computer.

## 2. Configure

Copy `.env.example` to `.env` (Windows: `copy .env.example .env`, macOS or Linux: `cp .env.example .env`). Then set these two values in `.env`:

| Setting | Value |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key. Keep it only in `.env`. |
| `GEMINI_FREE_TIER_CONFIRMED` | `true`, after you check that the key's Google project has no billing. |

The other settings can keep their default values. `.env`, `.django-secret` (created on the first run) and `db.sqlite3` are never committed.

## 3. Create the database and the demo data

Windows:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo_users --password "SpeakoDemo2026!"
```

macOS or Linux:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo_users --password "SpeakoDemo2026!"
```

- `migrate` creates the tables and the restaurant lesson with its word lists.
- `seed_demo_users` creates the demo accounts. The demo uses pre-created accounts; the registration API always creates Learners.

| Username | Password after the seed command above | Role |
|---|---|---|
| `learner1` | `SpeakoDemo2026!` | Learner |
| `learner2` | `SpeakoDemo2026!` | Learner |
| `curator1` | `SpeakoDemo2026!` | Curator |
| `reviewer1` | `SpeakoDemo2026!` | Reviewer |

The commands above set all four local demo passwords to `SpeakoDemo2026!`. If you choose a different password in the seed command, use it instead (8 or more characters). These are local demo credentials, not GitHub or API credentials. You can also set `SPEAKO_DEMO_PASSWORD` instead of `--password`. Running the command again resets the passwords and roles and never makes duplicate accounts.

## 4. Run

- Windows: double-click `start.bat`, or run `powershell -NoProfile -File .\start.ps1`.
- macOS or Linux: run `.venv/bin/python manage.py runserver 127.0.0.1:8001 --insecure --noreload`.

Open http://127.0.0.1:8001/ in Chrome or Edge, sign in with a demo account and allow the microphone. Keep the terminal open while you use the app. Ctrl+C stops it. Restart the app after you change `.env`.

## 5. Use a lesson

1. Start the lesson and listen to the partner's opening line.
2. Tap Record answer, speak, then tap Stop recording.
3. Check the text the app heard. Continue sends it to the partner. Try again discards it, and nothing is evaluated.
4. Tap Repeat slower to hear the partner's last line again at a slower pace.
5. After the last turn, the summary shows the target words you used, the words you did not use and each correction.

A lesson you leave early has no summary and shows as In progress. Your progress is saved to your account, so it is the same after you sign out and sign in again.

## 6. Run the tests

Windows:

```powershell
.\.venv\Scripts\python.exe manage.py test practice
Get-ChildItem practice\tests_*.cjs | ForEach-Object { node $_.FullName }
```

macOS or Linux:

```bash
.venv/bin/python manage.py test practice
for f in practice/tests_*.cjs; do node "$f"; done
```

The first command runs the Django tests. The second runs the frontend tests. The tests fake the AI provider, so they make no API calls and use none of the budget.

## API budget

Gemini is used only for speech-to-text and for the partner's replies. The project has a $10 budget in total. The app records every API attempt in `db.sqlite3` and stops before the next call would go over `PROJECT_BUDGET_USD` or `MAX_API_ATTEMPTS`. Do not delete `db.sqlite3` to reset this record. The numbers are an estimate, so check real usage in Google AI Studio.

## Microphone problems

- Open http://127.0.0.1:8001/ in a normal Chrome or Edge window. Browsers allow the microphone on this local address without HTTPS.
- If the browser blocked the microphone, allow it from the icon in the address bar and reload the page.
- On Windows, open Settings > Privacy & security > Microphone and turn on microphone access and desktop app access. Then check Settings > System > Sound > Input for the right device.

## Project layout

- `practice/`: the app (models, views, the progress rule in `progress.py`, the Gemini client, the vocabulary check), its templates, static files and tests
- `speako/`: Django settings and URLs
- `docs/`: the test plan and notes from the October prototype


## Submission and demo version

For assessment, use the fixed tag `submission-sprint3-2026-11-04-r2` after it is
published, or the exact commit linked in the submission document. New work goes
through feature PRs and develop; tested submission changes are merged into main.
Do not move an existing submission tag. A new checkout needs dependencies,
migrations, seeded accounts and a private local .env.

The app runs on localhost; a GitHub URL is source code, not a hosted website.
An instructor can follow sections 1–4 on their computer. A working unbilled
Gemini project is required for live speech recognition and replies. A Gemini
chat subscription does not configure API access. No API key is included in
submission files. Use the instructor's own project or arrange authorized access
privately, and retain the project's usage accounting when switching the single
live environment. Do not copy the old prototype database into the new schema.

For live demonstration: sign in as learner1, select the restaurant, record,
discard one transcript, record again, confirm, repeat the reply slowly, finish
five accepted turns, inspect the summary, then sign out and back in. Sign in as
learner2 to verify isolation. Frontend tests use simulated browser devices; an
actual microphone and voice playback still need checking on the demo computer.

The fixed beginner list includes service function words and common contractions.
An off-list AI candidate is hidden and may be rewritten once through the same
budget guard. Invalid candidates never advance a turn; a second rejection or
provider failure keeps the transcript for retry. There is no unlimited retry
or paid fallback. See docs/reply-recovery.md.

This candidate contains the restaurant lesson. Other scenarios are not claimed
as completed by this demo. Review and curriculum interfaces without a completed
UI should not be listed in the learner demo script as working pages.

## Provider errors and recovery

Speech recognition retries once for a transient network failure or HTTP
500/502/503/504 response, with a 12-second timeout per attempt. Both network
attempts reserve budget separately. Quota/key/request-format errors do not
retry automatically. The server logs the HTTP status or exception category,
never the API key or raw audio.

If recognition still fails, Retry this recording resends the audio retained in
browser memory for the current attempt. Recording again replaces it; successful
recognition clears it. Reloading the page loses the retained recording. Neither
failed recognition nor retry advances a conversation turn. Conversation-provider
errors preserve the confirmed transcript for a manual Continue retry.

No paid fallback or alternate provider is enabled. External service failures can
still prevent live recognition or replies; a tag and passing simulated tests do
not guarantee Gemini availability. Supply the instructor's key privately in
.env, or let the instructor configure their own unbilled project. Never commit
credentials or publish them in the submission document.
