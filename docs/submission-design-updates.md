# Submission integration changes

- Keep database-backed lesson rules and a single account-progress helper. Final turn, summary and completion remain in one transaction.
- Isolate map loading from conversation rendering/playback. A map failure has its own retry message; 401/403 responses show sign-in guidance.
- Retain one failed recording in browser memory for the same attempt, with an explicit retry button. No failed transcription is evaluated or counted as a turn.
- Retry transcription once on transient transport/HTTP 500/502/503/504 errors. Each attempt reserves budget. Request timeout is 12 seconds per speech attempt. Quota/auth/format errors are not automatically retried. Conversation calls retain manual retry; vocabulary rejection allows one constrained rewrite.
- Parse flag submissions through the shared safe JSON helper, validate integer IDs, make duplicate flag creation idempotent with a conflict response, and atomically accept only an Unresolved review decision.
- Fix the test timezone import collision after merging main. Automated network tests remain simulated; live provider availability is separately checked.

Restaurant is the seeded scenario. Passing Customs is not implemented. Reviewer and curator API support does not imply completed web pages.
