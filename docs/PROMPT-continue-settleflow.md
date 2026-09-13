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

**State change since the last cold-start: ATL-242 IS REMEDIATED (2026-09-13, session 18, all 12
findings, pushed at `6569162`, issue in_review).** D-40's `deploy → remediate → deploy` now needs
its SECOND deploy. The things left, in priority order:

1. **Deploy 0.7.5** — the session-17 brief said: "the sequence is already authorised in shape;
   say go again anyway." Say go, then `bash scripts/deploy.sh` (same verified-externally ritual
   as ATL-246: `/health` version+runs, origin greps, backup, canary). The fixes ride on
   `6569162`: peer-aware rate-limit identity + global window, notify throttle+prune, one-mailbox
   email, sync reconcile + row/concurrency caps, formula-initiator set, money/date/epoch bounds,
   PDF/OCR ceilings. D-42 records the design decisions. Self-check is 77 checks now.
2. **The security gate needs a Nous Portal API key — owner-gated on Sanjay, one click.** He directed
   "any free LLM from Nous, long context, smart" after CommandCode ran dry. **Already verified with
   the portal OAuth JWT: `z-ai/glm-5.3` on `https://inference-api.nousresearch.com/v1` returns HTTP
   200, `finish_reason=tool_calls`, correct tool args — exactly Strix's contract** (D-39-compatible:
   non-thinking model). A 1-h JWT cannot live in CI and the refresh token rotates on use, so CI
   needs the static key: Sanjay creates it at portal.nousresearch.com/api-docs → store in vault /
   repo secret `NOUS_API_KEY` → flip `.github/workflows/security.yml` env to
   `STRIX_LLM: openai/z-ai/glm-5.3`, `LLM_API_BASE: https://inference-api.nousresearch.com/v1`,
   `LLM_API_KEY: ${{ secrets.NOUS_API_KEY }}` (same shape as the CommandCode wiring in `b14c87a`).
   Cost honesty: the last `quick` scan was 85.5M tokens; on Nous "free" means billed to the
   subscription, not unmetered. The first scan that completes WITH findings is the acceptance test
   for the still-unproven exit-2 gate branch.
3. **ATL-218 — owner-gated, only Sanjay:** PyPI account+token; Proton SMTP creds; Cloudflare
   AI-crawl toggle; real Juspay/PhonePe/IDFC samples.
4. **The real-money trial — the only thing that decides the venture:** run ONE real reconciliation
   offline for one real CA/fintech and hand back the output. Nothing has ever met real money. The
   Conjunction rename (ATL-230) is deliberately deferred behind it.

---

## WHAT SESSION 17 (2026-09-11, glm-5.3-flash) DID — the receipts

- **ATL-244 (done): the CF-Connecting-IP question is ANSWERED — no.** Probed from outside AND at the
  origin (header-echo listener on the VPS, tunnel ingress retargeted settleflow→:8097 for ~2 min via
  the CF API, config backed up and restored verbatim, health re-verified). Any request carrying a
  client-supplied CCI is **403'd by the Cloudflare edge (error code 1000)** before cloudflared; the
  origin log saw zero of them. `X-Forwarded-For` IS forwarded with the caller's value as FIRST hop.
  → vuln-0010's HIGH chain does not close from outside **on this topology** (it re-arms if the origin
  is ever exposed directly — keep 127.0.0.1 bind + tunnel-only ingress as a binding invariant, D-41).
  Evidence: `E:/Sanjay Files/StartUp/open source/strix-settleflow-2026-09-11/PROBE-cf-connecting-ip.md`.
