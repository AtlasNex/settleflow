# Completion record — SettleFlow end-to-end

Date: 2026-09-11 · Baseline at start: `6dc1a31` (later rebased onto `ae1250d`) · Shipped revision: `1e0369d`
Hosted: https://settleflow.atlasnex.com · Repo: https://github.com/AtlasNex/settleflow (public, MIT) · Release: `v0.7.3`

Status vocabulary: **DONE** (verified with the evidence shown) · **PARTIAL** (some of it verified, the
rest named) · **DEFERRED** (not done, not attempted, with the reason) · **BLOCKED** (needs something only
the owner can supply) · **SKIPPED** (deliberately not done).

## Phase 1 — Data safety (the blocker)

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | No unauthenticated data surface | **DONE** | `curl` against the live host: `/runs` → 404, `/runs/1/export/tally.csv` → 404, `/r/1/export/tally.csv` → 404, `/r/1` → 404, `/docs` → 404, `/openapi.json` → 404. Canary check `leak_closed` asserts all six and also that no 404 body contains CSV columns. Legacy rows have NULL `run_token` and are unreachable by design. |
| 2 | Concurrent-upload race | **DONE** | Old code wrote every upload to one fixed path (`saas/upload_bank.csv`). Now a unique `NamedTemporaryFile` per request. `scripts/../race.sh` result: 12 concurrent reconciles (6 with bank A, 6 with bank B) → **12/12 redirects, 12 distinct tokens, 0 runs carrying the other upload's UTR**. |
| 3 | Input bounds | **DONE** | 11 MB upload → 413; `.exe` renamed bank file → 400; non-JSON settlement → 400; nonexistent column override → 400; undetectable columns → 400 naming the headers found; empty CSV → 400. Failures render `error.html`, never a traceback. |
| 4 | Retention true | **DONE** | `_prune()` runs at startup and before every new run; `RETENTION_DAYS=30`; `/health` reports `retention_days: 30`; the live Privacy draft states 30 days. The disk is at 91%, which is why the window is enforced in code. |
| 5 | `/runs/{id}/exceptions` as a data surface | **DONE** | Now `/r/<token>/exceptions`, token-gated, `no-store`, `X-Robots-Tag: noindex`. |

## Phase 2 — Product completeness

| # | Item | Status | Evidence |
|---|---|---|---|
| 6 | Readable results page | **DONE** | `saas/templates/results.html`: matched / gateway-only / bank-only / exception counters, totals, exception table with plain-language meanings, download buttons, and the column mapping actually used. Verified live: a real run renders "Matched 1", total `99736.35`, 1 exception. |
| 7 | Auto-detect columns + Advanced | **DONE** | `guess_columns()` (exact match beats substring; short patterns like `cr` excluded to avoid matching `Description`). 3 new self-checks. Live run with headers `Value Date, Narration, UTR No, Credit` auto-mapped correctly. |
| 8 | Hide `/docs` | **DONE** | `docs_url=None, redoc_url=None, openapi_url=None`; all three 404 live. |
| 9 | Human error messages | **DONE** | `HTTPException` handler + catch-all handler with a logged reference id. Verified: 400 (bad file/columns), 404 (unknown/expired run), 413 (too big), 429 (rate limit) all render the error template. |
| 10 | Self-check grows, stays green | **DONE** | 42 → **50 checks** at the time, plus new `tests/test_zero_dependency_core.py`. The count has kept growing (see `docs/HANDOVER.md` for the current figure) — the command prints it, so trust the command. |

## Phase 3 — Public surface

