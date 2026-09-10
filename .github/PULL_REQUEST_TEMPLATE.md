<!--
One change per PR. If you're tempted to "while I'm here" an unrelated edit —
don't; split it. Read every diff before you open. (AGENTS.md)
-->

## What & why

Fixes #

## How

-

## Verification

<!-- Paste real output. "I think it works" is not a status. -->

- [ ] `python tests/test_matching.py` — exit 0 (output below; add checks if you touched matching/parsers)
- [ ] Core still imports with zero third-party packages (no new imports outside an optional extra)
- [ ] `docs/SCHEMAS.md` updated with sources (if any parser/format changed)
- [ ] README / `brand-context.md` claims still true (if behavior or copy changed)

```
$ python tests/test_matching.py

```

## Honest notes for the reviewer

<!-- Known ceilings, skipped edge cases, anything DEFERRED vs DONE. -->
