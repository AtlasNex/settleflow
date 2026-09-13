# User guide

Who this is for: a merchant, accountant or finance ops person in India who has a
payment-gateway settlement export and a bank statement, and needs to prove the
payout that landed matches what the gateway says it sent — and to hand the
result to Tally in the format the books expect.

Three ways to use SettleFlow, in increasing order of control:

| | Get started with | You get |
|---|---|---|
| 1. Hosted service | open [settleflow.atlasnex.com](https://settleflow.atlasnex.com) | browser upload, workpaper downloads |
| 2. CLI | `pip install "settleflow @ git+https://github.com/AtlasNex/settleflow.git"` | the same engine, fully offline |
| 3. Library | same install, then `import settleflow` | every step individually |

Nothing about your data leaves your machine in options 2 and 3. The hosted
service stores the run record for 30 days and deletes the uploads immediately
(see the [privacy page](https://settleflow.atlasnex.com/privacy)).

## Step 1 — get the right two files

**Settlement side.** From the gateway, export a settlement file for the period:

- **Razorpay**: dashboard → Settlements → *Settlements* report (CSV) for batch
  level, or the **Settlement Recon** report (CSV/API JSON) for line-item level.
  Line-item is the better file: it is what unlocks the GST and TDS workpapers.
- **PayU**: the `/settlement/range` (batch) or `/settlement/transactionDetails`
  (line-item) API JSON.
- **Cashfree**: the *Settlement Recon* report — the one with two sections; both
  are handled, pick the event section for line items.
- **PhonePe / Juspay**: the settlement report / settlement file exports.

**Bank side.** The statement covering the same period, as CSV or (for SBI) PDF.
Download it from netbanking — a *transaction* export, not a balance certificate.
One bank line will usually be the whole payout: UPI settles as bulk NEFT credit,
which is exactly the mess this tool cleans up.

## Step 2 — run it

CLI, one command:

```bash
python -m settleflow reconcile \
    --settlements settlements.csv --vendor razorpay_settlement_csv \
    --bank sbi --statement statement.csv --out-dir out
```

`--bank` accepts `sbi | hdfc | icici | axis | kotak | pnb | dbs`.
`--vendor` keys are listed in `settleflow/schemas.py` (e.g.
`razorpay_recon_csv`, `cashfree_recon_csv`). SBI statements only: a `.pdf`
works directly, add `--ocr` for scanned PDFs (needs `pip install "settleflow[ocr]"`
plus a system Tesseract). `--as-of 2026-09-30` dates the stale-settlement check
when a statement header does not carry a date.

The CLI prints the counts (settlements / bank lines / matched / unmatched /
exceptions) and exits `2` with a one-line reason if a file cannot be read — a
refusal is never silent.

Hosted: pick the settlement kind, drop both files, press **Reconcile**. If your
statement's columns are unusual, the form's *Advanced* section lets you name the
UTR / amount / date columns yourself; otherwise they are detected and the run
page shows what it read — check it, because wrong columns mean a confidently
wrong answer.

## Step 3 — read the result

Every output separates three states, always with the money attached:

- **Matched** — gateway row ↔ bank credit. The run page's *How* column says
  which rule paired them (`exact` on normalized UTR, or the `amount+date`
  fallback when your bank's UTR is the correspondent bank's — which it usually is).
- **In gateway, not in bank** — money the gateway says it paid out that your
  bank has not credited (yet). This is the unpaid-payout alarm.
- **In bank, not in gateway** — money that landed with no settlement behind it:
  a direct transfer, an old payout, or someone else's credit.
- **Exceptions** — the rows a person must look at: fee drift (amounts within a
  small band but not equal), duplicates, stale settlements, sign-reversal
  candidates. The page numbers each with a category code; `exceptions.csv` /
  the JSON export carry the same.

## Step 4 — the workpapers

The download buttons produce exactly the files an accountant books from:

| File | What it is | When |
|---|---|---|
| `tally.csv` | Bank-receipt rows, one per settlement, unmatched rows flagged `PENDING_BANK` | every run |
| `gst.csv` | GST netting worksheet (gross, MDR, GST on MDR, refunds, net) | line-item runs |
| `tds1035.csv` | TDS code-1035 (ex-194O) worksheet — 0.1% aggregation, ₹5L individual exemption handled | line-item runs |

Amounts are rupees with two decimals, no formula cells (anything a spreadsheet
could evaluate is neutralised), and the CSVs are UTF-8 with the exact column
names documented in `docs/SCHEMAS.md`.

## Step 5 — when the numbers do not look right

1. **Check the column mapping** shown on the run page first — the single most
   common cause of a wrong reconciliation is a wrong column, and the page tells
   you what it used.
2. **Totals**: the summary's three totals must satisfy *matched + unmatched
   (each side)* = file totals. SettleFlow always reconciles arithmetically;
   if your expectation does not, look at which bucket the difference sits in.
3. **A format that refuses to load** is intentional if your gateway/ bank is not
   in the supported list: an unverifiable layout is refused rather than guessed.
   Email sanjay@atlasnex.com with a redacted header line and it becomes a
   supported format (see [CONTRIBUTING.md](../CONTRIBUTING.md)).
4. Re-running with `--as-of` (CLI) changes only the stale-settlement window,
   never the matching.

## Limits (stated, not discovered)

- 10 MB per file; 200,000 lines per file; ~60 reconciliations per hour per
  client on the hosted service (these are the hosted guards — the library and
  CLI have no such caps).
- The amount+date fallback can mis-pair when two bank lines share one
  (amount, date); the exception list surfaces these for review rather than
  hiding them.
- This is a matcher and a workpaper generator. It does not file anything, does
  not talk to the income-tax portal, and nothing in it is tax advice.
