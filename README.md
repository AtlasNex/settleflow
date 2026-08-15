# settleflow

> Working name. Open-source UPI/NPCI settlement reconciliation for India.

Parse payment-gateway settlement files and bank statements, then match them so a
merchant can reconcile "what the gateway says I received" against "what actually landed
in my bank." Open-core, MIT, zero runtime dependencies.

## Status

Phase 1 done: data model, two-pass matching engine, settlement-level matcher, generic
CSV loader, Razorpay settlement parser. Self-check green.

## Quickstart

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
python tests/test_matching.py     # self-check (7 checks)
```

```python
from decimal import Decimal
from datetime import date

from settleflow import Txn, match

settlements = [Txn("123456789012", Decimal("100.00"), date(2026, 8, 15), ref="order_1")]
bank = [Txn("1234 5678 9012", Decimal("100.00"), date(2026, 8, 16))]
result = match(settlements, bank)
print(result.matched)             # one exact match (UTR normalized)
```

## The model

Two levels of reconciliation:

1. **Settlement -> bank credit**: match a settlement batch to a bank NEFT credit by
   `settlement_utr`, falling back to (date + net amount).
2. **Line items -> orders**: decompose a batch into order/payment rows (gross - MDR -
   GST - refunds = net). Phase 2.

## Docs

| File | What |
|---|---|
| `MASTER-PLAN.md` | strategy, roadmap, market, monetization |
| `AGENTS.md` | working rules for any AI touching this repo |
| `docs/ARCHITECTURE.md` | system map: files, data model, algorithm, data flow |
| `docs/CONSTRAINTS.md` | never-touch rules |
| `docs/FLOW.md` | execution trace |
| `docs/DECISIONS.md` | the why behind every decision |
| `docs/HANDOVER.md` | where the last session stopped |
| `docs/BUG.md` / `docs/FEATURE.md` | bug/feature trails |
| `docs/ROLLBACK.md` | the way out |
| `docs/TESTING.md` | test checklist |

## License

MIT. See `LICENSE`.
