# Speako: instructor demo setup

Submission version: **submission-sprint3-2026-11-04-r3**

Speako runs on your own computer. The GitHub page contains source code, not a hosted application. This tag preserves the tested restaurant implementation and expanded setup instructions; the previous tag remains unchanged.

## 1. Requirements

- Python 3.12 recommended (supported: 3.10–3.13).
- Normal Chrome or Edge, microphone, and speakers/headphones.
- Internet and a privately configured Gemini API key for live recognition/replies.
- Git is optional with the ZIP download. Node.js is needed only for frontend tests.

## 2. Download this version

**Without Git:** open the [submission release](https://github.com/JustinHlink/speako/releases/tag/submission-sprint3-2026-11-04-r3), download **Source code (zip)**, and extract it. Open the folder containing `manage.py`, `requirements.txt` and `.env.example`.

**With Git:**

```text
git clone --branch submission-sprint3-2026-11-04-r3 https://github.com/JustinHlink/speako.git speako-demo
cd speako-demo
```

Use this tag rather than a moving development branch.

## 3. Install and configure — Windows PowerShell

Open PowerShell in the folder containing `manage.py`. Run one line at a time:

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

If `py` is unavailable but `python --version` works, replace `py` with `python` in the first two commands. If neither works, install Python and reopen PowerShell. No virtual-environment activation is required.

In Notepad, set the following values and save the file:

```dotenv
GEMINI_API_KEY=PASTE_YOUR_REAL_KEY_HERE
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_FREE_TIER_CONFIRMED=true
```

Replace the key placeholder with your actual key. Use the exact filename `.env`, not `.env.txt`. Leave the other settings at their defaults. Set the confirmation flag only after verifying that the key's project has no billing enabled.

Use your own key from [Google AI Studio](https://aistudio.google.com/apikey), or obtain the team's authorized key privately. See [Google's key setup instructions](https://ai.google.dev/gemini-api/docs/api-key). The public source does not contain the team's real key. The local demo password below is not an API key. Never put a real key in the public repository, document, screenshot or recording.

Without the key you can start the server and sign in, but live speaking practice will be unavailable. Restart Django after changing `.env`.

## 4. Create the database and demo accounts — Windows

Back in PowerShell, run:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo_users --password "SpeakoDemo2026!"
```

`migrate` creates the database and seeds the restaurant lesson and vocabulary. The second command creates/resets these local accounts:

| Username | Password | Role | Demo use |
|---|---|---|---|
| `learner1` | `SpeakoDemo2026!` | Learner | Main restaurant walkthrough |
| `learner2` | `SpeakoDemo2026!` | Learner | Separate account progress |

These are local demonstration credentials, not GitHub or API credentials. They exist on your computer only after running the seed command. If you use a different password in that command, use it for the learner accounts instead. Rerunning the command resets the local demo passwords without creating duplicates.

## 5. Start the app — Windows

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --insecure --noreload
```

Keep this terminal open. In normal Edge or Chrome, open **http://127.0.0.1:8001/**. Ctrl+C stops the server. The `--insecure` flag serves CSS/JavaScript from Django's localhost development server when DEBUG is off; this command is not a public deployment configuration.

If port 8001 is occupied, use 8002 in both the command and browser address. Sign in again when changing browsers or switching between localhost and 127.0.0.1.

## 6. macOS / Linux equivalent

Open Terminal in the extracted project folder:

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Open `.env` in a text editor and set the same API values from step 3. Dot files may be hidden in your file browser. Then run:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo_users --password 'SpeakoDemo2026!'
.venv/bin/python manage.py runserver 127.0.0.1:8001 --insecure --noreload
```

Open http://127.0.0.1:8001/ and use the same demo accounts. Windows setup was checked locally; macOS/Linux commands are provided but were not executed on this computer.

## 7. Complete demo walkthrough

1. Sign in at the top of the page with **learner1 / SpeakoDemo2026!**.
2. Under **Choose a lesson**, select **Ordering at a Restaurant**. Inspect its goal and target words. Restaurant is the only seeded scenario in this submission.
3. Click **Start practice** or **Start new practice** and listen to the waiter. A Completed lesson can be practised again.
4. Click **Repeat slower**. The latest waiter line replays more slowly without adding a turn.
5. Click **Record answer**, allow microphone access, speak, then click **Stop recording**. Recording also stops automatically after 30 seconds.
6. Read **Did we hear you correctly?**. Choose **Try again** once: the text is discarded without evaluation. Record again, check the text, then choose **Continue**.
7. Follow the waiter's current question. Read any correction and hear the reply. Timing tags show actual time and suggested targets; Gemini can exceed those targets.
8. After **five accepted answers**, inspect the saved summary: words used, words unused and corrections. If there were no corrections, the page says **No corrections were made during this lesson.**
9. Sign out and sign back in as learner1. The lesson remains Completed. Click **View last summary** to reopen the saved result.
10. Sign out and sign in as **learner2 / SpeakoDemo2026!**. A fresh learner2 has its own progress, not learner1's result. Accounts previously used for practice may already have their own attempts.

Possible answers, depending on the actual waiter question:

```text
Yes, please.
I would like chicken with rice, please.
Can I have some water, please?
No, thank you.
Can I have the bill, please?
```

AI wording may vary. Check the behavior rather than exact wording: lesson constraints, correct turn handling and appropriate correction/redirection. Leaving before five accepted answers creates no summary and leaves map progress as In progress.

## 8. Troubleshooting

| Symptom | Action |
|---|---|
| Connection refused / page unavailable | Keep the Django terminal running and match the browser port to the command. |
| Missing table / no seeded restaurant | Run migrate in the same environment used for the server. |
| Sign-in fails | Rerun the seed command, then enter learner1 and SpeakoDemo2026! exactly. |
| Sign in above to choose a lesson | Sign in on this page; GitHub sign-in does not sign you into Speako. |
| API not ready | Check the exact .env filename, actual key and free-tier confirmation, then restart Django. |
| Microphone blocked | Use normal Chrome/Edge; allow the microphone for this local site and in Windows/macOS privacy settings. |
| HTTP 503 / timeout during recognition | One retry happens automatically. After failure, use Retry this recording to resend retained audio, or Record answer to replace it. Reloading loses retained audio. |
| Quota/rate limit (429) | Wait and check AI Studio allowance. There is no paid fallback; do not repeatedly retry. |
| AI reply fails after confirmation | The text remains pending. Retry Continue; failed replies do not add a turn. |
| No spoken reply | Read the text, check speaker volume and an English browser/system voice, then try Repeat slower. |
| Plain page / old buttons | Use the server flags shown above and hard-refresh with Ctrl+F5 on Windows. |

Do not delete a used project database to troubleshoot: it contains progress and usage accounting. If using the team's project key, coordinate one designated live environment at a time. Retain its ledger and recorded external usage when switching computers so the project-wide budget is not reset.

## 9. Optional tests and verification

Node.js is needed only for frontend tests. In a second terminal in the project folder:

Windows:

```powershell
.\.venv\Scripts\python.exe manage.py test practice
Get-ChildItem practice\tests_*.cjs | ForEach-Object { node $_.FullName }
```

macOS / Linux:

```bash
.venv/bin/python manage.py test practice
for f in practice/tests_*.cjs; do node "$f"; done
```

The implementation passed 115 Django tests and all six frontend check files. These simulate AI/network responses and use no live API quota. A separate real-Gemini five-turn test with synthesized English speech completed, saved and reopened its summary, and passed account isolation. See [validation details](submission-validation.md).

Provider uptime and suggested timing targets are not guaranteed. Check the actual microphone/browser playback on the presentation computer. Continue development through feature branches/develop, and create a new tag for later submission changes rather than moving this one.
