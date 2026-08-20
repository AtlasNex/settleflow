# Fixture attribution

`kotak_savings-jul-2025.txt` is the anonymised text layer of a real Kotak
Mahindra Bank savings-account statement, copied from the Apache-2.0 project
[`raptar231/indian-bank-statement-parser`](https://github.com/raptar231/indian-bank-statement-parser)
(`tests/fixtures/kotak/`). It is used only to verify
`settleflow.parsers.parse_drcr_statement` against the real Kotak "combined
amount + Dr/Cr marker" layout (never guessed, D-7). Account holder name,
account number, and branch are already anonymised in the source.

License: Apache License 2.0. See
<https://github.com/raptar231/indian-bank-statement-parser/blob/HEAD/LICENSE>.
