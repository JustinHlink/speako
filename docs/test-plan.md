# Prototype test checklist

No live test is considered passed until it is performed with the real API and microphone.

1. Configure an unbilled Gemini API project, then record 5 short replies. Check transcript accuracy before Continue.
2. Choose Try again on an incorrect transcript. Confirm it receives no correction and never enters the summary.
3. Deny microphone permission. Check that the page explains how to enable it and no API evaluation occurs.
4. Record silence. Check that no answer is evaluated and recording is offered again.
5. Interrupt the network or hit quota. Check error timing, unchanged turn count, and an explicit retry.
6. Use a correct restaurant answer. Check that no unnecessary correction is added.
7. Make a target grammar mistake. Check one explanation sentence and one corrected example.
8. Give a grammatically correct off-topic answer. Check gentle redirection without labeling it incorrect.
9. Repeat slower. Confirm the same line plays and the turn count stays unchanged.
10. Finish 5 exchanges. Confirm used AND unused target words and all corrections, or an explicit no-corrections message.
11. Exit early. Confirm no summary is created. Restart from the beginning.
12. Refresh a completed session. Confirm its summary remains in this browser's local session.
13. Check each timing tag; export measurements. Report p50/p90 from at least 50 tested exchanges, including failure counts separately. Do not average away errors or include human thinking as system latency.
14. Check provider usage and consolidate any teammate usage against the $10 development/testing/review budget.
15. Repeat microphone/playback tests in Chrome and Edge. Other major browser compatibility remains unverified.

Suggested comparison targets: mic 1 s, transcription 5 s, AI 5 s, playback start 1 s, local summary 0.5 s, page-ready 1.5 s, system wait 11 s. First permission prompts and cold starts should be labeled separately when comparing results.
