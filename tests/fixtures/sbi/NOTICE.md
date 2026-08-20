# Fixture attribution

These SBI statement text fixtures are the anonymised text layer of real SBI
statements, copied from the Apache-2.0 project
[`raptar231/indian-bank-statement-parser`](https://github.com/raptar231/indian-bank-statement-parser)
(`tests/fixtures/sbi/`), which parses Indian bank statement PDFs. They are used
only to verify `settleflow.pdf.parse_sbi_statement` against the real SBI layout
(never guessed, D-7). Account holder names, account numbers, and contact
details are already anonymised in the source.

- `yono_savings_multi_jan_2026.txt` — modern SBI YONO e-statement (savings).
- `yono_savings_combined_sep_2025.txt` — YONO e-statement with a loan account
  and a savings account (two transaction tables).
- `netbanking_2021_22.txt` — legacy SBI netbanking statement layout (used to
  assert the parser rejects it with `PdfLayoutError`, not to parse it).

License: Apache License 2.0. See
<https://github.com/raptar231/indian-bank-statement-parser/blob/HEAD/LICENSE>.
