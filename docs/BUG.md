# Bug

A start-to-finish trail for anything broken.

## Open (found 2026-09-11 by the end-to-end review — `settleflow-review-2026-09-11-v2.md`)

Nine issues were reproduced; most are now fixed in the commits of that session. What
remains open is listed here rather than claimed as fixed:

| # | Issue | Where | Status |
|---|---|---|---|
| B-1 | `deploy.sh` tarred `saas/settleflow.db` over the server's database, and `scripts/.deploy.env` with it. Nothing had been lost yet (147 live runs against ~100 local) but the next deploy would have destroyed them. | `scripts/deploy.sh`, `scripts/rollback.sh` | **FIXED**, plus a deploy-time assertion that the live run count never drops |
| B-2 | Rate limit keyed on caller-controlled input, so rotating `X-Forwarded-For` gave unlimited buckets (70/70 accepted). | `saas/helpers.py`, `saas/app.py` | **FIXED** — only Cloudflare's `CF-Connecting-IP` counts |
| B-3 | The advertised 10MB cap bounded only the two named files; ~58MB of extra parts rode through, and a 210MB request was accepted. | `saas/app.py` | **FIXED** — a whole-body cap; 25MB of parts now returns 413 |
| B-4 | `parse_amount('Rs.100')` returned `Decimal('0.100')` — a 1000x understatement with no error — and non-finite values (`NaN`, `Infinity`, `1e400`) were accepted and later crashed an export. | `settleflow/parsers.py` | **FIXED** |
| B-5 | A wrong-shaped settlement payload (top-level list, `items` as an object) raised `AttributeError`/`KeyError` and surfaced as HTTP 500. | `settleflow/parsers.py`, `saas/app.py` | **FIXED** — the parser validates its envelope and the app treats it as user error |
| B-6 | The CLI read a JSON settlement file as CSV, found nothing, printed `settlements : 0` and exited 0. | `settleflow/parsers.py`, `settleflow/__main__.py` | **FIXED** — the loader refuses a JSON payload by name; the CLI exits 2 |
| B-7 | `exceptions.csv` was built with string joins, so a narration containing a comma shifted every later column. | `settleflow/__main__.py` | **FIXED** — `csv.writer` |
| B-8 | `match()` rescanned candidates per row, going quadratic when many rows share one UTR (8k rows = 0.655s, ~4x per doubling). | `settleflow/matching.py` | **FIXED** — linear consumption |
| B-9 | Spreadsheet formula injection: a reference starting `=` was written through, live in Excel. | `settleflow/exports.py` | **FIXED** — defused with a leading quote |

## Known limitations (not bugs, but do not hide them)

| # | Limitation | Where | Upgrade path |
|---|---|---|---|
| 1 | The `match()` (amount, date) fallback can mis-pair when two distinct bank lines share one amount and date. | `settleflow/matching.py` | It is reported as `AMOUNT_DATE` rather than `EXACT`, so a human sees it; UTR-based disambiguation or order-level matching is the real fix. |
| 2 | A Juspay reconciliation runs on documentation and vendor code, never a real populated file: the rupee unit, one-date-is-one-credit, and the status filter are all unverified. | `settleflow/schemas.py` (`load_juspay_settlement_csv`) | One real export plus its matching bank credit settles all three. |
| 3 | PhonePe's per-settlement aggregate has never been compared against a real bank credit. | `load_phonepe_settlement_csv` | One PhonePe settlement total plus the matching bank line. |
| 4 | The hosted service exposes the library's formats but not its PDF path (bank statements are CSV-only there). | `saas/app.py` | Wire the SBI PDF parser behind the `[pdf]` extra. |
| 5 | `parse_date` does not read a scan-only PDF (image, no text layer). | `settleflow/pdf.py`, `settleflow/ocr.py` | The OCR path exists behind the `[ocr]` extra; it needs a real scanned statement to verify against. |
| 6 | Razorpay CSV amounts: the official sample shows rupees while the API returns paise — the CSV unit is not confirmed against a real export. | `settleflow/schemas.py` | Confirm against a real Razorpay settlements CSV export. |

`L-1` above supersedes the earlier `L-1`; the numbering was reset when this table gained
the review findings, and row 1 is the same limitation with its mitigation stated.

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
