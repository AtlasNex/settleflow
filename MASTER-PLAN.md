# SettleFlow — Master Plan

> **Working name:** `settleflow`. Final name TBD by Sanjay. Private until complete.

## 1. What this is

An open-source Python library for **UPI/NPCI settlement reconciliation in India**.

It parses payment-gateway settlement files and bank statements, then matches them so a
merchant can reconcile "what the gateway says I received" against "what actually landed
in my bank account." The output is a matched/unmatched ledger with the exceptions
flagged, not a black box.

The open-source **component layer** (the parsers + the matching engine) is owned by
nobody today. Every Indian reconciliation SaaS re-implements these parsers privately
behind a paywall. That component layer is what we are building.

## 2. Why this exists (the problem)

- UPI settles **T+1 as bulk NEFT credits** that only disaggregate via the gateway's
  settlement file. The bank statement shows one undifferentiated credit.
- 200-300 UPI collections/month = **8-12 hours of manual reconciliation** for a small
  merchant or CA.
- The match key is **not the UTR**. The bank statement's UTR is the *correspondent
  bank's* UTR, which differs from the gateway's `settlement_utr`. The correct key is
  `settlement_id` -> (settlement date + net amount).
- Gateways return amounts in **paise** (smallest currency unit); bank statements are in
  rupees. Reconciling them means a currency-unit conversion is mandatory and easy to
  get wrong.

## 3. Market / why now (evidence gathered 2026-08-15)

| Fact | Number | Source |
|---|---|---|
| UPI volume (CY2025) | 228B transactions, ₹300 lakh crore | NPCI / Business Standard |
| Live banks on UPI | 703 | NPCI/PIB |
| Enterprise recon ownership | Gini, UnPay, ReconPe, Cointab, Paxcom | vendor pricing pages |
| Only OSS anywhere near this | Hyperswitch (43k stars) — infra-grade, config-bound, not SMB turnkey | GitHub |
| New e-com TDS (code 1035) | in force 1 Apr 2026 under the new IT Act | IT Act 2025 |

The gap is real at the **SMB layer** and the **component layer** is un-owned. The
enterprise *platform* layer is crowded, which is exactly why we build the parsers +
matching engine and a *thin* SaaS on top, not "another closed recon platform."

## 4. The reconciliation model (two levels)

1. **Settlement -> bank credit.** Match a settlement batch (`settlement_id`) to a bank
   NEFT credit by `settlement_utr`, falling back to (settlement date + net amount).
2. **Line items -> orders.** Decompose each batch into its `order_id` / `payment_id`
   rows (gross - MDR - GST-on-MDR - refunds = net) and match against the merchant's
   order management system.

Level 1 is built and tested. Level 2 is the immediate next increment; the Razorpay
`Fetch Settlement Recon` schema is already captured in research and ready to wire.

## 5. Current state (what is built)

| Piece | File | Status |
|---|---|---|
| Data model: `Txn`, `Match`, `MatchStatus`, `ReconResult`, `Settlement` | `settleflow/models.py` | done |
| Matching engine: exact UTR -> amount+date fallback -> unmatched | `settleflow/matching.py` | done |
| Settlement-level matcher | `settleflow/matching.py` (`match_settlements`) | done |
| Generic CSV loader (explicit column mapping) | `settleflow/parsers.py` | done |
| Razorpay settlement parser (real API schema; paise->rupee, epoch->date) | `settleflow/parsers.py` | done |
| Self-check (7 checks, assert-based, no framework) | `tests/test_matching.py` | done |

## 6. Roadmap

| Phase | What | Depends on |
|---|---|---|
| 1 (done) | scaffold + data model + matching + Razorpay parser + self-check | - |
| 2 | line-item decomposition (Razorpay Fetch Recon schema) | 1 |
| 3 | more parsers: Cashfree, PayU, PhonePe, Juspay + bank statements (HDFC/SBI/ICICI/Axis/Kotak) | 1 |
| 4 | thin hosted SaaS: auto-ingest, exception queue, Tally/Zoho/GST exports, e-com TDS 1035 | 3 |
| 5 | agents on the unmatched 1-3% (LLM-assisted exception classification) | 4 |

## 7. Monetization (honest)

- **OSS core (MIT) = trust + distribution.** The money is never in the code.
- Thin SaaS at ₹4-7k/mo, sold through CAs/bookkeepers (the channel ReconPe proved).
- Consulting: an EY Band-5 urban-planner/founder + a real payments-OSS repo is a
  differentiated bidder for reconciliation/ops work.
- Grants: Zerodha FLOSS/fund ($10k-100k), GitHub Secure Open Source Fund ($10k).
- **Honest expectation:** 12-24 months to meaningful revenue. Do not build this
  expecting to quit the day job. The first 6-12 months are reputation + distribution.

## 8. Competitive landscape (condensed)

| Player | What | Why we still win |
|---|---|---|
| Hyperswitch (Juspay) | open-source payment orchestration + recon module | infra-grade, config-bound per merchant, Juspay's own schema, not SMB turnkey |
| ReconPe / Synaptic / Gini / Cointab / Paxcom | closed recon SaaS | they re-implement the parsers privately; no OSS component layer |
| Razorpay Optimizer / RazorpayX | gateway-bundled recon | vendor lock-in; only works if you route via them |

## 9. Decisions index

All "why" lives in `docs/DECISIONS.md`. The short version: Decimal-not-float, two-pass
matching, settlement_id-as-key, paise->rupee in the parser, generic CSV loader with
explicit column mapping, assert-based self-check (no pytest), MIT, private until done.

## 10. Doc map

| File | What it is |
|---|---|
| `README.md` | entry point, quickstart |
| `MASTER-PLAN.md` | this file: strategy, roadmap, market |
| `AGENTS.md` | the working rules for any AI/agent touching this repo |
| `docs/ARCHITECTURE.md` | system map: files, data model, algorithm, data flow |
| `docs/CONSTRAINTS.md` | things to never touch, spelled out |
| `docs/FLOW.md` | exact execution trace between files and functions |
| `docs/DECISIONS.md` | the why behind every decision, with version pinning |
| `docs/HANDOVER.md` | incremental context so the next session starts warm |
| `docs/BUG.md` / `docs/FEATURE.md` | start-to-finish trails |
| `docs/ROLLBACK.md` | the way out, before you need it |
| `docs/TESTING.md` | test checklist: proof it works |
| `logs/SESSION-LOG.md` | append-only session trail |

## 11. Run it

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
python tests/test_matching.py     # self-check, 7 checks
```
