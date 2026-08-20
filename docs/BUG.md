# Bug

A start-to-finish trail for anything broken. No open bugs at this time (all fixed).

## Known limitations (not bugs, but do not hide them)

| # | Limitation | Where | Upgrade path |
|---|---|---|---|
| L-1 | `match()`'s amount+date fallback can mis-pair when two distinct bank lines share the same (amount, date) | `matching.py` pass 2 | UTR disambiguation, or order-level matching (Phase 2, built) |
| L-2 | `parse_date` does not read a scan-only PDF (image, no text layer) | `parsers.py` | OCR path (ATL-72, needs a real scanned file) |
| L-3 | Razorpay CSV amounts: sample shows rupees but API is paise — unit not yet confirmed against a real export | `schemas.py` | confirm against a real Razorpay CSV export |

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
| B-1 | SBI native export is tab-separated `.xls`; comma-only reader failed to find the header | 2026-08-16 | `csv.Sniffer` auto-detect delimiter in `load_bank_statement_csv` | `e2f16e4` |
| B-2 | Razorpay recon CSV date `2022-06-07T13:33:57` unparseable | 2026-08-16 | strip trailing time in `parse_date` | `14c6824` |
