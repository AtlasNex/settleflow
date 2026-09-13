# Architecture

The system map. Read this before touching anything so you do not work blind.

## Package layout

```
settleflow/
├── pyproject.toml          # name=settleflow; library = zero runtime deps; saas = optional-deps
├── settleflow/
│   ├── __init__.py         # public API surface (exports)
│   ├── models.py           # Txn, Match, MatchStatus, ReconResult, Settlement,
│   │                       #   ReconLine, BatchRecon, OrderMatch, OrderReconResult
│   ├── matching.py         # match(), match_settlements(), group_batches(), match_orders()
│   ├── parsers.py          # load_csv(), parse_razorpay_settlements(),
│   │                       #   parse_razorpay_recon(), parse_payu_*(), load_recon_csv(),
│   │                       #   parse_date/amount, split_cashfree_recon_report()
│   ├── exports.py          # export_tally_csv(), export_gst_worksheet(),
│   │                       #   export_tds_1035(), format_money()
│   ├── exceptions.py       # classify(), build_llm_prompt(), Exception
│   ├── pdf.py              # optional [pdf] extra (pymupdf): extract_pdf_text(),
│   │                       #   parse_sbi_statement() -> parse_sbi_pdf() (YONO/netbanking/credit-card)
│   ├── ocr.py              # optional [ocr] extra (tesseract): parse_sbi_scanned_pdf()
│   ├── __main__.py         # the CLI: python -m settleflow reconcile ...
│   └── schemas.py          # ColumnMap, BankColumnMap, ReconColumnMap, *_MAPS, load_* helpers
├── saas/
│   ├── app.py              # FastAPI: /reconcile (sync, work-capped), /r/<token>,
│   │                       #   /r/<token>/export/*, /health, /static (brand assets)
│   ├── helpers.py          # stdlib-only helpers (decoding, column guess,
│   │                       #   peer-aware rate-limit identity, one-mailbox email)
│   ├── templates/          # index.html, results.html, page.html, error.html,
│   │                       #   _head/_style/_brand/_footer partials (Jinja2)
│   ├── static/             # logo/favicon/OG card/banner + real UI screenshots
│   └── requirements.txt    # fastapi, uvicorn, jinja2, python-multipart
└── tests/
    └── test_matching.py    # assert-based self-check
```

`__init__.py` is the only public boundary. Everything a user imports comes from it. The
submodules use relative imports (`.models`, `.matching`, `.parsers`, `.exports`,
`.exceptions`, `.schemas`).

## Data model (models.py)

| Type | Kind | Fields | Notes |
|---|---|---|---|
| `MatchStatus` | enum | `EXACT`, `AMOUNT_MISMATCH`, `AMOUNT_DATE`, `UNMATCHED` | the four reconciliation outcomes |
| `Txn` | frozen dataclass | `utr`, `amount`, `txn_date`, `ref` | one side of a reconciliation; `.key` = normalized UTR |
| `Match` | dataclass | `settlement`, `bank`, `status` | a paired result |
| `ReconResult` | dataclass | `matched`, `settlement_only`, `bank_only` + total properties | the full outcome |
| `Settlement` | frozen dataclass | `settlement_id`, `amount`, `created_at`, `utr`, `fees`, `tax` | a gateway settlement batch |
| `ReconLine` | frozen dataclass | 24 recon fields (see below) + `net` property | one line of a recon report |
| `BatchRecon` | dataclass | `settlement_id`, `utr`, `lines` + gross/fees/taxes/refunds/net | one batch's netting |
| `OrderMatch` | dataclass | `line`, `order`, `status` | a recon line matched to an order row |
| `OrderReconResult` | dataclass | `matched`, `refund_links`, `unmatched_lines`, `unmatched_orders`, `adjustments` | level-2 outcome |

**Invariant:** every `amount` field is a `Decimal` in **rupees**. The paise-to-rupee
conversion happens in the parser, never in the model or the matcher.

## Matching algorithm (matching.py)

`match(settlements, bank) -> ReconResult` is deterministic and two-pass (see
`docs/FLOW.md` for the exact trace).

`group_batches(lines)` groups `ReconLine` rows into `BatchRecon` by `settlement_id`.

`match_orders(lines, orders)` is level-2: it joins `payment` lines to the merchant order
ledger by `order_id` (normalized), links `refund` lines back to their originating
payment via `payment_id`, sets `adjustment` lines aside for review, and falls back to
(amount, date). Consumption is by list index.

## Parser layer (parsers.py)

- `load_csv(path, utr_col, amount_col, date_col, ref_col=None)` -> `list[Txn]`. Column
  names are **explicit arguments**, so any vendor or bank layout plugs in without
  vendor-specific code.
- `parse_razorpay_settlements(data)` -> `list[Settlement]` (documented API schema).
- `parse_razorpay_recon(data)` -> `list[ReconLine]` (24 documented params of
  `GET /v1/settlements/recon/combined`). **Fails closed**: unknown or missing fields
  raise `ValueError` rather than silently dropping data (D-15).
- `load_razorpay_recon_json(path)` / `load_recon_csv(path, **explicit columns)`.
- `parse_date`, `parse_amount` are tolerant string parsers.

## PDF layer (pdf.py) — optional extra

