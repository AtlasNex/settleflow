# Flow

Exact execution trace. Follow a call from entry to exit so the flow is legible, not
just functional.

## Import graph

```
settleflow/__init__.py
  ├── from .models      import Match, MatchStatus, ReconResult, Settlement, Txn, normalize_utr
  ├── from .matching    import match, match_settlements
  └── from .parsers     import load_csv, parse_amount, parse_date, parse_razorpay_settlements

settleflow/matching.py  -> from .models import Match, MatchStatus, ReconResult, Settlement, Txn
settleflow/parsers.py   -> from .models import Settlement, Txn
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

## `parse_razorpay_settlements(data) -> list[Settlement]`

1. Iterate `data["items"]`.
2. Skip any item whose `entity != "settlement"`.
3. For each: `amount/fees/tax = _paise(int)` (= value / 100), `created_at =
   _epoch_date(epoch)` (= UTC date from timestamp), `utr = item["utr"]`, `id` ->
   `settlement_id`.
4. Append `Settlement(...)`.

## `load_csv(path, utr_col, amount_col, date_col, ref_col) -> list[Txn]`

1. Open with `utf-8-sig` (handles BOM), `csv.DictReader`.
2. For each row: `utr` = stripped value or `None`; `amount = parse_amount(row[amount_col])`;
   `txn_date = parse_date(row[date_col])`; optional `ref`.
3. Append `Txn(...)`.

## `parse_date` / `parse_amount`

- `parse_date` tries five formats in order (`%Y-%m-%d`, `%d-%m-%Y`, `%d/%m/%Y`,
  `%Y/%m/%d`, `%d.%m.%Y`); raises `ValueError` on all-miss.
- `parse_amount` strips `,`, `₹`, `Rs`, `rs`, spaces; unwraps parenthesized negatives;
  returns `Decimal`; raises `ValueError` on a bad value.

## Test flow

`tests/test_matching.py` inserts the repo root onto `sys.path`, imports from
`settleflow`, then runs each `test_*` function in order under `if __name__ ==
"__main__"`. It is a plain script: `python tests/test_matching.py`, exit 0 on all pass.
