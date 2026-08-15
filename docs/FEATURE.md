# Feature

A start-to-finish trail anyone can pick up cold.

## In progress

### Phase 2 — line-item decomposition

- **What:** parse the Razorpay `Fetch Settlement Recon` response (per-transaction rows:
  `entity_id`, `type` payment/refund/transfer/adjustment, `debit`/`credit`, `amount`,
  `fee`, `tax`, `settlement_id`, `payment_id`, `order_id`) and reconcile each batch's
  line items against the order management system: gross - MDR - GST-on-MDR - refunds = net.
- **Why:** settlement-level matching (Phase 1) tells you *which batch*, but not *which
  orders*; the order-level truth is what a CA actually needs.
- **Schema:** already captured in research (Razorpay docs, verbatim).
- **Status:** not started.

## Backlog (ordered)

| # | Feature | Notes |
|---|---|---|
| 3 | More gateway parsers: Cashfree, PayU, PhonePe, Juspay | same pattern as Razorpay |
| 4 | Bank statement parsers: HDFC, SBI, ICICI, Axis, Kotak | statement formats, narration parsing |
| 5 | e-com TDS code 1035 classification | new IT Act, from 1 Apr 2026 |
| 6 | Thin hosted SaaS (auto-ingest, exception queue, Tally/Zoho/GST exports) | the paid layer |
| 7 | Agents on the unmatched 1-3% (LLM exception classification) | the moat |

## Feature template

```markdown
## Feature: <one line>

- **Why:** <the problem / who has it>
- **Files touched:** <list>
- **Model + date:** <who made the call>
- **Test:** <which check proves it works>
- **Status:** planned / in progress / done
```
