# US-13: reviewer web page

Use the README install/migrate steps. Run `python manage.py seed_demo_users
--password YOUR_LOCAL_DEMO_PASSWORD` (on one line) to create the reviewer1 role.
Sign in on the home page as reviewer1 with that chosen local password. Login
opens `/review/`; an already signed-in reviewer can use Open review queue.
Do not use a real account password in a public document.

## Demo / manual checks

1. Have a learner flag one of their saved turns through the existing API or the
   separate US-06 frontend PR. This page itself does not create fake queue items.
2. Sign in as reviewer1. Check scenario, grammar goal, target words, opening,
   earlier turns, flagged learner/AI pair, correction if any, and flag timestamp.
3. Mark Acceptable or Incorrect. The saved item leaves the unresolved queue.
   Refresh or sign out/in: it must remain resolved.
4. Open the same unresolved item in two browser tabs. Resolve it in one tab;
   saving in the second must report it is already reviewed and refresh the queue,
   without overwriting the original reviewer or decision.
5. Sign in as a learner and open `/review/`: expect 403. Direct API calls are
   also denied. Signed-out access is 401. A Curator is not a Reviewer.
6. Disconnect networking during loading or saving. Expect an error, retry/refresh
   instructions, and no claimed successful save. Refresh before retrying an
   uncertain write, since it may already have reached the server.

No provider calls are needed for review. Reviewer decisions are recorded; they
do not automatically rewrite AI replies or change lesson content.

## Tests

- `python manage.py test` (119 backend tests)
- Run all `practice/tests*.cjs` scripts with Node, including tests_reviewer_page.cjs.
- Page/API role denial, CSRF, saved decisions, duplicate review conflicts,
  unresolved filtering, context, network failures, and safe text rendering.

The existing atomic API update prevents a later review from overwriting a saved
decision. The frontend removes stale cards while refreshing and clears private
queue data if authorization expires.
