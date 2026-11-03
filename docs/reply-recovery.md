# Vocabulary recovery

The integrated demo validates every generated reply and corrected example against
the selected lesson vocabulary plus shared beginner words. An invalid candidate
is hidden and recorded as Validation rejected. It does not advance a turn.

On a vocabulary rejection, one automatic rewrite is allowed. The rewrite receives
the same confirmed learner text and conversation history, plus the candidate and
words to replace as data. It uses the same provider and budget guard. A valid
rewrite is saved once as the turn; another invalid result stops and keeps the
pending transcript. Provider failures, malformed output and inconsistent
off-topic corrections do not trigger further retries.

This is an integration change from the earlier manual-retry-only flow. There
are at most two reply-generation calls per Continue, each with its own budget
reservation. It does not expand the allowed vocabulary, generate a scripted
substitute, or guarantee model correctness. Semantic feedback still needs live
validation. Tests cover both successful recovery and bounded failure.
