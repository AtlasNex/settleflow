# Naming — CHOSEN: **Conjunction** (2026-09-11)

**Sanjay chose `Conjunction` on 2026-09-11.** `settleflow` is now a deprecated placeholder; the
rename is planned below and **not yet executed** (the VPS path change is the risky step and it
needs a deliberate go, not a drift).

The rest of this file is the evidence the choice was made on. `docs/CONSTRAINTS.md` #10 still
applies: the rename lands as a traceable diff plus a `DECISIONS.md` entry (D-37 records the choice).

## Why this name

The astronomical term for two bodies appearing aligned — which is literally the product's job:
a gateway settlement and a bank credit, made to agree. It is the only candidate that is
simultaneously the correct word, **free on PyPI**, and unclaimed by a notable company.

**The cost, stated once and not relitigated:** it is a common English word, so it will be hard to
rank for and awkward to say in conversation ("did you run the conjunction?"). The mitigations are a
compound domain plus always pairing the word with its category — *Conjunction, for UPI settlement
reconciliation* — the way Stripe pairs with payments.

---

# Original shortlist evidence (kept: this is what the decision rested on)

`settleflow` is the documented placeholder. `docs/CONSTRAINTS.md` #10 forbids renaming without a
traceable diff plus a `DECISIONS.md` entry, and Sanjay asked for the name himself:

> *"think of names from space, like how OpenAI and Anthropic names their products, also we have
> similar projects Nova and brand new one Kessler."*

So the register is astronomy/orbital (Nova = new star, Kessler = orbital debris), and the semantic
target is **two records being made to agree**. Nothing here is decided and nothing was bought.

## What was actually checked (and what was not)

| Check | Method | Trustworthiness |
|---|---|---|
| PyPI package name | `https://pypi.org/pypi/<name>/json` → 200 taken / 404 free | direct registry answer |
| Domain registration | RDAP (`rdap.org/domain/<d>`), controls run first (`google.com`, `web.dev`, `zerodha.in` all correctly reported registered) | **registered ≠ unavailable to buy**, and **not-found ≠ yours**. `.io` had to be discarded: `github.io` returned 404, so `.io` answers from this endpoint are meaningless (all nine candidates falsely looked "free") |
| Brand collision | general web search per candidate | **weak evidence.** No registry trademark search was run. A real clearance search (IP India, classes 9 and 42; or TMview) is a legal step and is still open |

## The evidence

Single dictionary words are gone as exact-match .com/.in for every candidate, so a domain will be
a compound or a non-.com TLD. Compound `.com` availability (RDAP, 404 = likely free):

| Candidate | PyPI | .com | .in | free compound `.com` |
|---|---|---|---|---|
| **Conjunction** | **free** | taken | taken | `getconjunction.com`, `conjunctionapp.com`, `tryconjunction.com`, `conjunctionrecon.com` |
| **Parallax** | taken | taken | taken | `parallaxrecon.com` |
| **Epoch** | taken | taken | taken | `epochrecon.com` |
| Pulsar | taken | taken | taken | — |
| Equinox | taken | taken | taken | `equinoxrecon.com` |
| Syzygy | taken | taken | taken | `syzygyrecon.com` |
| Libration | **free** | taken | taken | not checked |
| Perigee | taken | taken | taken | not checked |
| Alcyone / Vega | taken | taken | taken | not checked |

## Three finalists

### 1. Conjunction — best semantic fit, and the only clean-technical option
The real astronomical term for two bodies appearing aligned. That is literally the product's job:
gateway settlement and bank credit, made to agree. Free on PyPI, four free compound `.com` forms,
and general web search surfaced no notable commercial user of the word.

**Cost:** 11 letters, and it is a common English word, so it is generic in conversation
("did you run the conjunction?") and awkward to shorten. Exact-match `.com`/`.in` are taken.

### 2. Parallax — strongest "verification" story, most crowded word
Measuring by viewing the same thing twice from two positions is exactly what a reconciler does, and
it reads technical-serious. **Cost:** the word is used widely (Parallax Inc. in electronics, and
many products besides), the PyPI name is taken, and only a `recon`-suffixed `.com` checked free.

### 3. Epoch — best mouth-feel, most brand noise
Five letters, hard to misspell, and reconciliation is date-anchored, which is what an epoch is. It
also sits beside Nova and Kessler without explaining itself. **Cost:** heavily used — including
large media and SaaS brands — PyPI taken, and only `epochrecon.com` checked free.

### Dark horse, if he wants stranger
**Libration** — the apparent wobble of the same body seen twice, i.e. cross-checking by looking
again. Free on PyPI. **Cost:** obscure, nine letters, and nobody spells it on the first try.

