# Fixture attribution

`dbs_savings-may-2019.txt` is the anonymised text layer of a real DBS Bank
India (digibank) statement, copied from the Apache-2.0 project
[`raptar231/indian-bank-statement-parser`](https://github.com/raptar231/indian-bank-statement-parser)
(`tests/fixtures/dbs/`). It is used only to verify
`settleflow.parsers.parse_bank_text` against the real DBS collapsed-column
layout (never guessed, D-7). Account holder name and account number are already
anonymised in the source.

License: Apache License 2.0. See
<https://github.com/raptar231/indian-bank-statement-parser/blob/HEAD/LICENSE>.
