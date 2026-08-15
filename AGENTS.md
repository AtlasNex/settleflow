# AGENTS.md

Working rules for any AI or agent touching this repository. These are binding, not
advisory. They exist so a future session cannot silently damage the project.

## Before writing code

1. **Read every diff. Every time.** Before you commit, read what changed. A diff you
   have not read is a bug you have not found.
2. **Ask "why" before "what".** Trace the real flow before writing a line. A small diff
   in the wrong place is a second bug, not laziness.
3. **One change per request.** Small, traceable, reviewable. Do not bundle unrelated
   edits into one commit.
4. **Read `docs/CONSTRAINTS.md` and `docs/HANDOVER.md` first.** They tell you what you
   must never touch and where the last session stopped.

## While writing

5. **Explicit comments make the flow legible, not just functional.** A docstring or
   comment should answer "why", not restate the code.
6. **Money is `Decimal`, never `float`.** No exceptions.
7. **Never fabricate data or schemas.** Vendor formats come from real docs/samples. If
   you cannot verify it, raise; do not guess.
8. **Follow `docs/ARCHITECTURE.md`'s invariants**: deterministic output, zero runtime
   dependencies, rupees in the model, UTR normalization is alnum+uppercase only.

## Before claiming done

9. **Verify, do not assert.** Run the command, paste the real output. Never narrate past
   a failure or a contradiction in your own tool output.
10. **Non-trivial logic leaves one runnable check.** The self-check is
    `python tests/test_matching.py`. If you change the matching engine, add a test.
11. **Closeouts separate DONE / DEFERRED / ABORTED / SKIPPED.** Never mark deferred or
    skipped work as done.

## Version pinning

12. **Tag your context.** Note in `docs/DECISIONS.md` which model made which call and
    when. Do not leave an un-attributed decision in the codebase.

## End of session

13. **Write the handoff.** Update `docs/HANDOVER.md` (state + next step) and append to
    `logs/SESSION-LOG.md`. Thirty seconds now saves hours later.

## Rollback

14. **Know your way out before you need it.** `docs/ROLLBACK.md` is the escape hatch.
    Prefer revert over rewrite; never force-push published history.
