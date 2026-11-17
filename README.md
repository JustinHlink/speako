# Speako

**For instructors:** start with the [step-by-step demo guide](docs/teacher-run.md): download, Windows/macOS setup, API configuration, login credentials and the complete walkthrough.

**Local demo login:** `learner1` / `SpeakoDemo2026!` after the setup below. Use `learner2` with the same password for account isolation, and `reviewer1` for the reviewer page.

Speako is a web app for beginner English learners. A learner signs in, starts a lesson and holds a short spoken conversation with an AI partner. The partner stays inside the lesson's word list and corrects important mistakes, and the lesson ends with a summary of the words used and the corrections made.

The app runs locally with Django and SQLite. A speech model on your own computer (Whisper `small.en`) turns the learner's speech into text, so recordings never leave the computer. Claude Haiku writes the partner's replies. The browser reads the replies aloud.

## Requirements

- Windows 10 or 11, macOS (Apple chip or Intel), or Linux (Ubuntu, Debian or similar)
- Python 3.10 to 3.13
- Chrome or Edge, and a microphone
- A Claude API key. Your team lead gives it to you privately (see [API key safety](#api-key-safety)).
- About 2 GB of free disk space and an internet connection for the first setup
- Node.js 18 or newer, only for the frontend tests

### Install Python (only if you do not have 3.10 to 3.13)

| System | How |
|---|---|
| Windows | Install Python 3.12 from [python.org](https://www.python.org/downloads/) and tick **Add python.exe to PATH**. Or run `winget install -e --id Python.Python.3.12` in PowerShell. |
| macOS | Install Python 3.12 from [python.org](https://www.python.org/downloads/), or run `brew install python@3.12` if you use Homebrew. |
| Linux | Ubuntu or Debian: `sudo apt install python3 python3-venv`. Other systems: use the package manager for Python 3.10 to 3.13 and its `venv` module. |

## 1. Get the code

```bash
git clone https://github.com/JustinHlink/speako.git
cd speako
```

You can also download the ZIP file from GitHub (Code > Download ZIP) and unzip it.

## 2. Set up (one step)

| System | Run this in the `speako` folder |
|---|---|
| Windows | Double-click `setup.bat`. Or run `.\setup.bat` in PowerShell. |
| macOS or Linux | `bash setup.sh` |

The setup asks for the Claude API key once. Typing is hidden. Paste the key and press Enter. Then the setup does the rest:

1. It creates the virtual environment `.venv` and installs the Python packages.
2. It creates `.env` from `.env.example` and saves the key in it. Git ignores `.env`, so the key never goes to GitHub.
3. It checks that the key works.
4. It creates the database with the lessons and their word lists.
5. It creates the demo accounts in the table below.
6. It downloads the speech model (about 464 MB, the first time only).

The first setup takes about 2 to 5 minutes. You can run the setup again at any time. It keeps what is already done, and it adds any new setting to an older `.env`.

| Username | Password | Role |
|---|---|---|
| `learner1` | `SpeakoDemo2026!` | Learner |
| `learner2` | `SpeakoDemo2026!` | Learner |
| `reviewer1` | `SpeakoDemo2026!` | Reviewer |
| `curator1` | `SpeakoDemo2026!` | Curator |

These are local demo accounts, not GitHub or API credentials. For a different password, set the `SPEAKO_DEMO_PASSWORD` environment variable (8 or more characters) before you run the setup.

## 3. Run

| System | Start | Stop |
|---|---|---|
| Windows | Double-click `start.bat` | Close the window, or press Ctrl+C |
| macOS or Linux | `bash start.sh` | Press Ctrl+C |

Open http://127.0.0.1:8001/ in Chrome or Edge, sign in with a demo account and allow the microphone. Keep the terminal window open while you use the app. Restart the app after you change `.env`.

## 4. Use a lesson

1. Start the lesson and listen to the partner's opening line.
2. Tap Record answer, speak, then tap Stop recording.
3. Check the text the app heard. Continue sends it to the partner. Try again discards it, and nothing is evaluated.
4. Tap Repeat slower to hear the partner's last line again at a slower pace.
5. After the last turn, the summary shows the target words you used, the words you did not use and each correction.

A lesson you leave early has no summary and shows as In progress. Your progress is saved to your account, so it is the same after you sign out and sign in again.

### Speech recognition limits

The speech model keeps beginner grammar mistakes such as "Me want the soup" or "Can I has the bill?". When two sounds join across words, it can mishear a word. For example, "I would likes tea" spoken quickly can come out as "I would like Steve". Always check the text before you tap Continue. If the text is wrong, tap Try again and speak a little more slowly.

## 5. Run the tests

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

The first command runs the Django tests. The second runs the frontend tests. The tests fake the speech model and the AI providers, and they run without the API keys in `.env`. So they make no API calls, download no model and use none of the budget.

## Settings in `.env`

The setup creates `.env` for you. Change a value only when you need to, then restart the app.

| Setting | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | (empty) | The Claude API key. Keep it only in `.env`. |
| `REPLY_PROVIDER` | `claude` | `claude` uses Claude Haiku for replies. `gemini` uses the earlier Gemini client. |
| `CLAUDE_MODEL` | `claude-haiku-5-5` | The only model the usage guard allows. |
| `SPEECH_PROVIDER` | `whisper` | `whisper` turns speech into text on this computer. `gemini` sends the recording to the Gemini API. |
| `WHISPER_MODEL` | `small.en` | `small.en` was the most accurate in our tests. `base.en` is smaller and faster, but it lost grammar mistakes in our tests. |
| `PROJECT_BUDGET_USD`, `MAX_API_ATTEMPTS` | `10`, `500` | The project-wide usage guard. |

The `GEMINI_*` settings are used only when a provider setting is `gemini`.

## API key safety

- Never put an API key in the repository, a commit, an issue, the shared document or a chat message. The repository is public, so anyone could use a key that is pushed.
- Each person keeps the key only in their own `.env`. Git ignores this file.
- The team lead shares keys privately, for example with a one-time secret link that expires after one view. A separate key for each person is best: the team lead can disable one key without stopping the others.
- If a key is exposed, disable it in the Claude Console at once and create a new one.

## API budget

Claude is used only for the partner's replies. Speech-to-text runs on your computer and costs nothing. The project has a $10 budget in total. The app records every API attempt in `db.sqlite3` and stops before the next call would go over `PROJECT_BUDGET_USD` or `MAX_API_ATTEMPTS`. The guard books at least $0.02 for each call, which is far more than a Claude Haiku reply costs, so the real spend stays well below the guard's total. Do not delete `db.sqlite3` to reset this record. Check real usage in the Claude Console.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Python 3.10 to 3.13 was not found" | Install Python 3.12 (see [Install Python](#install-python-only-if-you-do-not-have-310-to-313)), then run the setup again. |
| Linux: "Python could not create .venv" | Run `sudo apt install python3-venv` (or `python3.12-venv`), then `bash setup.sh` again. |
| Windows: Python is still not found after you installed it | Close the window, open a new one, and run the setup again. |
| "Claude rejected the API key" | Ask your team lead for a working key. Delete the value after `ANTHROPIC_API_KEY=` in `.env`, then run the setup again. |
| The speech model does not download | Check the internet connection and run the setup again. |
| The page says "Add your Claude API key" | Run the setup again, or add the key to `.env` and restart the app. |
| Port 8001 is already in use | Stop the other Speako window first (Ctrl+C). |

### Microphone problems

- Open http://127.0.0.1:8001/ in a normal Chrome or Edge window. Browsers allow the microphone on this local address without HTTPS.
- If the browser blocked the microphone, allow it from the icon in the address bar and reload the page.
- On Windows, open Settings > Privacy & security > Microphone and turn on microphone access and desktop app access. Then check Settings > System > Sound > Input for the right device.
- On macOS, open System Settings > Privacy & Security > Microphone and turn on access for Chrome or Edge.

### Manual setup (only if the setup script fails)

Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe setup_local.py
```

macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python setup_local.py
```

`setup_local.py` does steps 1 to 6 above.

### Optional: Conda

Instead of venv, run `conda env create -f environment.yml` and
`conda activate speako`. Then run `python setup_local.py` in the activated
environment for the remaining steps. Windows users can start the app with
`start_conda.bat` or `start_conda.ps1`. The recommended path is the setup script
above; the Conda scripts have been reviewed but not executed on this computer.

## Project layout

- `practice/`: the app (models, views, the progress rule in `progress.py`, the provider boundary in `providers.py`, the local speech model in `transcriber.py`, the Claude client in `claude.py`, the Gemini client, the vocabulary check), its templates, static files and tests
- `speako/`: Django settings and URLs
- `docs/`: the test plan and notes from the October prototype
- `setup.bat`, `setup.ps1`, `setup.sh`, `setup_local.py`: the one-step setup
- `start.bat`, `start.ps1`, `start.sh`: start the app

## Submission and demo version

For assessment, use the fixed tag `submission-sprint3-2026-11-04-r3` after it is
published, or the exact commit linked in the submission document. New work goes
through develop; tested submission changes are merged into main.
Do not move an existing submission tag. A new checkout needs the setup above
and a private local .env.

The app runs on localhost; a GitHub URL is source code, not a hosted website.
An instructor can follow sections 1 to 3 on their computer. A Claude API key is
required for live replies. No API key is included in submission files. Use the
instructor's own key or arrange authorized access privately. Do not copy the old
prototype database into the new schema.

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

Speech recognition runs on the computer, so it needs no network and has no API
limits. If the speech model cannot load or cannot read a recording, the app
says so, and the turn does not advance. Silence or noise gives "No clear speech
was detected", and nothing is evaluated.

If recognition fails, Retry this recording resends the audio retained in
browser memory for the current attempt. Recording again replaces it; successful
recognition clears it. Reloading the page loses the retained recording. Neither
failed recognition nor retry advances a conversation turn.

Claude replies are not retried automatically. A bad key, a rate limit, a
timeout or a declined reply shows a clear message, and the confirmed transcript
is kept for a manual Continue retry. The server logs the HTTP status or error
type, never the API key or raw audio.

No paid fallback or alternate provider is enabled automatically. Supply the key
privately in .env. Never commit credentials or publish them in the submission
document.

## Reviewer web page (Sprint 4)

Reviewer accounts can use `/review/` to inspect flagged responses and record
Acceptable or Incorrect decisions. Sign in as reviewer1 with the demo password.
Learner and Curator access is denied. The Curator web interface is not
implemented. See [Reviewer checks](docs/sprint4-reviewer.md).
