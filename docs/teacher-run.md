# Fixed restaurant demo — November 4, 2026

Version tag: **submission-sprint3-2026-11-04**

Use this fixed tag for assessment rather than a moving development branch.
The submission history preserves the original feature PRs and the integration
review. Later changes require a new tag.

## Download

Clone the tagged version (Git must be installed):

    git clone --branch submission-sprint3-2026-11-04 https://github.com/JustinHlink/speako.git speako-demo
    cd speako-demo

Alternatively download the source ZIP from the GitHub release, extract it, and
open a terminal in the folder containing manage.py. If the repository is private,
the instructor must sign in with an invited GitHub account before downloading.

## Windows setup (PowerShell)

    py -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    Copy-Item .env.example .env

Edit .env locally:

    GEMINI_API_KEY=YOUR_PRIVATE_TEST_KEY
    GEMINI_FREE_TIER_CONFIRMED=true

Use a valid key for a project without billing, provided privately or created by
the instructor. Do not put the real key in the repository, screenshots, videos,
or public submission text. Do not set the confirmation flag without checking
the project's billing state. Live speech recognition and replies require this
configuration and network access; opening the page alone does not validate AI.

Choose a local demo password of at least eight characters:

    .\.venv\Scripts\python.exe manage.py migrate
    .\.venv\Scripts\python.exe manage.py seed_demo_users --password "YOUR_DEMO_PASSWORD"
    .\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --insecure --noreload

Open http://127.0.0.1:8001/ in Edge or Chrome. Sign in as learner1 with the chosen
password. The second isolated learner is learner2, using the same chosen password.
Allow the microphone when recording. Keep the terminal running. Ctrl+C stops it.
The development server serves static files using --insecure on localhost only;
these commands are not instructions for public deployment.

## macOS / Linux

Use python3 -m venv .venv, .venv/bin/python instead of the Windows Python path,
and cp .env.example .env. The migrate, seed_demo_users and runserver arguments
are otherwise the same, including --insecure --noreload. Windows was checked
locally; a clean installation on macOS/Linux still needs separate verification.

## Demo sequence

1. Sign in and select Ordering at a Restaurant from the learning map.
2. Start, listen, record and stop; read the transcript before evaluation.
3. Choose Try again once: discarded words must not advance the turn.
4. Record again and choose Continue. Inspect the reply and any targeted correction.
5. Use Repeat slower: the last line replays without advancing the turn.
6. Finish five accepted turns; inspect used/unused words and corrections.
7. Sign out and back in; reopen the saved summary. Use learner2 to verify isolation.

Recordings stop automatically at 30 seconds. Only accepted turns advance the
conversation. An invalid AI vocabulary candidate can be rewritten once; if it
still fails, the pending transcript remains for retry. Gemini outages/timeouts
can still interrupt live operation. A recorded demo is a backup, not a substitute
for an independently runnable system.

## Verification and boundaries

- 115 Django tests passed on the submission candidate.
- All six frontend check files passed, including map-failure isolation and retained-recording retry.
- A fresh clone installed dependencies in a new virtual environment; migration,
  demo-user creation, login and lesson-list checks succeeded.
- Live water-order generation passed after the basic-vocabulary revision.
- Real-device checks are still needed on the actual presentation computer.
- Restaurant is the seeded demonstration scenario. Other scenarios and missing
  reviewer/curator pages are not claimed as completed by this release.

All automated tests use simulated AI/network/device inputs and spend no API quota:

    .\.venv\Scripts\python.exe manage.py test practice
    Get-ChildItem practice\tests_*.cjs | ForEach-Object { node $_.FullName }

Node.js is needed only for frontend tests. Python 3.12 was used for verification.
Do not copy the old prototype database into this schema. Keep existing project
usage accounting when changing the single designated live environment; a new
database must not silently reset the team's ten-dollar allowance.

## Future work

Continue development on feature branches or develop. To change this demo, issue
a new tag and release after tests; do not move or replace the existing tag.
Keep the team's individual PR reviews and main-branch merges as collaboration
evidence. The fixed tag does not replace those records.

## API failure recovery

A transient speech-recognition failure gets at most one automatic retry, with
budget reserved for each attempt. If both attempts fail, use Retry this recording
without speaking again, or Record answer to replace the audio. The retained audio
exists only in this browser tab's memory and is cleared after successful
recognition. Quota and key errors need configuration/allowance checks rather than
repeated retries. Provider errors do not advance the turn.

Only one designated environment uses the project key for live tests at a time.
Before handing live use to another computer, stop calls from the previous
machine and retain its usage ledger and recorded external usage. A fresh
installation must not silently reset the project-wide budget.
