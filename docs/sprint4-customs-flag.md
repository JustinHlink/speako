# US-06 / US-07: customs and learner flag flow

Run the existing README setup and migrations. The new data migration adds
Passing Customs; it does not replace the restaurant lesson or reset accounts,
progress, or API usage. It does not add a Curator page.

## Manual checks

1. Sign in as a learner. Select Passing Customs. Check that the partner is a
   customs officer, the visit context replaces the menu, and target vocabulary
   includes passport, holiday, stay, days, bag, and declare.
2. Start the lesson. The opening asks for a passport. Use fictional practice
   answers: "Here is my passport", "I am here for a holiday", "I will stay ten
   days", "I have one bag", "I have nothing to declare". Adapt to the questions.
   Record, stop, inspect the transcript, then Continue. Real speech/replies need
   the privately configured provider key; automated tests use provider doubles.
3. On a saved AI reply click Flag this reply. Expect confirmation and a disabled
   Flag submitted button. Reload: the same reply remains flagged. The opening
   has no flag button because it is not a saved learner/AI turn.
4. Block the flag request in browser developer tools and submit on another turn:
   expect an error and an enabled retry button, without changing lesson progress.
5. Complete five accepted turns; inspect the customs summary. Restaurant progress
   must not become completed. A second learner cannot open the first learner's
   saved summary or flag their turns.
6. Switch back to the restaurant. The waiter role, menu, vocabulary, and prompts
   must return. Exit an unfinished attempt before switching to another lesson.

The reviewer queue is a separate PR. This branch works with the existing flag
API and does not depend on that new page. No live provider calls were used in
this PR's automated validation; generated speech content still needs a live check.

## Automated checks

- `python manage.py test` (121 backend tests)
- Run every `practice/tests*.cjs` file with Node, including tests_flags_page.cjs
  and tests_customs_page.cjs.
- `python manage.py makemigrations --check --dry-run`

Provider interfaces and budget rules are unchanged. The scenario-specific prompt
keeps customs questions about the visit and luggage; tests verify routing and
persistence with controlled outputs, not Gemini's live quality or availability.
