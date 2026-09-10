# SettleFlow

> Working name. Pre-1.0 beta. The matching engine is the product — read it, it's all here.

**For merchants and accountants reconciling Razorpay payouts against bank credits.**
Parse a payment-gateway settlement file and a bank statement, match them, and export
Tally / GST / TDS-1035 (ex-194O) workpapers. Open source (MIT), Python, **zero runtime
dependencies** — the core runs on the standard library alone, enforced by CI.

**Why not just use Razorpay's own settlement reports?** Gateway reports tell you what
the gateway *says* it sent. They never check against the credit that actually landed in
your **bank**, and they don't produce Tally/GST/TDS workpapers. SettleFlow closes that
gap: settlement file ↔ bank statement, with export-ready output and an explicit list of
everything that *doesn't* match.

[Hosted demo (free while in beta)](https://settleflow.atlasnex.com) ·
[Report a bug](https://github.com/AtlasNex/settleflow/issues/new?template=bug_report.yml) ·
[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Privacy (draft)](docs/legal/PRIVACY.md)

![CI](https://github.com/AtlasNex/settleflow/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Runtime deps](https://img.shields.io/badge/runtime%20deps-none%20(stdlib)-brightgreen)

## Install

Not on PyPI yet — install from source (nothing else is required; no `pip install` of
dependencies happens):

```bash
pip install git+https://github.com/AtlasNex/settleflow.git
```

Or just clone and run from the repo root. Python ≥ 3.10.

## 10-second example

```python
from datetime import date
from decimal import Decimal
from settleflow import Txn, match

settlements = [Txn("123456789012", Decimal("100.00"), date(2026, 8, 15))]
bank        = [Txn("1234 5678 9012", Decimal("100.00"), date(2026, 8, 16))]

result = match(settlements, bank)
print(result.matched)           # one exact match — UTRs normalized, money is Decimal
print(result.settlement_only)   # in the gateway file, not in your bank
print(result.bank_only)         # in your bank, not in the gateway file
```

## CLI — one command, three workpapers

```bash
python -m settleflow reconcile \
    --settlements settlements.csv --vendor razorpay_settlement_csv \
    --bank sbi --statement statement.csv --out-dir out
```

Writes matched/exception CSVs into `out/`; `--ocr` handles scanned SBI PDFs (needs the
`[ocr]` extra).

## Library

```python
from settleflow import parse_razorpay_recon, group_batches, match_orders

lines = parse_razorpay_recon(api_response_dict)   # GET /v1/settlements/recon/combined
batches = group_batches(lines)                    # netting: gross − MDR − GST − refunds
orders = [Txn(None, Decimal("1000.00"), date(2026, 8, 15), ref="order_123")]
result = match_orders(lines, orders)              # payments joined to your order ledger
```

Exports: `export_tally_csv`, `export_gst_worksheet`, `export_tds_1035`. Exceptions:
rule-based `classify`, a `build_llm_prompt` helper, and a provider-agnostic
`triage_exceptions` hook. Full API in `docs/ARCHITECTURE.md`.

## Optional extras

The core is stdlib-only — these are opt-in and lazily imported:

| Extra | Gives you | Pulls in |
|---|---|---|
| `pip install "settleflow[saas]"` | the thin FastAPI web layer (`saas/`) | fastapi, uvicorn, jinja2, python-multipart |
| `pip install "settleflow[pdf]"` | native SBI PDF statements (YONO / netbanking / credit-card) | pymupdf |
| `pip install "settleflow[ocr]"` | scanned (image-only) PDF statements | pymupdf + a system Tesseract install |

## Self-check

One runnable check, no test framework (deliberate — see `docs/TESTING.md`):

```bash
python tests/test_matching.py    # exit 0 = all green
```

## Status — what works, what doesn't

**Built (v0.7.3):**

- Two-pass matching: exact normalized-UTR → amount+date fallback → explicit unmatched.
- Order/line-item level reconciliation from the Razorpay recon schema (24 params),
  with per-batch netting.
- Settlement parsers: Razorpay settlement CSV + Razorpay recon CSV.
- Bank statement CSVs: HDFC, SBI, ICICI, Axis, Kotak (three variants incl. Dr/Cr),
  PNB, DBS. SBI PDFs (YONO/netbanking/credit-card) + scanned-PDF OCR via extras.
- Exports: Tally CSV, GST worksheet, TDS code-1035 (ex-194O) worksheet.
- CLI, exception classifier, hosted beta (`saas/`, deployable via Docker).

**Not built — don't pretend otherwise:**

- Only **Razorpay** as a gateway. PayU / Paytm / PhonePe settlements: not supported
  (a redacted sample file is the fastest way to change this).
- PDF statement parsing exists **only for SBI layouts** with public evidence; other
  banks' PDFs are CSV-only.
- The amount+date fallback can mis-pair when two bank lines share one (amount, date);
  UTR-based disambiguation is open work (`docs/CONSTRAINTS.md`).
- Pre-1.0: no API-stability promise, no PyPI release, no SLA, no upgrade tooling.
- Legal pages (`docs/legal/`) are **drafts pending review** — the operator is an
  individual pre-registration, and that is stated in them.

## Pricing, honestly

- Library: MIT, free forever. Self-hosting: free.
- Hosted service: **free while in beta**. No commercial tier is live yet — if that
  changes it will be announced here and on the site.

## Docs

| File | What |
|---|---|
| `brand-context.md` | positioning, audience, tone — source of truth for copy |
| `docs/ARCHITECTURE.md` | system map: files, data model, algorithm |
| `docs/SCHEMAS.md` | verified vendor/bank column layouts + sources |
| `docs/CONSTRAINTS.md` | never-touch rules (Decimal, determinism, zero deps) |
| `docs/TESTING.md` / `docs/DECISIONS.md` | checklist; the why behind choices |
| `docs/BUG.md` / `docs/FEATURE.md` | bug and feature trails |
| `docs/legal/` | PRIVACY / TERMS / REFUND — **drafts pending review** |
| `MASTER-PLAN.md` / `docs/MONETIZATION.md` | strategy and the commercial thesis |

## License

MIT — see `LICENSE`. The one asymmetry that matters: you can audit exactly how your
reconciliation is computed, which no closed reconciliation SaaS will let you do.

Built by [AtlasNex](https://atlasnex.com) · sanjay@atlasnex.com
