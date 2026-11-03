# Submission validation — November 4, 2026

## Automated checks

- 115 Django tests passed.
- All six frontend check files passed (map isolation, microphone, browser protocol, retained-recording retry, repeat-page and speech helper).
- `manage.py makemigrations --check --dry-run`: no missing migrations.
- Flag tests cover malformed/empty/non-object JSON, invalid IDs, ownership, duplicate submission and preventing a later decision from replacing an existing review.

## Live provider check

One five-turn restaurant run used real Gemini transcription and replies, with locally synthesized English WAV files as test audio. This is not evidence of a human microphone/browser recording test. The run completed, saved its summary, reopened it after login, and denied another learner access.

A speech request returned HTTP 503 and another timed out. The bounded retry recovered both. Successful recognition latency ranged from 1.38 to 14.87 seconds; replies ranged from 0.64 to 10.68 seconds. Some steps exceeded the suggested five-second timing target. External API uptime and timing are not guaranteed by this validation.

See live-validation-2026-11-04.json for the measured run. The local conservative guard plus retained external usage reached $2.50 of the $10 project allowance at the end of this run. This is not a provider invoice. Unknown/failed calls retain their reservations. No billing or paid fallback was enabled.

## Submission boundaries

Only the restaurant scenario is seeded. Passing Customs is unfinished. Continue final human microphone/playback checks on the presentation computer. A recorded walkthrough can serve as backup, while the instructor runs the submitted tag using a private API configuration.
