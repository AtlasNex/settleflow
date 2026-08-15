# Testing

Proof it works, not a claim that it does.

## The one command

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
python tests/test_matching.py
```

Exit 0 = all green. It is a plain assert-based script (no framework, by design — see
`docs/DECISIONS.md` D-8).

## What is covered (18 checks)

| Check | What it proves |
|---|---|
| `test_exact_utr_match` | normalized UTR pairing -> `EXACT` |
| `test_amount_mismatch_flag` | same UTR, different amount -> `AMOUNT_MISMATCH` |
| `test_amount_date_fallback_when_no_utr` | no UTR -> `AMOUNT_DATE` |
| `test_unmatched_flows_to_correct_buckets` | leftovers split settlement_only vs bank_only |
| `test_totals_reconcile` | the three total properties sum correctly |
| `test_razorpay_settlements_parse_and_match` | real Razorpay schema: paise->rupee, epoch->date, match by UTR |
| `test_razorpay_settlement_matches_by_amount_date_when_bank_utr_differs` | bank UTR differs -> amount+date fallback |
| `test_parse_recon_lines_verbatim` | verified recon schema: 4 line types, paise->rupee, epoch->date |
| `test_parse_recon_rejects_unknown_fields` | parser fails closed on a schema change |
| `test_parse_recon_rejects_missing_required` | parser fails closed on a missing required key |
| `test_group_batches_nets_correctly` | gross/fee/tax/refund/net per batch |
| `test_match_orders_exact_and_unmatched` | order_id join -> EXACT, adjustments set aside |
| `test_match_orders_amount_mismatch_and_amount_date_fallback` | order mismatch + (amount,date) fallback |
| `test_refund_links_to_payment` | refund -> payment linkage via payment_id |
| `test_export_tds_1035` | code-1035 0.1% TDS + ₹5L individual exemption |
| `test_export_gst_and_tally` | GST netting + Tally MATCHED row |
| `test_classify_fee_drift_and_direct_transfer` | exception rules fire |
| `test_build_llm_prompt` | prompt builder emits triage text |

## Manual smoke checklist (when a parser changes)

1. Parse a real sample file through the new parser; confirm no exception.
2. Confirm amounts are in rupees (not paise) in the output.
3. Run `match` on a known pair; confirm the status is what you expect.
4. Re-run `python tests/test_matching.py` and paste the output.

## SaaS smoke checklist (Phase 4)

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
python -m uvicorn saas.app:app --host 127.0.0.1 --port 8091
# in another shell:
curl http://127.0.0.1:8091/health                                   # {"status":"ok"}
curl -X POST http://127.0.0.1:8091/reconcile \
  -F settlement_file=@saas/sample_settlements.json \
  -F bank_file=@saas/sample_bank.csv \
  -F settlement_kind=razorpay_settlements \
  -F bank_utr_col=utr -F bank_amount_col=amount -F bank_date_col=date
# -> run_id, matched/settlement_only/bank_only counts, export URLs
```

## What is NOT yet covered (known gaps)

- Real (non-doc) vendor files with dirty columns (extra headers, blank rows).
- Bank statement formats (registry built; column maps DEFERRED pending real samples).
- Cashfree / PayU / PhonePe / Juspay parser data (same — needs real sample files).
- Performance on large files (tens of thousands of rows).
- SaaS auth, multi-user, hosting (later-stage concerns, out of scope for the open core).

Do not claim these are tested. Add a check the moment one is built.
