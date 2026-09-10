# Cashfree fixture — SYNTHETIC, no real merchant data

This directory contains **no real settlement data.** Every row is invented. The
file exists to test a parser and to hold the two-section shape, nothing else.

## What is real here and what is not

- **Real:** both header rows, verbatim, and the section marker line
  (`** Settlement Reconciliation Details **`). The 14-column batch header and the
  63-column event header were read out of a real, publicly committed
  (header-only) Cashfree Settlement Recon export, listed with its URL in
  `docs/RESEARCH-gateway-samples.md` §1a. Header names are facts.
- **NOT real:** every `Id`, `Event Id`, UTR (`AXNCFTESTUTR…`), order reference,
  amount, fee, tax and customer value. The real file was committed by someone else
  and had no data rows; the rows here were generated so the parser has something
  to read.

## Why the real file is not vendored

It is a named merchant's export path in an unrelated public repository. Copying it
in would re-publish someone else's data, which is not a licensing question a NOTICE
file can settle — the same reasoning as D-19 (banks) and the PhonePe fixture.

## What the fixture proves

The event section's netted total equals the batch section's total
(`5881.12`), which is the assertion that fails if the `Sale Type` direction flag is
applied to the gross `Event Amount` instead of the money-movement
`Event Settlement Amount`. See `docs/DECISIONS.md` D-34.

## Source

- `docs/RESEARCH-gateway-samples.md` §1a (the real file URL, fetched 2026-09-11)
  and §1b (Cashfree's official per-column sample values, incl. the
  `Sale Type ∈ {CREDIT, DEBIT}` and `Event Type` enums).
- Column maps live in `settleflow/schemas.py`
  (`cashfree_settlement_csv`, `cashfree_recon_csv`).
