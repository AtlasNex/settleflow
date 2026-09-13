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

**State change since the last cold-start: 0.7.5 IS DEPLOYED (2026-09-13, session 19) and the
launch sweep shipped with it (UI WCAG-AA, brand assets, docs, packaging).** The
deploy→remediate→deploy sequence is COMPLETE. The Strix Security Scan workflow was **retired**
the same day (D-43): ~85M tokens/scan, no funded provider, permanently-red gate — its value was
already banked (the 12 findings, all fixed with live-gated evidence in 0.7.5). What is left, in
priority order:

1. **ATL-218 — owner-gated, only Sanjay:** PyPI account + API token (name verified FREE; sdist
   + wheel build clean — one `twine upload` away); Proton SMTP creds (the `SETTLEFLOW_SMTP_*`
   env on the box makes the lead-email feature real); Cloudflare AI-crawl toggle; real
   Juspay/PhonePe/IDFC sample files.
2. **The real-money trial — the only thing that decides the venture:** run ONE real
   reconciliation offline for one real CA/fintech and hand back the output. Nothing has ever met
   real money. The Conjunction rename (ATL-230) is deliberately deferred behind it.
3. **If a security gate is ever wanted again:** don't resurrect CI Strix on a free tier. Run one
   funded scan manually at a milestone and keep the exit-code/artifact discipline from the old
   `security.yml` (it is one commit back: `git show 3407a5c:.github/workflows/security.yml`).

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
- **Live:** `https://settleflow.atlasnex.com` — **v0.7.5**, 321+ runs, retention 30 days.
  UI is WCAG 2.2 AA (see `docs/UI-AUDIT.md`); tag `v0.7.5` pushed.
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
git log --oneline -3 && git status --short          # expect clean at 4237e34+ (or later)
python tests/test_matching.py                        # expect: all 77 checks passed
curl -s https://settleflow.atlasnex.com/health       # expect version 0.7.5, runs >= 321
gh run list --limit 3                                # CI green (the Security Scan workflow was retired 2026-09-13, D-43)

# then verify state the recorded way (never a full verify):
hermes verify --skip-start --json                    # expect ok:true; port 8000 clear before+after

# board:
multica issue get ATL-242 --output json | head -40
multica issue get ATL-218 --output json | head -20
```

Then: the board's open items are owner-gated (ATL-218: PyPI token, SMTP creds, CF crawl toggle,
vendor samples) and the real-money trial. There is no in-repo security backlog — if a future scan
is wanted, do it manually funded (see item 3 in MISSION above), not as a CI gate.

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
   *(Legacy: the CI scan was retired 2026-09-13, D-43 — applies again if a manual scan is ever run.)*
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
    via Python with explicit `chr(92)`/`chr(34)`, verify with a stub `ssh`. It also mangled a
    `"\r\n"` literal in a test (session 18/19) — same repair path, byte-exact.
14. **Never kill Hermes-owned processes** (agent-stack rule). **Never `rm -rf`** without a verified path.
15. **Packaging**: `python -m build` fails on sdist metadata in this environment — verify
    packaging with `pip wheel . --no-deps` instead. Under PEP 639 the `License :: OSI Approved`
    classifier is invalid alongside `license = "MIT"` and BREAKS the build; expression only.
16. **pip's `$TEMP` in git-bash is `/tmp`** — native Windows Python cannot see it; always pass an
    explicit `C:/Users/.../Temp/...` path to anything a native tool must read afterwards.

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

## THE QUESTIONS FOR SANJAY THIS TIME

1. **PyPI** (one click + one command): create an account at pypi.org, add an API token scoped to
   the `settleflow` project (the name verified FREE 2026-09-13), then Hermes runs
   `twine upload` — sdist + wheel both build clean today. Until then the README's
   `pip install git+...` is the supported path.
2. **Proton SMTP creds** (`SETTLEFLOW_SMTP_*` on the box) — the lead-email feature is coded,
   tested against a capture server, and inert until real creds exist.
3. **The real-money trial** — the one thing that decides the venture: one real reconciliation
   for one real CA/fintech.
