# Cold-start prompt — continue Conjunction (repo `settleflow`)

Paste this whole file into a fresh Hermes session. It is self-contained: it assumes no memory of the
session that wrote it. Read `docs/HANDOVER.md` "READ THIS FIRST" and this file together before
touching anything.

---

## MISSION

Sanjay's project. **Conjunction** (chosen 2026-09-11, D-37) — an open-core UPI/payment-gateway
settlement-reconciliation engine: a zero-dependency MIT Python core plus a thin FastAPI SaaS at
`https://settleflow.atlasnex.com`. It matches gateway settlements against bank statements and
produces the workpapers a finance team files (Tally CSV, GST worksheet, TDS 1035).

**The four things left, in priority order:**

1. **DECIDE THE DEPLOY (Sanjay's call, blocked on him).** Seven commits of fixes are in the repo,
   tested and pushed, and **inert** — the live box still runs pre-fix v0.7.3 with **165 runs** and
   contains every defect the review found, including a deploy script that would overwrite the live
   database on its next run. Recommended: `deploy → remediate ATL-242 → deploy again` (D-40).
2. **Remediate the 12 Strix findings — ATL-242** (1 high, 5 medium, 5 low, 1 info). Start with
   vuln-0010/0002 (rate-limit identity + bound the work derived from an upload), 0001/0011 (`/notify`
   is unrated and unpruned), then 0005/0007/0009 (small correctness), then the rest.
3. **Owner-gated items — ATL-218** (only Sanjay can do these): PyPI account + token; Proton SMTP creds
   for workpaper email; Cloudflare zone AI-crawl toggle; real sample exports for Juspay/PhonePe/IDFC.
4. **The real-money trial** — the only thing that actually decides the venture: run ONE real
   reconciliation for one real CA/fintech, offline, and hand back the output. Nothing has ever met
   real money. Rename to Conjunction (ATL-230) is deliberately deferred behind this.

---

## THE SINGLE MOST IMPORTANT OPEN QUESTION

**Can a caller supply `CF-Connecting-IP` through the Cloudflare tunnel?**

Everything about the severity of the HIGH finding turns on it. If yes, an unauthenticated caller can
mint a fresh rate-limit bucket per request and compose that with per-request amplification (one
8.5 MB upload inside every advertised limit = ~7 s service-wide stall, ~881 MB peak, ~72 MB durable
DB growth; 4 concurrent = 28 s at a full core, `/health` answered 7 times, ~37 GB/h if sustained).
If no, the finding is not exploitable as written.

**Source review cannot answer this. A live probe from outside can.** Do that first if the deploy has
happened — it is the highest-information five minutes available on this project.

---

## WHERE EVERYTHING IS

- **Repo:** `E:/Sanjay Files/StartUp/open source/settleflow` (Windows, git-bash). Branch `master`.
  Public: `AtlasNex/settleflow`.
- **Live:** `https://settleflow.atlasnex.com` — v0.7.3, 165 runs, retention 30 days.
- **Board:** Multica project **SettleFlow** `1e5c2be2-9967-46b5-8958-4275b73b6ad5`, agent **Hermes PM**
  `a1a9bdd5-f9b8-4505-854a-a4f943a6b17f`. CLI: `multica`.
  ATL-234/235/237/238 `in_review` (review + its remediation) · ATL-241 (plan) · **ATL-242 (Strix
  findings, todo)** · ATL-218 `blocked` (owner-gated) · ATL-230 `todo` (rename).
- **Review reports (OUTSIDE the repo — they are abuse write-ups and the repo is public):**
  `E:/Sanjay Files/StartUp/open source/settleflow-review-2026-09-11-v2.md` (current, 234 lines)
  and `...-v1.md` (superseded).
- **Strix findings, durable copy (the CI artifact expires in 30 days):**
  `E:/Sanjay Files/StartUp/open source/strix-settleflow-2026-09-11/` — 19 files incl.
  `vulnerabilities.json`, 12 per-finding `.md`, `penetration_test_report.md`, `run.json`, SARIF.
- **Deploy:** `bash scripts/deploy.sh` (needs `SETTLEFLOW_HOST` from gitignored `scripts/.deploy.env`
  — present). Rollback: `bash scripts/rollback.sh latest`. Both now exclude `*.db` and `.deploy.env`,
  and the deploy asserts the live run count never drops.
- **Watchdog:** Hermes cron `34f4e54a27d8`, every 15 min, runs
  `C:/Users/sanja/AppData/Local/hermes/scripts/settleflow_canary.py`, state at
  `C:/Users/sanja/AppData/Local/hermes/state/settleflow-canary.log`.
- **Scratch (uncommitted, outside the repo):** `C:/Users/sanja/.multica-tmp/` holds the probes
  (`verify_hosted.py`, `cc_probe.py`, `verify_m3m4.py`), the test-insertion scripts, the commit
  message files, and the issue bodies.

---

## STATE AT CLOSE (2026-09-11)

- Repo clean at **`acc5275`**, pushed. **`hermes verify --skip-start` → `ok: true`**, bootstrap exit 0,
  test exit 0, **all 74 checks passed**, port 8000 clear before and after.
- Zero-dependency core verified (24 modules, all stdlib). Canary 5/5 on the live service.
- CI green; the **Security Scan** workflow runs on `push: master` too and now **fails on exit 2**.
- A GLM-5.3 Strix re-run (`34604701290`) was in flight at close — **check it first**; it is the first
  real test of the exit-2 gate that `264c254` fixed.
- Nothing was deployed. No background processes left by this session except that CI run.

### What shipped this session (8 commits)

| Commit | What |
|---|---|
| `7fc77ef` | **deploy/rollback no longer ship `saas/*.db`** (would have wiped 165 runs) + a run-count tripwire |
| `f38b4ac` | library/CLI: strict `parse_amount` (was 1000× wrong for `'Rs.100'`), fail-closed envelope validation, JSON-not-CSV detection, `csv.writer`, linear `match()` (8k dup-UTR rows 0.655s→0.033s), formula-injection defusing |
| `7b82d50` | saas: rate-limit identity fix, whole-body size cap, **all six wired formats reachable**, exact decimal JSON money, honest copy |
| `342e79d` | docs: seven different check-counts across eight files corrected; `ROLLBACK.md` rewritten (it said "no database, no deploy") |
| `442dac4` | Starlette's own `HTTPException` now gets the branded page (it returned raw JSON) |
| `b14c87a` | CI: Strix routed through CommandCode |
| `264c254` | CI: **fail the build when Strix finds vulnerabilities** (it went green over 12 findings) |
| `acc5275` | CI: GLM-5.3 — deepseek's thinking mode breaks Strix's client |

---

## HARD PITFALLS (each of these has cost real time)

1. **NEVER run a full `hermes verify` on this repo.** It hangs and orphans a process on port 8000
   that answers `/health` 200 while `POST /reconcile` returns 500. Use `hermes verify --skip-start`.
2. **Check port 8000 before and after any verify**, or a stale listener flatters the pass.
3. **A green CI security run is not "no findings"** — read `strix_runs/*/vulnerabilities.json`.
   Ours reported success while holding 12 findings (D-38).
4. **Never commit the origin IP** (repo is public, origin is not in public DNS). The deploy host comes
   from `scripts/.deploy.env`, which is gitignored and must never be committed or quoted.
5. **`scripts/.deploy.env` and `saas/*.db` must never enter a deploy tarball** — that was the C-1
   data-loss bug. The deploy script's tripwire catches it now; don't "simplify" the excludes away.
6. **No `pytest` in this repo by design** (D-8). Tests are assert-based: `python tests/test_matching.py`.
7. **Real vendor files must never be committed** — they carry a named merchant's real UTRs. Fixtures
   are regenerated from the real header with invented values, each with a `NOTICE.md` (D-19/D-21).
8. **`parse_amount` is strict on purpose.** `'Rs.100'` used to become `0.100` — a 1000× silent
   understatement — and `NaN`/`Infinity`/`1e400` reached the exporters' `quantize()`. Do not relax it
   without a specific real file that needs it.
9. **Native Windows Python cannot read MSYS `/e/...` paths** — pass `E:/...` forward-slash paths.
10. **The patch tool mangles quote-escaping on `deploy.sh`/`rollback.sh` remote blocks.** Edit those
    via Python with explicit `chr(92)`/`chr(34)`, and verify with a stub `ssh` that prints the remote
    command.
11. **Cloudflare edge-caches `.csv`.** A removed route keeps serving until purged — that is why every
    run response is `no-store` (D-30) and why run URLs are `noindex`.
12. **Never kill Hermes-owned processes** (agent-stack rule): `Hermes.exe`, `hermes_cli.main serve`,
    `gateway run`, `gee-mcp`. RAM cleanup means extra Cursor-spawned MCP copies only.
13. **Strix model contract:** `LLM_API_BASE` (not `OPENAI_BASE_URL`) for a gateway; never a
    thinking-mode model (reasoning_content round-trip 400s); a 403 `error code 1010` is Cloudflare
    bot-blocking a bare client, not an auth failure (D-39).

---

## BINDING RULES (the repo's own constitution — `docs/CONSTRAINTS.md`, `AGENTS.md`)

- **#2 — no invention.** Vendor formats come from primary sources; parsers **raise** rather than
  silently coerce. If a schema has no verified source, it stays unwired (that is why IDFC is empty).
- **#10 — no renaming without a traceable diff plus a `DECISIONS.md` entry.**
- Ponytail lazy-senior mode: smallest working diff, reuse before writing, deletion over addition,
  one runnable check behind any non-trivial logic.
- Honesty taxonomy in every closeout: **DONE vs DEFERRED vs ABORTED vs SKIPPED**, never inflate.
- Currency as **USD (INR) both**. Never `rm -rf`; verified-path deletes; docker via compose.
- Sanjay's working style: answers first, execute in-session (cron is backup, never the doer), build
  only on an explicit go, and challenge completion claims as well as tech rejections.

---

## HOW TO START

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
git log --oneline -3 && git status --short          # expect clean at acc5275+
python tests/test_matching.py                        # expect: all 74 checks passed
curl -s https://settleflow.atlasnex.com/health       # expect runs >= 165, version 0.7.3
gh run list --workflow=security.yml --limit 3        # did 34604701290 finish? any findings?

# then verify state the recorded way (never a full verify):
hermes verify --skip-start --json

# check the board, then ask Sanjay the only open question that blocks progress:
multica issue get ATL-242 --output json | head -40
```

**First question to Sanjay:** *deploy now, or hold?* Everything else is queued behind that answer,
and the fixes protect nothing until `bash scripts/deploy.sh` runs.