A **separate trust boundary** (D-20): the core stays stdlib-only, so PDF support is
`pip install "settleflow[pdf]"` (pulls `pymupdf`), imported lazily so `import settleflow`
never requires it. Entry points:

- `extract_pdf_text(path)` — pull the text layer of a PDF, raising a specific error for
  a **password-locked** (`PdfEncryptedError`) or **scanned/image-only** (`PdfScannedError`)
  file. `PdfLayoutError` covers a recognised-but-unsupported layout.
- `parse_sbi_statement(text)` — auto-dispatches an SBI statement text to one of three
  layouts (D-23): modern **YONO / e-statement** (4-column money tail, rows may wrap),
  legacy **netbanking** (`Txn Date | Value Date | Description | Ref No. | Debit | Credit |
  Balance`), and **credit-card** (`Date | Description | Amount (Rs.)`, `Cr` marker).
  Credit -> positive amount, debit -> negative; narration -> `Txn.ref`, reference number ->
  `Txn.utr`.
- `parse_sbi_pdf(path)` — `parse_sbi_statement(extract_pdf_text(path))` in one call.

The YONO parser reconstructs each transaction from the **trailing money columns**
(`ref / credit / debit / balance`), never from a guessed column width, because a long
narration wraps onto several lines in the extracted text. Verified against real
anonymised SBI statements (`tests/fixtures/sbi/`, Apache-2.0). **Not handled (raise)**
rather than half-parsed: legacy netbanking via PDF (use the CSV export), scanned PDFs
(needs OCR — a separate, unbuilt layer), and encrypted PDFs (decrypt externally).

## Schema registry (schemas.py)

Vendor/bank formats are **column-map data**, not code. The registry ships three maps:
`SETTLEMENT_CSV_MAPS` (batch files -> `ColumnMap`), `BANK_STATEMENT_MAPS` (two-column
debit/credit -> `BankColumnMap`), and `RECON_CSV_MAPS` (line items -> `ReconColumnMap`).
Every wired map traces to a verified header in `docs/SCHEMAS.md`. Any slot still `None`
raises a clear "needs a real sample" error when called — the D-7 posture, never a
guessed schema.

## Exception layer (exceptions.py)

`classify(result, as_of, stale_after_days)` applies priority-ordered rules to produce
`Exception` rows: `FEE_DRIFT`, `DUPLICATE_SUSPECT`, `STALE_SETTLEMENT`,
`DIRECT_TRANSFER`, `MANUAL_REVIEW`. `build_llm_prompt(exceptions)` formats a triage
prompt; the core never calls an LLM (that is the SaaS layer's job).

## Export layer (exports.py)

Tally bank-receipt CSV, GST netting worksheet, and TDS code-1035 deduction worksheet.
All stdlib `csv` + `Decimal`.

## SaaS layer (saas/)

FastAPI app over the core. `POST /reconcile` parses an uploaded settlement file
(Razorpay settlements or recon JSON, plus the other wired kinds) + bank CSV, runs
the matcher + classifier, persists the run to sqlite3, and serves generated CSVs.
Deliberately thin: no ORM, no auth, no user model. Since 0.7.5 the resource
guards are part of the architecture, not bolted on: per-identity rate limit keyed
on the tunnel peer rule (helpers.pick_client_ip + D-41), an identity-independent
global window, `MAX_STATEMENT_ROWS` (bound the derived work, not the bytes), a
2-slot concurrency semaphore, and a synchronous reconcile handler so heavy work
never touches the event loop. Every bound is an env-tunable constant. The UI is
WCAG 2.2 AA by computed contrast (`docs/UI-AUDIT.md`), brand assets under
`saas/static/` served from `/static` (public, cacheable — deliberately outside
the no-store run paths).

## Data flow

```
CSV / JSON                                    PDF (optional [pdf])
   │  load_csv / parse_razorpay_settlements /     │  extract_pdf_text(path)
   │  parse_razorpay_recon                        │  parse_sbi_pdf / parse_sbi_statement
   ▼                                              ▼
list[Txn] | list[Settlement] | list[ReconLine]   list[Txn]
   └──────────────┬────────────────────────────────┘
                  │  match_settlements / group_batches(+match) / match_orders
                  ▼
ReconResult / OrderReconResult  ── classify() ──► list[Exception]
   │
   └─► export_tally_csv / export_gst_worksheet / export_tds_1035
```

## Extension: add a vendor parser

1. Get the real schema from the vendor's docs or a real sample file (never guess).
2. If it is a column-map CSV, fill the `ColumnMap`/`ReconColumnMap` in `schemas.py`.
   If it is an API JSON, write a `parse_<vendor>(...)` returning `list[Txn]`/`list[Settlement]`.
3. Export it from `settleflow/__init__.py`.
4. Add a test using verbatim sample data to `tests/test_matching.py`.
5. Log the decision in `docs/DECISIONS.md`.

## Design invariants

- **Decimal everywhere**, never `float`, for any amount.
- **Deterministic**: no reliance on dict iteration order in the output.
- **Zero runtime dependencies** in the library core: stdlib only (SaaS may use FastAPI;
  `pdf.py` is an optional `[pdf]` extra pulling `pymupdf`, never imported at package load).
- Money in the model is **rupees**; unit conversion lives only in parsers.
- **Fail closed** on unknown vendor data: raise, never silently coerce or drop.
