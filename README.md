# Speako

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

If you prefer Conda over `venv`, create and activate the environment using `environment.yml` (configured with Python 3.10 and matching `requirements.txt`):

```bash
conda env create -f environment.yml
conda activate speako
```

When using Conda:
- Follow steps 2 through 6 using `python manage.py ...` inside the activated `speako` environment instead of the `.venv` paths.
- On Windows, you can also launch the app by running `powershell -NoProfile -File .\start_conda.ps1` or double-clicking `start_conda.bat`.

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
.\.venv\Scripts\python.exe manage.py seed_demo_users --password <choose-a-password>
```

macOS or Linux:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo_users --password <choose-a-password>
```

- `migrate` creates the tables and the restaurant lesson with its word lists.
- `seed_demo_users` creates the demo accounts. There is no public sign-up.

| Username | Role |
|---|---|
| `learner1` | Learner |
| `learner2` | Learner |
| `curator1` | Curator |
| `reviewer1` | Reviewer |

All four accounts use the password you choose (8 or more characters). You can also set `SPEAKO_DEMO_PASSWORD` instead of `--password`. Running the command again resets the passwords and roles and never makes duplicate accounts.

## 4. Run

- Windows: double-click `start.bat`, or run `powershell -NoProfile -File .\start.ps1`. (If using Conda, double-click `start_conda.bat` or run `powershell -NoProfile -File .\start_conda.ps1`.)
- macOS or Linux: run `.venv/bin/python manage.py runserver 127.0.0.1:8001` (or `python manage.py runserver 127.0.0.1:8001` in your activated Conda environment).

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