- **ATL-246 (done): v0.7.4 deployed.** Version bump release commit `85a0f2f`; `bash scripts/deploy.sh`
  (the run exited into the background and its stdout was swallowed — every claim below was verified
  EXTERNALLY, do not trust a deploy's own output alone). `/health` → `version 0.7.4, runs 173`
  (169 before; delta = canary traffic — runs never dropped, tripwire held). Origin grep: zero
  `x-forwarded-for` in `/opt/settleflow/saas/app.py`; `pick_client_ip` + `cf-connecting-ip` present —
  the live XFF bypass is CLOSED. Backup `/opt/settleflow-backups/20260911-142122.tar.gz`; rollback
  `bash scripts/rollback.sh latest`. Watchdog canary exit 0 silent = pass. CI green on `85a0f2f`
  (Security Scan still red on CommandCode credits only). Also: the SERVER's copy of deploy.sh was
  pre-`7fc77ef` (DB-overwrite bug still armed there) — now replaced.
- Commits this session: `c37fcdc` (probe docs + D-41), `85a0f2f` (release 0.7.4), `f36aae4` (session
  log) + this file's own commit.

---

## WHERE EVERYTHING IS

- **Repo:** `E:/Sanjay Files/StartUp/open source/settleflow` (Windows, git-bash). Branch `master`.
  Public: `AtlasNex/settleflow`.
- **Live:** `https://settleflow.atlasnex.com` — **v0.7.4**, 303+ runs, retention 30 days. The
  remediated build (ATL-242, 12 fixes) is pushed but NOT deployed yet — 0.7.5 is pending.
- **Board:** Multica project **SettleFlow** `1e5c2be2-9967-46b5-8958-4275b73b6ad5`, agent **Hermes PM**
  `a1a9bdd5-f9b8-4505-854a-a4f943a6b17f`. CLI: `multica`.
  ATL-244 done (probe) · ATL-246 done (deploy) · **ATL-242 in_review (all 12 fixes pushed — the
  remediation-ledger comment on the issue lists per-finding evidence; the full comment text also
  lives at `C:/Users/sanja/.multica-tmp/atl242-ledger.md`)** · ATL-234/235/237/238/241 in_review ·
  ATL-218 blocked (owner-gated; includes the Nous Portal API key) · ATL-230 todo (rename, deferred).
- **Review reports (OUTSIDE the repo — abuse write-ups, repo is public):**
  `E:/Sanjay Files/StartUp/open source/settleflow-review-2026-09-11-v2.md` (current) / `-v1.md` (old).
- **Strix findings + the CCI/XFF probe evidence, durable copies (CI artifacts expire):**
  `E:/Sanjay Files/StartUp/open source/strix-settleflow-2026-09-11/` — 20 files incl.
  `vulnerabilities.json`, 12 per-finding `.md`, `PROBE-cf-connecting-ip.md`, `run.json`, SARIF.
- **Deploy:** `bash scripts/deploy.sh` (needs `SETTLEFLOW_HOST` from gitignored
  `scripts/.deploy.env` — present). Rollback: `bash scripts/rollback.sh latest`. Excludes `*.db` and
  `.deploy.env`; asserts the live run count never drops.
- **Watchdog:** Hermes cron `34f4e54a27d8`, every 15 min, runs
  `C:/Users/sanja/AppData/Local/hermes/scripts/settleflow_canary.py`, state at
  `C:/Users/sanja/AppData/Local/hermes/state/settleflow-canary.log`.
- **Scratch (uncommitted, outside the repo):** `C:/Users/sanja/.multica-tmp/` — this session's
  `cf_passthrough_probe.py`, `tunnel_cfg_backup.json` (verbatim live tunnel config), issue-body files.

---

## HOW TO START (the recorded verification way)

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
git log --oneline -3 && git status --short          # expect clean at 6569162+ (or later)
python tests/test_matching.py                        # expect: all 77 checks passed
curl -s https://settleflow.atlasnex.com/health       # expect version 0.7.4, runs >= 303 (until 0.7.5 ships)
gh run list --limit 3                                # CI green; Security Scan red ONLY on model access

# then verify state the recorded way (never a full verify):
hermes verify --skip-start --json                    # expect ok:true; port 8000 clear before+after

# board:
multica issue get ATL-242 --output json | head -40
```

Then: ask for the 0.7.5 deploy go (or act on it if given), bump 0.7.4→0.7.5 in pyproject +
`settleflow/__init__.py` in a release commit, `bash scripts/deploy.sh`, verify externally
(/health shows 0.7.5, runs never drop, origin grep for `pick_client_ip` + `_work_slots` +
`GLOBAL_RATE_LIMIT`), canary, done. If the Nous key exists by then, wire it into `security.yml`
and let the re-scan judge the remediation.

---

## HARD PITFALLS (each of these has cost real time)

1. **NEVER run a full `hermes verify` on this repo.** It hangs and orphans a process on port 8000.
   Use `hermes verify --skip-start` and check port 8000 before and after.
2. **No `pytest` in this repo by design** (D-8). Tests are assert-based: `python tests/test_matching.py`.
3. **Never commit the origin IP** (repo is public). The deploy host comes from `scripts/.deploy.env`
   (gitignored; never commit or quote it). `saas/*.db` must never enter a deploy tarball — the
   tripwire now fails the deploy if the live run count ever drops; don't "simplify" the excludes.
4. **A green CI security run is not "no findings"** — read `strix_runs/*/vulnerabilities.json` (D-38).
   And a red one is not "findings" — CommandCode credits was the last cause. Read `run.json` status.
5. **`scripts/canary.py` run DIRECTLY from the laptop FAILS by design** — it targets
   `127.0.0.1:8093`, which exists only on the VPS. Use the watchdog wrapper
   `C:/Users/sanja/AppData/Local/hermes/scripts/settleflow_canary.py` (public URL; silent + exit 0
   = pass).
6. **A long background command's stdout can be swallowed** (deploy.sh exited 0 with empty output
   after an incoming message moved it to background). Verify state-changing scripts externally:
   `/health` version+runs, origin file greps, backups dir, canary — never the script's own report.
7. **Cloudflare edge-caches `.csv`** — a removed route keeps serving until purged (D-30, no-store).
8. **Strix model contract (D-39):** `LLM_API_BASE` (not `OPENAI_BASE_URL`); never a thinking-mode
   model (`reasoning_content` round-trip 400s); a 403 `error code 1010` is Cloudflare bot-blocking a
   bare client, not an auth failure. Verified-on-Nous substitutes if GLM-5.3 misbehaves:
   `moonshotai/kimi-k3` answered 200 (but showed no tool_call in a one-shot probe — re-verify
   tool-calling before trusting it); `qwen/qwen3.8-max-0902` 400'd.
9. **The Nous portal OAuth refresh token rotates on use** — never refresh it from two processes
   (CI + laptop racing it breaks the laptop's auth). Static `NOUS_API_KEY` is the CI-safe credential.
10. **Real vendor files must never be committed** (named merchant UTRs) — fixtures with NOTICE.md only.
11. **`parse_amount` is strict on purpose** (`'Rs.100'` used to become `0.100`). Do not relax it
    without a specific real file that needs it.
12. **Native Windows Python cannot read MSYS `/e/...` paths** — pass `E:/...` forward-slash paths.
13. **The patch tool mangles quote-escaping on `deploy.sh`/`rollback.sh` remote blocks** — edit those
    via Python with explicit `chr(92)`/`chr(34)`, verify with a stub `ssh`.
14. **Never kill Hermes-owned processes** (agent-stack rule). **Never `rm -rf`** without a verified path.

---

## BINDING RULES (the repo's own constitution — `docs/CONSTRAINTS.md`, `AGENTS.md`)

- **#2 — no invention.** Vendor formats come from primary sources; parsers **raise** rather than
  silently coerce. If a schema has no verified source, it stays unwired (that is why IDFC is empty).
- **#10 — no renaming without a traceable diff plus a `DECISIONS.md` entry.**
- Ponytail lazy-senior mode: smallest working diff, reuse before writing, deletion over addition,
  one runnable check behind any non-trivial logic.
- Honesty taxonomy in every closeout: **DONE vs DEFERRED vs ABORTED vs SKIPPED**, never inflate.
- Currency as **USD (INR) both**.
- Sanjay's working style: answers first, execute in-session (cron is backup, never the doer), build
  only on an explicit go, and challenge completion claims as well as tech rejections.

---

## THE TWO QUESTIONS FOR SANJAY THIS TIME

1. **Deploy go for 0.7.5** (the second half of D-40's authorised sequence — one word).
2. **The Nous Portal API key** (one click, gates the verifying re-scan): create at
   portal.nousresearch.com/api-docs, give it to Hermes — store as repo secret `NOUS_API_KEY`,
   flip `.github/workflows/security.yml` to `openai/z-ai/glm-5.3` +
   `LLM_API_BASE: https://inference-api.nousresearch.com/v1`. Budget ~85M tokens (subscription-
   billed). The first re-scan that COMPLETES is both the ATL-242 verification and the still-
   unproven exit-2 gate branch's acceptance test.
