# Contributing to SettleFlow

Thanks for taking an interest. SettleFlow is an MIT-licensed, stdlib-only
settlement-reconciliation library for Indian payment gateways and banks. This
project is small and moves deliberately — please read the ground rules before
opening a PR.

## The two rules that matter most

1. **Zero runtime dependencies.** The core (`settleflow/`) must stay
   importable on a clean Python ≥ 3.10 with nothing but the standard library
   installed. Optional integrations (PDF parsing, OCR, the SaaS layer) live
   behind the `[pdf]`, `[ocr]`, and `[saas]` extras and are imported lazily.
   CI enforces the zero-dependency claim.
2. **No test framework.** The repo's standard is a single runnable assert-based
   self-check: `python tests/test_matching.py`. Do not add pytest, tox, or
   fixtures. If you change matching logic, add checks to that file.

Full never-touch rules: `docs/CONSTRAINTS.md`. Working rules for humans *and*
AI agents: `AGENTS.md`.

## Development setup

```bash
git clone https://github.com/AtlasNex/settleflow
cd settleflow
python tests/test_matching.py   # must print "all N checks passed" (exit 0)
```

Nothing to install. Python 3.10+ (CI runs 3.10, 3.11, 3.12). To work on the
optional SaaS layer: `pip install -e ".[saas]"`.

## Making a change

1. **Open an issue first** for anything beyond a typo — especially new file
   formats. A parser for a bank statement is only acceptable with a real
   sample file or official schema documentation. **Never fabricate a vendor
   schema** (`docs/CONSTRAINTS.md` #2); an unverifiable format will be closed,
   not merged.
2. Branch from `master`, keep it to **one change per PR**, small and reviewable.
3. Money is `Decimal`, never `float`. Model amounts are rupees; paise→rupee
   conversion happens only inside parsers.
4. UTR normalization is alphanumeric + uppercase, nothing else. It is the
   match key for the whole engine.
5. Keep output deterministic — never rely on dict/hash ordering.
6. Run the self-check before pushing. CI will too.
7. Update `docs/SCHEMAS.md` (with sources) when adding/altering a format.

## Pull requests

- Explain *why*, then *what*. Link the issue.
- For behavior changes: show the self-check output in the PR.
- A docstring or comment should answer "why", not restate the code.
- Maintainers may ask you to squash; we never force-push published history —
  rollbacks are reverts (`docs/ROLLBACK.md`).

## Bug reports

Use the issue template. The most useful bug report contains: the exact vendor
file header line (with account numbers/amounts redacted), what matched that
shouldn't have (or vice versa), and the output of the self-check. Screenshots
of ledgers help less than one redacted CSV row.

## Security issues

Do **not** open a public issue for anything that could expose someone's
financial data. See `SECURITY.md`.

## License

By contributing you confirm the contribution is yours to license and agree it
is contributed under the MIT License, with no additional restrictions.
