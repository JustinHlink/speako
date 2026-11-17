# Speako: instructor demo setup

Sprint 4 version: the **develop** branch

Speako runs on your own computer. The GitHub page holds the source code, not a hosted app. The Sprint 3 tag `submission-sprint3-2026-11-04-r3` stays unchanged. This guide covers the Sprint 4 version, which adds the one-step setup, the customs lesson, reply flags and the reviewer page.

## 1. Requirements

- Python 3.10 to 3.13 (3.12 recommended).
- Normal Chrome or Edge, a microphone, and speakers or headphones.
- An internet connection, a Claude API key and a Groq API key. Groq turns speech into text, and Claude Haiku writes the partner's replies.
- About 2 GB of free disk space for the first setup.
- Git is optional with the ZIP download. Node.js is needed only for the frontend tests.

## 2. Download this version

**Without Git:** download the [develop ZIP file](https://github.com/JustinHlink/speako/archive/refs/heads/develop.zip) and extract it. Open the folder that contains `manage.py`, `setup.bat` and `setup.sh`.

**With Git:**

```text
git clone --branch develop https://github.com/JustinHlink/speako.git speako-demo
cd speako-demo
```

## 3. Install and configure: Windows

In the project folder, double-click `setup.bat`. You can also open PowerShell in that folder and run:

```powershell
.\setup.bat
```

The setup asks for the Claude key and then the Groq key. Typing is hidden: paste each key and press Enter. The setup then does the rest by itself:

1. It creates the virtual environment `.venv` and installs the Python packages.
2. It creates `.env` and saves both keys in it.
3. It checks that both keys work.
4. It creates the database with the lessons and their word lists.
5. It creates the demo accounts in step 4.
6. It downloads the local speech model, the backup for Groq (about 464 MB, first time only).

The first setup takes about 2 to 5 minutes. You can run it again at any time: it keeps what is already done.

If Python is missing, the setup says so. Install Python 3.12 from [python.org](https://www.python.org/downloads/) and tick "Add python.exe to PATH", or run `winget install -e --id Python.Python.3.12`. Then open a new window and run `setup.bat` again.

Use your own keys, or get the team's keys privately from the team. Claude keys come from the [Claude Console](https://console.anthropic.com/settings/keys) and start with `sk-ant-`. Groq keys come from the [Groq console](https://console.groq.com/keys) and start with `gsk_`. The keys stay only in your local `.env`, which Git ignores. Never put a real key in the repository, a document, a screenshot or a recording. The demo password below is not an API key.

## 4. Create the database and demo accounts: Windows

The setup in step 3 already did this. It creates or resets these local accounts:

| Username | Password | Role | Demo use |
|---|---|---|---|
| `learner1` | `SpeakoDemo2026!` | Learner | Main walkthrough |
| `learner2` | `SpeakoDemo2026!` | Learner | Separate account progress |
| `reviewer1` | `SpeakoDemo2026!` | Reviewer | Reviewer page for flagged replies |
| `curator1` | `SpeakoDemo2026!` | Curator | Shows that a Curator cannot open the reviewer page |

These are local demo accounts, not GitHub or API credentials. They exist on your computer only after the setup. Running the setup again resets the demo passwords without creating duplicates. For a different password, set `SPEAKO_DEMO_PASSWORD` (8 or more characters) before you run the setup.

## 5. Start the app: Windows

Double-click `start.bat`. Keep the window open. In normal Edge or Chrome, open **http://127.0.0.1:8001/**. Close the window or press Ctrl+C to stop the server.

If port 8001 is in use, stop the other Speako window first. Sign in again when you change browsers or switch between localhost and 127.0.0.1. Restart the app after you change `.env`.

## 6. macOS / Linux equivalent

Open Terminal in the extracted project folder and run:

```bash
bash setup.sh
```

The setup asks for the same two keys and does the same six steps as on Windows. Then start the app:

```bash
bash start.sh
```

Open http://127.0.0.1:8001/ and use the same demo accounts. Press Ctrl+C to stop.

If Python is missing, install Python 3.12 from [python.org](https://www.python.org/downloads/) or run `brew install python@3.12` on macOS. On Ubuntu or Debian, run `sudo apt install python3 python3-venv`. The Windows setup was tested on our computers. The macOS and Linux script has not yet been run on a Mac.

## 7. Complete demo walkthrough

1. Sign in at the top of the page with **learner1 / SpeakoDemo2026!**.
2. Under **Choose a lesson**, select **Ordering at a Restaurant**. Look at its goal and target words.
3. Click **Start practice** or **Start new practice** and listen to the waiter. You can practise a completed lesson again.
4. Click **Repeat slower**. The latest waiter line plays again more slowly, and no turn is added.
5. Click **Record answer**, allow the microphone, speak, then click **Stop recording**. Recording also stops by itself after 30 seconds.
6. Read **Did we hear you correctly?**. Choose **Try again** once: the text is thrown away and nothing is evaluated. Record again, check the text, then choose **Continue**.
7. Answer the waiter's current question. Read any correction and listen to the reply. Timing tags show the real time and the suggested target. A slow network can go over those targets.
8. On a saved reply, click **Flag this reply**. The button changes to **Flag submitted** and stays that way after a reload. The opening line has no flag button.
9. After **five accepted answers**, look at the saved summary: words used, words not used and corrections. With no corrections, the page says **No corrections were made during this lesson.**
10. Sign out and sign in again as learner1. The lesson is still Completed. Click **View last summary** to open the saved result again.
11. Select **Passing Customs**. The partner is now a customs officer, and the target words include passport, holiday, stay, days, bag and declare. The restaurant progress does not change.
12. Sign out and sign in as **learner2 / SpeakoDemo2026!**. A new learner2 has its own progress, not learner1's. An account that was used for practice before may already have attempts.
13. Sign out and sign in as **reviewer1 / SpeakoDemo2026!**. The reviewer page opens at `/review/` and shows the reply flagged in step 8. Mark it **Acceptable** or **Incorrect**. A learner or curator who opens `/review/` is refused.

Possible answers, depending on the partner's question:

```text
Restaurant:
Yes, please.
I would like chicken with rice, please.
Can I have some water, please?
No, thank you.
Can I have the bill, please?

Customs:
Here is my passport.
I am here for a holiday.
I will stay ten days.
I have one bag.
I have nothing to declare.
```

The AI wording can change from run to run. Check the behavior, not the exact words: the partner stays inside the lesson, handles each turn correctly and corrects or redirects when needed. If you leave before five accepted answers, there is no summary and the map shows the lesson as In progress.

Speech recognition keeps most beginner grammar mistakes, such as "Can I has the bill?". Short words that run together can still be misheard, so always check the text before you click Continue. If it is wrong, click Try again and speak a little more slowly.

## 8. Troubleshooting

| Symptom | Action |
|---|---|
| Connection refused / page unavailable | Keep the start window open and use port 8001 in the browser. |
| Missing table / no lessons | Run the setup again. It creates the database and adds new lessons. |
| Sign-in fails | Run the setup again, then type learner1 and SpeakoDemo2026! exactly. |
| Sign in above to choose a lesson | Sign in on this page. Signing in to GitHub does not sign you in to Speako. |
| "Add your Claude API key" or "Add your Groq API key" | Run the setup again, or add the key to `.env`. Then restart the app. |
| "Claude rejected the API key" or "Groq rejected the API key" | Delete the value after `ANTHROPIC_API_KEY=` or `GROQ_API_KEY=` in `.env`, run the setup again and paste a working key. |
| Microphone blocked | Use normal Chrome or Edge. Allow the microphone for this local site and in the Windows or macOS privacy settings. |
| "No clear speech was detected" | Speak closer to the microphone and record again. Nothing was sent or evaluated. |
| Timeout during recognition | One retry happens by itself. If Groq still fails, the local speech model reads the recording instead. If that fails too, use Retry this recording to send the kept audio again, or Record answer to replace it. Reloading the page loses the kept audio. |
| "Groq rate limit reached" | Wait a minute and record again. |
| AI reply fails after Continue | The text stays pending. Click Continue again. A failed reply does not add a turn. |
| No spoken reply | Read the text, check the speaker volume and an English browser or system voice, then try Repeat slower. |
| Plain page / old buttons | Start the app with `start.bat` or `start.sh` and hard refresh with Ctrl+F5 on Windows. |

Do not delete a used project database to fix a problem: it holds progress and the usage record. If you use the team's keys, keep one live computer at a time, so the project budget record stays in one place.

## 9. Optional tests and verification

Node.js is needed only for the frontend tests. In a second terminal in the project folder:

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

The Sprint 4 version passed 164 Django tests and all nine frontend test files. The tests fake the speech services and the AI replies and ignore the keys in `.env`, so they make no API calls. A live check with a real voice used Groq for speech and Claude Haiku for the replies. The Sprint 3 checks are in [validation details](submission-validation.md).

Provider uptime and the suggested timing targets are not guaranteed. Check the real microphone and voice playback on the presentation computer.
