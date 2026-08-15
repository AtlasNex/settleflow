# upirecon (working name)

Open-source UPI/NPCI settlement reconciliation for India.

Reconcile payment-gateway settlement files against bank statements: parse
settlement/bank CSVs, match by RRN/UTR, and flag the exceptions.

## Status — first increment (in progress)

- [x] Data model (`Txn`, `Match`, `ReconResult`, `Settlement`)
- [x] Deterministic RRN/UTR matching engine (exact UTR → amount+date fallback → unmatched)
- [x] Settlement-level matcher (`match_settlements`)
- [x] Generic CSV loader with explicit column mapping
- [x] Razorpay settlement parser (real API schema: paise→rupee, epoch→date)
- [ ] More vendor parsers (Cashfree, PayU, PhonePe, Juspay) + bank statements
- [ ] Hosted SaaS (later)

## Why

UPI settles T+1 as bulk NEFT credits that only disaggregate via the
aggregator's settlement file. 200–300 UPI collections/month = 8–12 hours of
manual reconciliation. The open-source component layer (parsers + matching)
is owned by nobody.

## Run the self-check

```bash
python tests/test_matching.py
```

## Usage

```python
from datetime import date
from decimal import Decimal

from upirecon import Txn, match

settlements = [Txn("123456789012", Decimal("100.00"), date(2026, 8, 15), ref="order_1")]
bank = [Txn("123456789012", Decimal("100.00"), date(2026, 8, 16))]
result = match(settlements, bank)
print(result.matched)  # one exact match
```