### I would drop these three
- **Equinox** — Equinox Group already operates a fan-out of fitness/media brands, and the PyPI name
  is a well-known JAX library. Too much noise in more than one register.
- **Pulsar** — Apache Pulsar owns the developer mindshare, and Pulsar is also a watch brand.
- **Syzygy** — SYZYGY AG is a company listed on the Frankfurt exchange, and the word is
  unspellable. Keep it for the three-way match feature (gateway ↔ bank ↔ order ledger), as the
  earlier brief suggested.

**My one-line recommendation:** Conjunction, because it is the only candidate that is
simultaneously the correct word, free on PyPI, and unclaimed by a notable company — and the
`*.com` penalty is identical for every single-word option.

## The rename to `Conjunction` — ordered plan (NOT executed; needs Sanjay's go)

Sequenced so that the repo is renamed and verified BEFORE anything on the live host moves. Steps 1-3
are safe and reversible; step 4 is the one that can take the site down.

**Phase 0 — before touching the repo (facts that expire)**
1. Re-check the four compound `.com` options at the registrar (RDAP said free on 2026-09-11:
   `getconjunction.com`, `conjunctionapp.com`, `tryconjunction.com`, `conjunctionrecon.com`).
   Registration is a purchase — Sanjay's call, not mine. Note `conjunction.com` and `conjunction.in`
   are registered and are not for the taking.
2. Reserve `conjunction` on PyPI (it is free today; PyPI names are first-come).

**Phase 1 — inside the repo (one commit per step, self-check green between each)**
3. Rename the package directory `settleflow/` → `conjunction/` and update `tests/test_matching.py`'s
   `sys.path` + imports. Verify: `python tests/test_matching.py` → all checks pass (the
   count is printed; it was 74 when this plan was written).
4. `pyproject.toml`: `name`, the console-script entry point, and the wheel/pyproject metadata.
   Verify: build the wheel and install it in a clean venv, then run the CLI's `--help`.
5. Prose sweep: `README.md`, `MASTER-PLAN.md`, `brand-context.md`, `docs/**`, `AGENTS.md`,
   `CONTRIBUTING.md`, `SECURITY.md`, `sitemap.xml`/`llms.txt` in `saas/`, the page templates and
   copy. Verify: `grep -rn settleflow` returns only the intentional historical references
   (the `DECISIONS.md` boundary entry below, and the git history).
6. `DECISIONS.md` D-38: record the rename and mark the `settleflow` → `conjunction` boundary in git
   history, so "settleflow" in old commits is explained rather than confusing.
7. Push both repos' rename, wait for CI green on the pushed head (the repo is public and CI is the
   gate).

**Phase 2 — the live host (the risky half; do it deliberately, with the rollback ready)**
8. `saas/` copy change → `bash scripts/deploy.sh` (it refuses to ship on a red self-check, backs up,
   restarts, then asserts `/health`, runs the end-to-end canary, and checks the public URL).
   Verify: canary 5/5 on `conjunction.atlasnex.com` (or whichever hostname is decided) **and** on the
   existing one while it still answers.
9. Only then the VPS moves: the `settleflow.service` unit and `/opt/settleflow` → `/opt/conjunction`,
   which means **the deploy script's path allowlist changes too** — a plain `deploy.sh` run will not
   do it, because the script ships an allowlist of paths and cannot delete files by itself. Rollback
   for this step: the previous release is on disk, `bash scripts/rollback.sh latest`.
10. The Cloudflare tunnel ingress is remote-managed (`PUT /accounts/{acct}/cfd_tunnel/{tun}/configurations`,
    tunnel `9a8936c6-d343-41da-b792-d7e6b5489037`); a local `config.yml` edit is ignored. Change the
    hostname and/or the `:8093` service mapping there, then re-run the canary.

**Not to be forgotten (verified 2026-09-11, not assumed):** the Hermes watchdog cron job
`34f4e54a27d8` ("SettleFlow canary", `*/15 * * * *`, `--no-agent`) runs
`C:/Users/sanja/AppData/Local/hermes/scripts/settleflow_canary.py`, whose public base is
`os.environ.get("SETTLEFLOW_PUBLIC_BASE", "https://settleflow.atlasnex.com")` — a default with an
env override, so the rename must change **either** that default **or** set the env var, and must
also carry the `CANARY` path it shells out to. Leave it and the alerting keeps polling the old
hostname: green right up until the old hostname stops answering, which is the one day it matters.
Its state/log live in `C:/Users/sanja/AppData/Local/hermes/state/settleflow-canary{,-state}.json`.
