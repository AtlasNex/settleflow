# PhonePe fixture — SYNTHETIC, no real merchant data

This directory contains **no real statement or settlement data.** Every value is
invented. The file exists to test a parser, nothing else.

## What is real here and what is not

- **Real:** the 15-column header row and the column semantics. Taken verbatim from
  two publicly committed merchant exports found on 2026-09-11, whose URLs and
  field-by-field evidence are recorded in `docs/RESEARCH-gateway-samples.md`.
  Header names are facts.
- **NOT real:** every `MerchantReferenceId`, `PhonePeReferenceId`, `BankReferenceNo`,
  amount, and store name. `AXNPNTESTUTR…` is a made-up UTR shape; the real files
  carried a named merchant's actual UTRs and order references.

## Why the real files are not vendored

The two source exports contain a named merchant's real settlement UTRs, order
references and amounts, committed publicly in an unrelated repository. Copying them
here would re-publish someone else's financial data. That is not a licensing
question that a NOTICE file solves, so the fixture is regenerated instead — the same
approach used for the bank fixtures (D-19).

## Source

- `docs/RESEARCH-gateway-samples.md` §2a / §2c — the two file URLs, the 23-column
  variant's extra columns, and PhonePe's own column-description CSV.
- Netting rule (`Amount + Fee + IGST + CGST + SGST`) from PhonePe's official
  settlement-report docs, recorded in the same document.
