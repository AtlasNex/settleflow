# Flow

Exact execution trace. Follow a call from entry to exit so the flow is legible, not
just functional.

## Import graph

```
settleflow/__init__.py
  ├── from .models      import Match, MatchStatus, ReconResult, Settlement, Txn,
  │                        ReconLine, BatchRecon, OrderMatch, OrderReconResult, normalize_utr
  ├── from .matching    import match, match_settlements, group_batches, match_orders, normalize_ref
  ├── from .parsers     import load_csv, parse_amount, parse_date,
  │                        parse_razorpay_settlements, parse_razorpay_recon,
  │                        load_razorpay_recon_json, load_recon_csv
  ├── from .exports     import export_tally_csv, export_gst_worksheet, export_tds_1035
  ├── from .exceptions  import Exception, classify, build_llm_prompt
  └── from .schemas     import ColumnMap, ReconColumnMap, load_settlement_csv,
                          load_bank_statement, load_vendor_recon_csv, *_MAPS

settleflow/matching.py  -> from .models import (…)
settleflow/parsers.py   -> from .models import ReconLine, Settlement, Txn
settleflow/exports.py   -> from .matching import group_batches
settleflow/schemas.py   -> from .parsers import load_csv, load_recon_csv
```

No circular imports. `models.py` imports nothing from the package.

## `match(settlements, bank) -> ReconResult`

1. `result = ReconResult()` (empty buckets).
2. Build `bank_by_utr: dict[str, list[(index, Txn)]]` — only for bank lines with a
   non-empty `.key` (normalized UTR). `consumed: set[int]` tracks taken bank indices.
3. `take(candidates, amount)`: inner helper. Prefer a same-amount free line, else the
   first free line. Marks the index consumed and returns the `Txn`.
4. **Pass 1** — for each settlement `s`:
   - if `s.key` is non-empty, `take(bank_by_utr[s.key], s.amount)`.
   - on hit: status = `EXACT` if amounts equal else `AMOUNT_MISMATCH`; append `Match`.
   - on miss (or no UTR): append `s` to `pending`.
5. **Pass 2** — rebuild `by_amount_date: dict[(amount, date), list[(index, Txn)]]` from
   the bank lines **not** consumed. For each `pending` settlement:
   - `take(by_amount_date[(s.amount, s.txn_date)], s.amount)`; hit -> `AMOUNT_DATE`,
   else -> `settlement_only`.
6. `bank_only` = every bank line whose index was never consumed.
7. Return `result`.

## `match_settlements(settlements, bank) -> ReconResult`

1. Convert each `Settlement` to `Txn(utr=s.utr, amount=s.amount, txn_date=s.created_at,
   ref=s.settlement_id)`.
2. Return `match(txns, bank)`. The `ref` (= settlement_id) rides through on the `Txn`
   so the caller still knows which batch matched.

## `group_batches(lines) -> list[BatchRecon]`

1. Insert each `ReconLine` into a dict keyed by `settlement_id` (defaulting a new
   `BatchRecon` with `utr=line.settlement_utr`).
2. Return the batches sorted by `settlement_id` (deterministic order).

## `match_orders(lines, orders) -> OrderReconResult`

1. Link refunds: for each `type == "refund"` line, if `payment_id` points at a
   `payment` line, record a `(refund, payment)` tuple in `refund_links`.
2. Partition `payment` lines and `adjustment` lines. Adjustments go straight to
   `result.adjustments` (human review).
3. Pass 1: for each payment line, join on `order_id` via `normalize_ref` (case+alnum).
   Hit -> `EXACT` (amounts equal) or `AMOUNT_MISMATCH`; miss -> `pending`.
4. Pass 2: rebuild `(amount, created_at)` index of free orders; join `pending` ->
   `AMOUNT_DATE`; leftover -> `unmatched_lines`.
5. `unmatched_orders` = orders never consumed. Consumption is by **list index**.

## `parse_razorpay_settlements(data) -> list[Settlement]`

1. Iterate `data["items"]`.
2. Skip any item whose `entity != "settlement"`.
3. For each: `amount/fees/tax = _paise(int)` (= value / 100), `created_at =
   _epoch_date(epoch)` (= UTC date from timestamp), `utr = item["utr"]`, `id` ->
   `settlement_id`.
4. Append `Settlement(...)`.

## `parse_razorpay_recon(data) -> list[ReconLine]`

1. Require `data["items"]` to be a list, else `ValueError`.
2. For each item: require `entity_id`, `type`, `settlement_id`, `created_at`; reject any
   field outside `RAZORPAY_RECON_KEYS` + `{credit_type, posted_at}` (fail closed).
3. Money (`debit/credit/amount/fee/tax`) is paise -> rupees via `_paise`; `created_at`/
   `settled_at` are epoch -> UTC date (settled_at may be null).
4. Build `ReconLine` and append.

## `classify(result, as_of, stale_after_days) -> list[Exception]`

Priority-ordered rules over a `ReconResult`:
1. `AMOUNT_MISMATCH` matches -> `FEE_DRIFT`.
2. settlement_only line with a bank_only line sharing (amount, date) -> `DUPLICATE_SUSPECT`.
3. settlement_only older than `as_of - stale_after_days` -> `STALE_SETTLEMENT`.
4. bank_only lines -> `DIRECT_TRANSFER`.
5. remaining settlement_only -> `MANUAL_REVIEW`.

## Exports

- `export_tally_csv(result)` — one row per settlement side (matched / `PENDING_BANK` /
  `UNEXPECTED_CREDIT`), shaped for Tally bank-receipt import.
- `export_gst_worksheet(lines)` — per batch: gross, fee, tax-on-fee, refunds, net.
- `export_tds_1035(lines, ...)` — per payment line: gross, code-1035 TDS (0.1%), net;
  individuals/HUFs below ₹5L gross are `EXEMPT_BELOW_5L`.

## SaaS flow (Phase 4)

`POST /reconcile` (multipart) -> parse settlement (by kind) + bank CSV (explicit
columns) -> `match`/`match_settlements` -> `classify` -> store run + generated CSVs in
`saas/settleflow.db` (sqlite3) -> return summary + exception list + export URLs.

## Test flow

`tests/test_matching.py` inserts the repo root onto `sys.path`, imports from
`settleflow`, then runs each `test_*` function in order under `if __name__ ==
"__main__"`. It is a plain script: `python tests/test_matching.py`, exit 0 on all pass.
