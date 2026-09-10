# Naming shortlist — for Sanjay to choose (2026-09-11, session 15)

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

## If he picks one, the rename blast radius (plan, do not start mid-session)

`pyproject.toml` name and console-script entry point · the `settleflow/` package directory ·
`README.md` · `MASTER-PLAN.md` · all of `docs/` · the CLI entry point and its `--help` text ·
the live site's copy and `/about` page · the `settleflow.service` unit on the VPS and the
`/opt/settleflow` path · the Cloudflare tunnel ingress · `brand-context.md` ·
`tests/test_matching.py`'s imports · a `DECISIONS.md` entry recording the choice and the
`settleflow` → `<name>` git history boundary. Roughly a one-session job, and the VPS path change
is the part that needs the deploy script's allowlist touched rather than a plain `deploy.sh` run.