| # | Item | Status | Evidence |
|---|---|---|---|
| 11 | Footer pages | **DONE** | Live 200: `/about`, `/pricing`, `/contact`, `/privacy`, `/terms`. Footer links every one plus the source repo. |
| 12 | Audit's ready-to-paste sub-head | **DONE** | Used as the starting copy, with one deliberate change: the audit's "files are deleted after" became "*files are used for this one reconciliation; the run record is deleted after 30 days*" — the audit itself warned not to ship an unverified deletion claim. |
| 13 | Lead capture | **PARTIAL** | Form live on the results page. Verified: valid address → `?saved=1` and a row in `leads`; `not-an-email` → `?error=email`. **Email delivery is BLOCKED on Proton SMTP credentials** (`SETTLEFLOW_SMTP_*`). The code never simulates a send: with no SMTP configured it stores the lead and the page says delivery is not wired yet. |
| 14 | SEO/GEO basics | **DONE** | Meta description + `og:` tags on every page (shared `_head.html`), `sitemap.xml` → 200, `llms.txt` → 200, `robots.txt` → 200, real h1/h2 hierarchy, no orphan pages. |
| 15 | Crawler policy | **PARTIAL** | Origin `robots.txt` now allows GPTBot/ClaudeBot/PerplexityBot on the public pages and disallows `/r/` and `/reconcile`. **However this zone's robots.txt is served by Cloudflare's *managed* policy, which takes precedence** — so the practical effect is unchanged until that is switched off in the Cloudflare dashboard (Zone → Settings → AI Crawl Control / managed robots.txt). Not flipped by me: it is a zone-level policy change with blast radius beyond this project. |
| 16 | `brand-context.md` first | **DONE** | Written before the copy; records audience, ICP, the buyer's three objections, and the open-source-engine differentiation. The audit scored without one and flagged that. |

## Phase 4 — Make "open source" true

| # | Item | Status | Evidence |
|---|---|---|---|
| 17 | LICENSE correct | **DONE** | MIT, 21 lines, `raw.githubusercontent.com/AtlasNex/settleflow/master/LICENSE` → 200 anonymously. Repo flipped to **PUBLIC** (owner-approved, after LICENSE/SECURITY/CONTRIBUTING/CI landed). |
| 18 | CI green on push and PR | **DONE** | Run `34523113085`: **6/6 jobs success** — Self-check on 3.10/3.11/3.12, Zero-dependency core, SaaS integration (boots the app and runs the end-to-end canary), Legal drafts present. A pre-existing Strix scan workflow (from another clone, `ae1250d`) is retained and its two required secrets exist. |
| 19 | CONTRIBUTING / SECURITY / templates / provenance | **DONE** | `CONTRIBUTING.md` (72), `SECURITY.md` (66) with a private disclosure route, issue + PR templates, and the four `tests/fixtures/*/NOTICE.md` provenance files remain tracked. |
| 20 | Tagged release + real install path | **PARTIAL** | Release `v0.7.3` published. Source install **verified**: `pip install .` in a clean venv, then imported from a different working directory (`site-packages/settleflow/__init__.py`, version 0.7.3). **PyPI is BLOCKED**: no account or token exists anywhere (checked vault, hermes `.env`, `~/.pypirc`). README already states "Not on PyPI yet" rather than implying otherwise. |
| 21 | README as a front door | **DONE** | Rewritten, truthful about what is *not* built. **Its headline example was broken** (`result.unmatched` does not exist on `ReconResult` — the first code a stranger would run raised `AttributeError`); fixed to `settlement_only`/`bank_only` and verified verbatim in a clean venv. |

## Phase 5 — Ops

