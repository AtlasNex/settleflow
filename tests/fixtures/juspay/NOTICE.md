# Juspay fixtures — SYNTHETIC, no real merchant data

Neither file is a real Juspay settlement file. **No real populated Juspay file has
ever been seen by this project** — that is exactly why the loader carries a
`NOT VERIFIED` block, and these fixtures exist to pin the column names and the
arithmetic, not to prove the format.

## What is real here and what is not

- **Real:**
  - `settlement_docs_schema_synthetic.csv` — the 25 column headers, verbatim from
    Juspay's official Settlement Files schema page.
  - `settlement_utr_variant_synthetic.csv` — the header NAMES that Juspay's own
    production parser matches on (nammayatri/shared-kernel, YesBiz module),
    including `UTR Number` and `Partner Amount`, which the docs schema does not
    have. The column ORDER in this fixture is **not** claimed to be real: that
    parser looks columns up by name, so only the names are known.
  - The enums used (`Settlement Status`, `Transaction Type`, `Type`) come from the
    same two sources.
- **NOT real:** every merchant id, UPI request id, RRN, UTR, VPA, order id and
  amount.

## What is NOT verified (and why these fixtures cannot fix it)

- The **money unit**. The docs say only "Integer"; Juspay's own parser reads plain
  rupee decimals, so the loader assumes rupees. A real file would settle it.
- Whether one `Settlement Date` is one bank credit. The documented schema carries
  no batch id and no UTR column, and the fixture cannot invent that fact.
- The `Settlement Status` filter (only `Settled` means the funds reached the bank).

## Licensing

`nammayatri/shared-kernel` is AGPL-3.0, © Juspay India Ltd. Column *names* and
value semantics are facts and are transcribed here; **no code was copied** from it.

## Source

- `juspay.io/pe/docs/upi-merchant-stack-pe/docs/resources/settlement-files`.
- `docs/RESEARCH-gateway-samples.md` §3a/§3b.
- Loader: `settleflow/schemas.py` (`load_juspay_settlement_csv`).
