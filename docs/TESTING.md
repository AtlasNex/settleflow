# Testing

Proof it works, not a claim that it does.

## The one command

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
python tests/test_matching.py
```

Exit 0 = all green. It is a plain assert-based script (no framework, by design — see
`docs/DECISIONS.md` D-8).

## What is covered (7 checks)

| Check | What it proves |
|---|---|
| `test_exact_utr_match` | normalized UTR pairing -> `EXACT` |
| `test_amount_mismatch_flag` | same UTR, different amount -> `AMOUNT_MISMATCH` |
| `test_amount_date_fallback_when_no_utr` | no UTR -> `AMOUNT_DATE` |
| `test_unmatched_flows_to_correct_buckets` | leftovers split settlement_only vs bank_only |
| `test_totals_reconcile` | the three total properties sum correctly |
| `test_razorpay_settlements_parse_and_match` | real Razorpay schema: paise->rupee, epoch->date, match by UTR |
| `test_razorpay_settlement_matches_by_amount_date_when_bank_utr_differs` | bank UTR differs -> amount+date fallback |

## Manual smoke checklist (when a parser changes)

1. Parse a real sample file through the new parser; confirm no exception.
2. Confirm amounts are in rupees (not paise) in the output.
3. Run `match` on a known pair; confirm the status is what you expect.
4. Re-run `python tests/test_matching.py` and paste the output.

## What is NOT yet covered (known gaps)

- Real (non-doc) vendor files with dirty columns (extra headers, blank rows).
- Bank statement formats (not built yet).
- Line-item (order-level) reconciliation (Phase 2, not built).
- Performance on large files (tens of thousands of rows).

Do not claim these are tested. Add a check the moment one is built.