| # | Item | Status | Evidence |
|---|---|---|---|
| 22 | Idempotent deploy that fails loudly | **DONE** | `scripts/deploy.sh`. Run three times this session. It refuses to ship on a red self-check, backs up first, restarts, then asserts `/health`, the server-side canary, and the public URL. Two defects found and fixed while using it: it assumed `scripts/`/`docs/` existed remotely (backup aborted), and a `\|\| true` on the tar could have produced an empty archive that still counted as a backup. |
| 23 | Monitoring: health + synthetic canary | **PARTIAL** | `scripts/canary.py` does a **real reconcile round-trip** (upload → private URL → export → leak paths → cache headers) and runs in CI, locally, and on the server. A Hermes cron watchdog runs it every 15 minutes against the public URL with Telegram alerting (first failure, then every 6th, plus a recovery notice); its failure path was verified (`consec` increments, exit 1, no false send). **uptime-kuma dashboard monitor DEFERRED** — creating one needs the kuma admin login, which I do not have and will not guess. |
| 24 | Exercise the rollback | **DONE** | `scripts/rollback.sh latest` was run for real: restored the previous release, restarted, health-checked and canaried. It exposed **two real bugs**: `--list` fell through and was treated as a target, and it validated the restored release with the canary *inside that archive* — so a drill passes while the release is broken, because the old tool shares the old release's blind spot. Fixed to validate with the newest canary; the corrected path was then verified live (extract → run → all checks pass), and the new check was proven to catch a bad release by failing against the pre-cache-fix build. |

## Phase 6 — Closeout

| # | Item | Status | Evidence |
|---|---|---|---|
| 25 | This document | **DONE** | — |
| 26 | HANDOVER / SESSION-LOG / DECISIONS / commits | **DONE** | Updated with this session; 9 commits, one change each, all pushed. |
| 27 | Multica issues per phase | **DONE** | ATL-212 … ATL-218 in the SettleFlow project, assigned to Hermes PM; ATL-218 holds the owner-gated blockers. |

## Findings that were not in the plan

1. **Cloudflare was still serving the leaked CSV after the fix shipped.** Found by probing from
   outside rather than trusting loopback: `cf-cache-status: HIT`, `Age: 2079`, `max-age=14400`.
   Purging a route does not un-publish what the edge already holds. Cached objects were purged via
   the API and run responses are now `no-store`, asserted by the canary.
2. **The public repo would have published the origin IP.** `scripts/deploy.sh` hardcoded
   `root@<origin>`, which is deliberately absent from public DNS. Committing it hands out a route
   that bypasses the Cloudflare rules in front of the origin. The host now comes from
   `SETTLEFLOW_HOST` or a gitignored `scripts/.deploy.env`.
3. **CI as generated would never have run** (targeted branch `main`; this repo is `master`) and its
   zero-dependency job failed on any Windows machine (`pywin32` bootstraps itself pre-user-code), so
   it would have been a permanently-red or permanently-ignored check.
4. **The rate limiter's default (30/h) was too low for the actual user** — a CA reconciling a client's
   month would hit it. Raised to 60/h. (It was the limiter, not a bug, that blocked the first
   concurrency test — worth knowing for next time.)
5. **The README's first example did not run** (see item 21).

6. **A blocking conclusion from a previous session was wrong.** D-24 had recorded Cashfree/PhonePe/
   Juspay/PayU settlement files as unobtainable "merchant-private" exports, which is why those
   parsers sat unwired. Asked to re-check the internet rather than accept it, the search found real
   committed PhonePe merchant exports (with the exact evidence that resolves the old blockers), a
   real Cashfree recon export proving the column count was wrong, official PayU settlement APIs
   with sample JSON, and a fetchable Juspay schema page. It also established where the original
   reasoning failed: for PayU it searched for a CSV that structurally cannot exist. PhonePe is now
   wired; the rest are specified. Recorded as D-33 with the lesson — *a negative result expires,
   and recording what was searched matters as much as the verdict.*

## Not done, and why

