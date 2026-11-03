# Transcript confirmation and targeted feedback

This branch builds on feature/us-05-vocabulary (PR #2). Review its incremental
changes against that branch; retarget to main after US-05 is merged.

## Automated checks

In a new checkout and virtual environment:

    python -m pip install -r requirements.txt
    python manage.py test practice
    node practice/tests_protocol.cjs

Tests use simulated provider results and make no external AI calls. They verify
the confirmation boundary, discard, silence, invalid audio, processing failure,
ownership, roles, stale IDs, retained pending text, correction persistence,
off-topic correction rejection and vocabulary behavior. They do not establish
real speech accuracy or model correction quality.

The old tests referenced the removed PracticeSession model. Their applicable
workflow checks now live in tests_confirmation.py; budget checks remain in
tests.py. Full saved-summary creation is owned by US-18 and remains an open
integration dependency, not a completed feature of this branch.

## Local setup

Use a NEW checkout and database. Do not copy the original prototype database:
main replaced its initial migration and introduced a custom User model.
Keep the original database and usage ledger intact.

    python manage.py migrate
    python manage.py shell

In the Django shell, create a local learner (choose your own password):

    from practice.models import User
    user = User.objects.create_user(username="learner", password="YOUR_LOCAL_PASSWORD", role="Learner")

The US-05 data migration creates the restaurant lesson and vocabulary. Configure
the existing unbilled Gemini project in .env as described in README only for live
validation; do not reset the project budget by starting a new ledger. Transfer
and reconcile existing usage before switching the designated live environment.

    python manage.py runserver 127.0.0.1:8002 --insecure --noreload

## Manual check in Edge

1. Open localhost:8002 and sign in with the learner account.
2. Start the restaurant lesson. Record a short English answer and stop.
3. Check that recognized text appears before any tutor reply or correction.
4. Click Try again. The text disappears and the turn count does not change.
5. Record again, reload the page, and check that the pending text survives.
6. Click Continue. Only the confirmed text appears as a learner turn.
7. Try a target grammar error, a correct answer, and a correct off-topic answer.
   Inspect actual feedback; automated mock tests cannot prove model judgments.
8. On a provider failure, pending text stays available for another Continue.
9. Sign out and use a different learner. The first learner's attempt must not appear.

No live test was performed as part of the automated verification. No provider key
or old database is included in this branch.

## Provider handoff

George can replace practice/providers.py without changing transcript confirmation:

- ready() -> (bool, setup message)
- usage() -> the existing budget-display fields
- transcribe(audio_bytes, mime_type) -> {"transcript": str}
- reply(parts, instructions, schema) -> reply, correction_explanation,
  corrected_example and off_topic; optional _api_attempt_id for usage tracking
- ProviderError -> a controlled provider failure

Transcription must preserve errors rather than fix them. It must never generate
tutor feedback. Endpoints, ownership and pending IDs stay outside the provider.
Any replacement that makes paid external calls must preserve the usage guard.

## Scope and open dependencies

- Minimal sign-in controls exercise the existing login endpoint; this is not
  the full account-management or learning-map implementation.
- Status and the existing restaurant page now use the new attempt response.
- Exit clears pending text without generating a summary.
- Summary rendering reads an existing LessonSummary if available; it does not
  create one. Final-turn atomic summary creation still needs US-18 integration.
- Other feature branches need integration and conflict checks before main merge.
- The existing main README describes the old prototype; this file documents
  this branch's setup without claiming the complete sprint is ready.
