# PayU fixtures — SYNTHETIC, no real merchant data

Both files are **constructed from PayU's official documentation sample payloads**,
with every identifier and amount replaced by an invented one. No real merchant
transaction is represented, and no live API call was made to produce them.

## What is real here and what is not

- **Real:** the response ENVELOPE and the field sets — `status`/`result`/`data`
  for `/settlement/range`, `code`/`message`/`status`/`result` for
  `/settlement/transactionDetails` — plus the per-field money and date formats
  (rupee strings and `YYYY-MM-DD HH:MM:SS[.ffffff]` on `/range`; JSON numbers,
  signed, and `YYYY-MM-DDTHH:MM:SS` on `/transactionDetails`). All of that is
  transcribed from PayU's own docs pages, listed in
  `docs/RESEARCH-gateway-samples.md` §4a/§4b.
- **NOT real:** every `settlementId`, `utrNumber`, `payuId`,
  `merchantTransactionId` and amount.

## Why no CSV fixture

PayU's settlement CSV export has no fixed header — the merchant chooses the columns
per report in a dashboard dialog (PayU's own documentation says so). There is
nothing to take a header from, which is why the CSV path is closed by design and
these two APIs are what the library parses. See `docs/DECISIONS.md` D-35.

## Source

- `docs.payu.in/reference/settlement-detail-range-api.md` (`.md` suffix fetches the
  page without the JS wall).
- `docs.payu.in/reference/settlement_transaction_details_api.md`.
- Parsers: `settleflow/parsers.py`
  (`parse_payu_settlement_range`, `parse_payu_transaction_details`).
