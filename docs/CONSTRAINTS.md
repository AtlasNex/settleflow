# Constraints

The things an AI (or any contributor) must **never** touch. These exist so a future
session cannot silently break the invariants the whole design depends on. Each rule is
paired with its reason (full reasoning in `docs/DECISIONS.md`).

## Hard rules (never violate)

1. **Money is `Decimal`, never `float`.** Floating-point breaks reconciliation math
   (₹0.1 + ₹0.2 != ₹0.3). Violation = silently wrong ledgers.
2. **Never fabricate a vendor schema.** Column/field names must come from official docs
   or a real sample file. Guessing a schema is how the Nova zoning layer got fabricated
   `(GUESS)` rows and broke. If the format is not verifiable, raise, do not invent.
3. **The matching algorithm stays deterministic.** No reliance on hash/dict order for
   correctness. If you change the algorithm, run the self-check and add a test for the
   new case.
4. **Model amounts are rupees.** Paise-to-rupee conversion happens only inside parsers.
   Do not move it into `models.py` or `matching.py`.
5. **UTR normalization is alphanumeric + uppercase, nothing else.** Do not strip other
   characters, trim differently, or lowercase. Changing this changes every match key.
6. **Zero runtime dependencies.** stdlib only. Any new dependency requires a
   `DECISIONS.md` entry and a good reason (there is none yet). Optional extras
   are allowed as long as the core stays importable with zero deps (see D-17
   SaaS extras; D-21 added an optional `[pdf]` extra pulling pymupdf, imported
   lazily only when a PDF is parsed).
7. **License stays MIT.** Do not re-license without Sanjay.
8. **No test framework.** The assert-based self-check (`python tests/test_matching.py`)
   is the standard. Do not introduce pytest/tox unless Sanjay asks.
9. **Never force-push or rebase published history.** Rollback is by revert, not rewrite.
10. **Do not rename the package again** without a traceable diff plus a `DECISIONS.md`
    entry. The name `settleflow` is a working placeholder.

## Soft rules (default unless there is a reason)

- One change per request, small and reviewable.
- Read every diff before committing.
- Ask "why" before "what": trace the actual flow before writing 200 lines.
- Verify before claiming done; paste real output, never narrate past a failure.
- Closeouts separate DONE / DEFERRED / ABORTED / SKIPPED. Never mark deferred as done.

## Trust boundaries (validate here)

- **Parsers** are the trust boundary: external files (CSV/JSON) may be malformed,
  hostile, or in the wrong unit. `parse_date`/`parse_amount` must raise a clear
  `ValueError`, never silently coerce.
- **Public API** (`settleflow/__init__.py`) is the other boundary: it is the only thing
  users import, so keep its exports explicit and stable.

## Known ceilings (marked for upgrade)

- `match()`'s amount+date fallback can mis-pair when two distinct bank lines share the
  same (amount, date). This is a deliberate first-pass simplification; the upgrade path
  is UTR-based disambiguation or order-level matching (Phase 2, now built via
  `match_orders`).
- PDF bank statements: the modern SBI YONO, the legacy netbanking, and the
  credit-card layouts are all parsed (`settleflow/pdf.py`, D-21/D-23). Still
  deferred: scanned/image-only PDFs (`PdfScannedError`; OCR is a separate
  unbuilt layer).
