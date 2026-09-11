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

## 3. Market / why now (evidence gathered 2026-08-15, refreshed 2026-08-16)

| Fact | Number | Source |
|---|---|---|
| UPI volume (FY2025-26) | 24,162 crore txn (~241.6B), ~₹314 lakh crore | PIB / MoF release, Apr 2026 |
| Live banks on UPI | 703 (Mar 2026) | PIB |
| P2M share of UPI volume | 63% | PIB |
| RBI-authorised Payment Aggregators | 82 (Aug 2026) | RBI CoA list |
| Enterprise recon ownership | ReconPe, Cointab, UnPay, Paxcom (Paymentus) | vendor pricing pages |
| Only OSS anywhere near this | Hyperswitch (43k stars) — infra-grade, config-bound, not SMB turnkey | GitHub |
| New e-com TDS (payment code 1035) | in force 1 Apr 2026 under the new IT Act 2025 | IT Act 2025 / Terra Insight / TaxGarden |

The gap is real at the **SMB layer** and the **component layer** is un-owned. The
enterprise *platform* layer is crowded, which is exactly why we build the parsers +
matching engine and a *thin* SaaS on top, not "another closed recon platform."

**The sharpest demand trigger (added 2026-08-16):** the 1-Apr-2026 TDS
re-codification — old s.194-O → new **s.393(1) Sl.8(v), payment code 1035** — forces
every marketplace seller and every CA to re-map reconciliation config and match
platform settlement ↔ Form 168/26Q ↔ Form 26AS on a quarterly cadence. That is a
named-deadline reconciliation event, a stronger hook than the generic "saves 8-12
hours" pain.

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
| Data model: `ReconLine`, `BatchRecon`, `OrderMatch`, `OrderReconResult` | `settleflow/models.py` | done |
| Matching engine: exact UTR -> amount+date fallback -> unmatched | `settleflow/matching.py` | done |
| Settlement-level matcher | `settleflow/matching.py` (`match_settlements`) | done |
| Line-item grouping + order-ledger matcher (Phase 2) | `settleflow/matching.py` (`group_batches`, `match_orders`) | done |
| Generic CSV loader (explicit column mapping) | `settleflow/parsers.py` | done |
| Razorpay settlement parser (real API schema; paise->rupee, epoch->date) | `settleflow/parsers.py` | done |
| Razorpay settlement-recon parser (24 documented params, strict schema check) | `settleflow/parsers.py` | done |
| Vendor/bank column-map registry (Phase 3; verified slots + empty slots) | `settleflow/schemas.py` | done |
| Exports: Tally CSV, GST worksheet, TDS-1035 worksheet | `settleflow/exports.py` | done |
| Exception classifier + LLM-prompt builder (Phase 5) | `settleflow/exceptions.py` | done |
| Thin SaaS: FastAPI reconcile/expose/export (Phase 4) | `saas/app.py` + templates | done |
| Self-check (assert-based, no framework) | `tests/test_matching.py` | done |

## 6. Roadmap

| Phase | What | Depends on | Status |
|---|---|---|---|
| 1 | scaffold + data model + matching + Razorpay parser + self-check | - | done |
| 2 | line-item decomposition (Razorpay Fetch Recon schema) | 1 | done |
| 3 | more parsers: Cashfree, PayU, PhonePe, Juspay + bank statements | real sample files | done — Razorpay (CSV + API), PayU's two settlement APIs, PhonePe, Juspay and Cashfree's two-section recon are all wired; IDFC statements and Cashfree's plain settlements export remain deferred for want of a real sample (see `docs/SCHEMAS.md`) |
| 4 | thin hosted SaaS: ingest, exception queue, Tally/GST/TDS-1035 exports | 3 | done (local; hosting deferred) |
| 5 | exception classifier + optional LLM triage hook | 4 | done (rules + prompt builder; LLM call is a SaaS-layer concern) |

## 7. Monetization (honest, refreshed 2026-08-16)

- **OSS core (MIT) = trust + distribution.** The money is never in the code.
- **#1 lever: Sidekiq-style commercial license for embedding** (white-label/OEM to
  fintechs and CA software vendors, per-deployment or revenue-share). This decouples
  revenue from our own SaaS signups — the only move that genuinely raises the ceiling.
- **Thin SaaS at ₹4-7k/mo through CAs** — but re-bundled to beat the ₹749-899/mo Zoho
  Books anchor: UPI/NPCI-specific matching, bank-statement packs, Tally bridge, and
  audit-grade TDS-1035 output justify the premium. Plus a ₹20-50k/mo support retainer.
- **Consulting:** an EY Band-5 urban-planner/founder + a real payments-OSS repo is a
  differentiated bidder for reconciliation/ops work.
- **Grants (deferred harvest):** Zerodha FLOSS/fund ($10k-100k/project, excludes new
  projects) and GitHub Secure Open Source Fund (~$10k/project) only become eligible
  after real adoption. Realistic year-1 grants: ₹0-5 lakh. `funding.json` +
  `.github/FUNDING.yml` are in the repo now (near-zero cost, also the FLOSS/fund
  application artifact).
- **Honest expectation:** 12-24 months to meaningful revenue. Do not build this
  expecting to quit the day job. The first 6-12 months are reputation + distribution.
  Full evidence in `docs/MONETIZATION.md`.

## 8. Competitive landscape (condensed)

| Player | What | Why we still win |
|---|---|---|
| Hyperswitch (Juspay) | open-source payment orchestration + recon module | infra-grade, config-bound per merchant, Juspay's own schema, not SMB turnkey |
| ReconPe (₹3,999-6,999/mo) / Synaptic AI Lab (₹3,999/mo) | self-serve SMB recon SaaS | they re-implement the parsers privately; no OSS component layer |
| Cointab ($149-749/mo) | volume-tiered recon SaaS | USD-priced, mid-market finance teams, not SMB or OSS |
| Paxcom (Paymentus) / UnPay | enterprise recon, sales-led | ₹100-500 Cr revenue, NDA-bound, no OSS |
| Razorpay Optimizer / RazorpayX | gateway-bundled recon | gives recon away to defend 2% txn fees; vendor lock-in |

*(Removed "Gini" — gini.co.in is a Pune construction firm, not a recon vendor.
Corrected Paxcom ownership to Paymentus, not PayU. See `docs/MONETIZATION.md`.)*

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
python tests/test_matching.py     # the self-check (prints the number of checks)
```