- **PayU / PhonePe / Juspay / Cashfree parsers** — **partly unblocked this session.**
  `docs/RESEARCH-gateway-samples.md` (searched at the owner's insistence, against an earlier
  "merchant-private" conclusion) found that **D-24 was partly wrong**: two real committed PhonePe
  merchant exports exist, a real Cashfree recon export proves 63 columns not 48, PayU has two
  officially documented settlement **APIs** (a CSV can never exist — its columns are chosen per
  merchant in a dashboard dialog), and the Juspay 25-column schema page fetches fine.
  **PhonePe is now wired** (`load_phonepe_settlement_csv`, netting per `BankReferenceNo`, tested
  against a synthetic fixture) — with the one gap named in the docstring: the aggregate has never
  been compared against a real bank credit. The rest are specified-and-ready, not guessed:
  Cashfree recon needs a two-section parser, PayU needs API-JSON parsers, Juspay needs its map
  with a money-unit caveat. **IDFC remains genuinely deferred** — no real file or official sample
  exists publicly, and the two community CSV claims contradict each other.
- **PyPI** — blocked on an account/token only the owner can create.
- **Email delivery of the workpaper pack** — blocked on Proton SMTP credentials.
- **Cloudflare managed-robots.txt** — a zone-level policy change, left to the owner.
- **uptime-kuma monitor** — needs the kuma login.

---

## Appendix: verification pass and late findings (end of session)

Added after the main record above, when the closeout verification was run.

### Re-verified at the final revision (`7344c30`)

| Check | Command | Result |
|---|---|---|
| Canonical self-check | `python tests/test_matching.py` | **52/52** |
| Zero-dependency core | `python tests/test_zero_dependency_core.py` | PASS, 24 modules all stdlib |
| Local battery | `bash run.sh` (unpiped) | **pass=40 fail=0**, exit 0 |
| Concurrency regression | `bash race.sh` | 12 issued / 12 tokens / **0 cross-contamination** |
| Recipe verify | `hermes verify --skip-start --json` | `ok: true`, manifest, bootstrap+test exit 0 |
| CI | `gh run list` | **success**, 6/6 jobs |
| Live | `scripts/canary.py --base https://settleflow.atlasnex.com` | **5/5 PASS** |

### Late findings

7. **A stale process can make a *later* verification pass.** A `hermes verify` full run left an orphan
   `uvicorn` on port 8000 (its command line matched the manifest's `start` string verbatim; created
   inside a subagent's execution window). It answered `/health` **200** while `POST /reconcile` returned
   **500** — so any readiness poll, or my own first canary run, was testing a broken *old* process
   rather than the current code. Isolated by checking which PID actually held the port and reading its
   `CommandLine` + `CreationDate`, then re-proving the current revision green on the same port.
   **Rule: before trusting a readiness result, check what is listening.**
8. **A verification result is only as trustworthy as its plumbing.** Running a check script piped into
   `tail` reported "exit code 0" for a run that printed `fail=3` and internally exited 1, because a
   pipeline returns the *last* command's status. The same session found a concurrency test whose three
   "failures" were the harness (12 shells appending to one file on MSYS silently drop lines — 5 of 12
   survived), not the code. **A red result needs the harness ruled out before the code is accused, and
   a green result needs its exit code to be real.**
9. **A subagent's stated mechanism was wrong, and it was the same error the work existed to fix.** Its
   research report recorded `gh search code` returning `[]` "because the token lacks `read:user`".
   Re-testing disproved it — the same token returns hits — and reproduced the true cause:
   `gh api -f q='… csv parser'` (terms ANDed) → 122, vs `q='"… csv parser"'` (literal phrase) → 0.
   An empty result was read as a permission failure, which is structurally identical to D-24 reading
   empty searches as proof that four gateway formats were unobtainable. Corrected in
   `docs/RESEARCH-gateway-samples.md`; the rule now lives in the `research-source-access` skill.
   **Self-reports are hypotheses, including from subagents — verify before recording.**

### Also closed after the main record

- **PhonePe settlement wired** (`load_phonepe_settlement_csv`) — with the per-settlement netting the
  file shape requires, and the single unverified gap named in the docstring (the aggregate has never
  been compared to a real bank credit). Two new checks; 50 → 52.
- **D-33** recorded: D-24's "merchant-private" conclusion was wrong for four of five targets, and the
  PayU search had been aimed at a CSV that structurally cannot exist.
