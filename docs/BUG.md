# Bug

A start-to-finish trail for anything broken. No known bugs at this time.

## Known limitations (not bugs, but do not hide them)

| # | Limitation | Where | Upgrade path |
|---|---|---|---|
| L-1 | `match()`'s amount+date fallback can mis-pair when two distinct bank lines share the same (amount, date) | `matching.py` pass 2 | UTR disambiguation, or order-level matching (Phase 2) |
| L-2 | `parse_date` handles 5 formats only | `parsers.py` | add formats as real files demand (never guess) |
| L-3 | Razorpay parser is settlement-level only; no line-item (`Fetch Settlement Recon`) decomposition yet | `parsers.py` | Phase 2 |

## Reporting a bug

Use this template so a cold reader can reproduce:

```markdown
## Bug: <one line>

- **Where:** <file / function>
- **Input:** <the CSV/JSON/values that trigger it>
- **Expected:** <what should happen>
- **Actual:** <what happened, with the error/output>
- **Model:** <which model/session found it>
- **Date:** <YYYY-MM-DD>
```

## Trail

| # | Bug | Found | Fixed | Commit |
|---|---|---|---|---|
| - | (none yet) | - | - | - |
