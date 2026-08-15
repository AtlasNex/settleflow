# Architecture

The system map. Read this before touching anything so you do not work blind.

## Package layout

```
settleflow/
├── pyproject.toml          # name=settleflow, zero runtime deps, setuptools
├── settleflow/
│   ├── __init__.py         # public API surface (exports)
│   ├── models.py           # data model: Txn, Match, MatchStatus, ReconResult, Settlement
│   ├── matching.py         # match(), match_settlements()
│   └── parsers.py          # load_csv(), parse_razorpay_settlements(), parse_date/amount
└── tests/
    └── test_matching.py    # assert-based self-check (the single runnable check)
```

`__init__.py` is the only public boundary. Everything a user imports comes from it. The
submodules use relative imports (`.models`, `.matching`, `.parsers`), so renaming the
package only touches `__init__` + `pyproject` + the test import.

## Data model (models.py)

| Type | Kind | Fields | Notes |
|---|---|---|---|
| `MatchStatus` | enum | `EXACT`, `AMOUNT_MISMATCH`, `AMOUNT_DATE`, `UNMATCHED` | the four reconciliation outcomes |
| `Txn` | frozen dataclass | `utr`, `amount`, `txn_date`, `ref` | one side of a reconciliation; `.key` = normalized UTR |
| `Match` | dataclass | `settlement`, `bank`, `status` | a paired result |
| `ReconResult` | dataclass | `matched`, `settlement_only`, `bank_only` + total properties | the full outcome |
| `Settlement` | frozen dataclass | `settlement_id`, `amount`, `created_at`, `utr`, `fees`, `tax` | a gateway settlement batch |

**Invariant:** every `amount` field is a `Decimal` in **rupees**. The paise-to-rupee
conversion happens in the parser, never in the model or the matcher.

## Matching algorithm (matching.py)

`match(settlements, bank) -> ReconResult` is deterministic and two-pass:

1. **Index** bank lines by normalized UTR into `bank_by_utr`.
2. **Pass 1 (exact):** for each settlement with a UTR, take a bank line with the same
   normalized UTR. Same amount -> `EXACT`; different amount -> `AMOUNT_MISMATCH` (kept,
   so a human sees it). No UTR match -> goes to `pending`.
3. **Pass 2 (amount+date):** index the still-free bank lines by `(amount, date)`. For
   each pending settlement, take a free bank line with the same amount and date ->
   `AMOUNT_DATE`. Else -> `settlement_only`.
4. Any bank line never consumed -> `bank_only`.

Bank lines are tracked by **list index** (not object identity), so two rows with
identical values are still treated as distinct.

`match_settlements(settlements, bank)` converts each `Settlement` to a `Txn`
(`ref = settlement_id`) and delegates to `match()`. It exists because the bank UTR is
the correspondent bank's, not the gateway's; the (amount, date) fallback is what pairs
them in practice.

## Parser layer (parsers.py)

- `load_csv(path, utr_col, amount_col, date_col, ref_col=None)` -> `list[Txn]`. Column
  names are **explicit arguments**, so any vendor or bank layout plugs in without
  vendor-specific code. The mapping for a given vendor is a dict, filled from a real
  sample file, never guessed.
- `parse_razorpay_settlements(data: dict)` -> `list[Settlement]`. Reads the documented
  Razorpay `Fetch All Settlements` schema (`id`, `entity`, `amount`, `fees`, `tax`,
  `utr`, `created_at`). `amount`/`fees`/`tax` are integers in **paise** and are divided
  by 100; `created_at` is an epoch second converted to a UTC `date`. Non-settlement
  entities are skipped.
- `parse_date`, `parse_amount` are tolerant string parsers (multiple date formats;
  currency symbols/commas stripped; parenthesized negatives).

## Data flow

```
CSV / JSON
   │  load_csv / parse_razorpay_settlements
   ▼
list[Txn] or list[Settlement]
   │  (Settlement -> Txn via match_settlements)
   ▼
match() ── two-pass ──► ReconResult { matched, settlement_only, bank_only }
```

## Extension: add a vendor parser

1. Get the real schema from the vendor's docs or a real sample file (never guess).
2. Write a `parse_<vendor>(...)` function that returns `list[Txn]` or `list[Settlement]`.
3. Export it from `settleflow/__init__.py`.
4. Add a test using verbatim sample data to `tests/test_matching.py`.
5. Log the decision in `docs/DECISIONS.md`.

## Design invariants

- **Decimal everywhere**, never `float`, for any amount.
- **Deterministic**: no reliance on dict iteration order in the output.
- **Zero runtime dependencies**: stdlib only. Any new dependency needs a DECISIONS entry.
- Money in the model is **rupees**; unit conversion lives only in parsers.
