# Cold-start prompt — continue SettleFlow

Paste everything below the line into a fresh session. It is self-contained: it assumes no
memory of the session that produced it.

---

## MISSION

Continue the **SettleFlow** project. Last session took it from a leaking private repo to a public,
CI-gated, secured open-source project and shipped `v0.7.3`. This session has **one product decision
to make first, then four unblocked workstreams**. Read the state below, then act.

**Two open threads, in this order:**

### 1. NAME THE PRODUCT (Sanjay's explicit outstanding request)
He asked to name it, with these constraints, verbatim: *"think of names from space, like how OpenAI
and Anthropic names their products, also we have similar projects Nova and brand new one Kessler."*

- `settleflow` is a documented placeholder; `docs/CONSTRAINTS.md` #10 forbids renaming without a
  traceable diff + a `DECISIONS.md` entry.
- Family context: **Nova** (geospatial engine — "new star"), **Kessler** (a new project — the Kessler
  syndrome, orbital debris). So the naming register is astronomy/orbital, not generic tech.
- The semantics to aim at: reconciliation is **two records being made to agree**. Starter shortlist
  to react to, not a final list —
  - **Conjunction** — the real astronomical term for two bodies appearing aligned. Best semantic fit.
  - **Equinox** — two sides equal; balance. Short, memorable.
  - **Parallax** — the cross-check technique that measures by seeing the same thing twice. Strong
    "verification" story.
  - **Pulsar** — precision and periodic certainty.
  - **Epoch** — the reference point everything is measured from; reconciliation is date-anchored.
  - **Syzygy** — literally "alignment of three bodies". Perfect meaning, unspellable brand; consider it
    for a feature (the three-way match: gateway ↔ bank ↔ order ledger) rather than the product.
  - **Perigee / Alcyone / Vega** — closer/farther, brightest-star options.
- Do the naming properly: check domain availability (do **not** buy anything), check PyPI for a
  collision (the package will be published there), check trademark noise for the shortlist, then
  give Sanjay 3 finalists with the trade-offs and let **him** choose. He names products himself —
  present the case, do not decide.
- A rename means: `pyproject.toml` name + `settleflow/` package dir, `README`, `MASTER-PLAN.md`,
  all `docs/`, the CLI entry point, the live site's copy, the service name on the VPS, and a
  `DECISIONS.md` entry. That is a real diff — plan it, don't start it mid-session.

### 2. Four unblocked workstreams (all previously blocked, now actionable)
1. **PayU parsers** — PayU's settlement **CSV can never exist** (its columns are chosen per merchant
   in a dashboard dialog). Build two JSON parsers from the officially documented APIs:
   `/settlement/range` and `/settlement/transactionDetails`. Complete sample payloads and every field
   are recorded in `docs/RESEARCH-gateway-samples.md` §4a/§4b. Mirror the shape of
   `parse_razorpay_recon` (strict, fails closed).
2. **Cashfree recon parser** — a real (header-only) export proved the file is **two sections**, 14 cols
   then **63 cols** (not 48), split by the marker line `** Settlement Reconciliation Details **`.
   Verbatim headers + per-column sample values in the same research doc §1a/§1b.
3. **Juspay settlement map** — the official 25-column schema page fetches fine (the old "not verifiable
   in raw docs" note was wrong). Money unit is officially unstated but Juspay's *own production parser*
   reads plain rupee decimals, so register it as rupees with that corroboration flagged in the map.
4. **PhonePe's unverified join** — PhonePe is already wired, but the one thing never checked is whether
   the per-settlement aggregate matches a real bank credit. If Sanjay can supply one real PhonePe
   settlement total + the matching bank line, close it; otherwise leave the caveat in the docstring.

**Read `docs/COMPLETION.md` FIRST** — it is the item-by-item DONE / PARTIAL / DEFERRED / BLOCKED record
with the evidence command for every line, plus the findings. Then `docs/RESEARCH-gateway-samples.md`
for the parser specs. Do not re-run the searches recorded there.

## WHERE EVERYTHING IS

- **Repo:** `E:/Sanjay Files/StartUp/open source/settleflow` — branch `master`, remote
  `https://github.com/AtlasNex/settleflow`, **now PUBLIC** (MIT). Last commit `7344c30`.
- **Live:** `https://settleflow.atlasnex.com` — systemd host-run service `settleflow.service` on
  `127.0.0.1:8093`, through the Cloudflare tunnel.
- **Deploy host is NOT in the repo** (deliberately — see D-31): set `SETTLEFLOW_HOST=root@<vps>`, or it
  is already in the gitignored `scripts/.deploy.env`.
- **Deploy:** `bash scripts/deploy.sh` — idempotent, refuses to ship on a red self-check, backs up,
  restarts, then asserts `/health` **and** runs the end-to-end canary on the server **and** checks the
  public URL. Rollback: `bash scripts/rollback.sh latest`.
- **Verify:** `python tests/test_matching.py` (the canonical gate — it prints the check count) ·
  `python tests/test_zero_dependency_core.py` · `python scripts/canary.py --base <url>` ·
  `hermes verify --skip-start --json` (see the pitfall below before trusting the start phase).
- **Board:** Multica project **SettleFlow** `1e5c2be2-9967-46b5-8958-4275b73b6ad5`, agent **Hermes PM**
  `a1a9bdd5-f9b8-4505-854a-a4f943a6b17f`. Phase issues ATL-212…218 (218 = the owner-gated blockers),
  ATL-221 = VPS origin exposure, ATL-224 = last session's recap.
- **Watchdog:** Hermes cron job "SettleFlow canary", every 15 min, `--no-agent`, script
  `settleflow_canary.py` in `~/.hermes/scripts/`, Telegram alert on first failure / every 6th / recovery.

## WHAT WAS SHIPPED LAST SESSION (all verified)

The hosted app had a public unauthenticated `/runs` listing and `/runs/<id>/export/*.csv` downloads,
enumerable by integer id — every uploaded statement's matched UTRs, amounts and exception text were
world-readable. **Fixed:** runs live behind `/r/<run_token>` (~144 bits). Also fixed a real correctness
bug (every upload was written to ONE fixed path, so concurrent reconciliations clobbered each other)
and added upload caps, human error pages, enforced 30-day retention, per-IP rate limiting, hidden
Swagger, real `/about` `/pricing` `/contact` `/privacy` `/terms` pages, `sitemap.xml`/`llms.txt`,
lead capture, CONTRIBUTING/SECURITY/templates, CI, `v0.7.3` release, deploy/rollback/canary tooling.

Beyond the plan, and worth knowing:
- **Cloudflare kept serving the leaked CSV after the route was removed** (`cf-cache-status: HIT`,
  4-hour TTL — `.csv` is in CF's default cacheable list). Purged via API; run responses are now
  `no-store` + `noindex`, asserted by the canary (D-30).
- **The old blocking conclusion was wrong.** Four of five "unobtainable" gateway formats turned out to
  be findable; PhonePe had real committed sample files. D-33 records it. **Never treat an empty search
  as evidence of absence** — re-run it as terms *and* as a phrase, through both `gh search code` and
  `gh api search/code`, and only a failed fetch of a specific candidate URL counts.
- **Never commit the origin host** (D-31), **never cache a run response** (D-30), **a canary must do a
  real reconcile, not a liveness GET** (D-32).

## STILL BLOCKED — on Sanjay, not on code

1. **PyPI release** — needs an account + API token. `pip install git+https://github.com/AtlasNex/settleflow.git`
   works today and is verified in a clean venv. README says "Not on PyPI yet" rather than implying otherwise.
2. **Workpaper email delivery** — needs Proton SMTP creds as `SETTLEFLOW_SMTP_{HOST,PORT,USER,PASS,FROM}`.
   The form stores addresses today and the page says delivery is not wired; **the code never fakes a send.**
3. **Cloudflare managed robots.txt** — the origin file now allows GPTBot/ClaudeBot/PerplexityBot on
   public pages, but the zone's *managed* policy overrides it, so AI crawlers still cannot cite the site.
   Needs the dashboard toggle (Zone → Settings → AI Crawl Control) or a zone API call.
4. **Pricing / money-movement / legal sign-off** — no entity or GSTIN yet (pre-registration, <₹20L).
   The legal pages are **DRAFTS** with explicit placeholders; nothing is charged.
5. **IDFC bank statements** — no real file or official sample exists publicly. Four community parsers
   corroborate the PDF layout but all test against hand-written mock text, and the two CSV claims
   contradict. Stays `None` until a real statement appears. **Do not guess it.**

## HARD PITFALLS (each has cost real time)

- **Windows git runs `core.autocrlf=true`.** Without `.gitattributes` the working tree silently becomes
  CRLF while the repo stores LF; `deploy.sh` ships over tar to Linux, where a CRLF shell script dies with
  `bad interpreter`. `.gitattributes` now pins LF — **and marks `tests/fixtures/**` as `-text`**: those
  are real anonymised statements and a careless `git add --renormalize` will rewrite their bytes.
- **`hermes verify --json` (full) hangs on this repo and leaves an ORPHAN holding port 8000** that
  answers `/health` **200** while the app is broken — so a later run's readiness poll can pass against
  the *stale* process. Check what is actually listening (`netstat -ano` + the PID's CommandLine and
  CreationDate) before trusting any readiness result. Use `--skip-start` for the recorded pass and
  prove start/readiness deliberately.
- **Kill the LISTENER PID, not the bash wrapper** — killing the wrapper leaves the `uv`/python child
  alive and still bound.
- **This VPS is a Proxmox LXC with no AppArmor → `docker compose build` FAILS.** Deploy is host-run
  systemd at `/opt/settleflow` (D-28). The `.venv` there must survive a deploy, which is why `deploy.sh`
  ships an *allowlist* of paths, and why files removed from the app must be named explicitly (tar cannot delete).
- **The CF tunnel is REMOTE-managed** — local `/etc/cloudflared/config.yml` edits are ignored; ingress
  goes through `PUT /accounts/{acct}/cfd_tunnel/{tun}/configurations`. Tunnel
  `9a8936c6-d343-41da-b792-d7e6b5489037`. Port **8093** is settleflow's; 8091 belongs to trade-ui.
- **VPS disk is at ~91%** and will not be expanded. Any new storage needs a retention policy on day one.
- **Windows dev box:** pass native forward-slash paths to native tools; heredocs eat backticks (write a
  `.sh`, run it); `/tmp` is invisible to Windows Python (use `$LOCALAPPDATA/Temp`); piping a check
  through `tail` masks its exit code — run verification **unpiped** or the failure hides.

## BINDING RULES (from the repo's own constitution)

`docs/CONSTRAINTS.md` is the highest authority. Money is `Decimal`, never `float`; paise→rupee only
inside parsers; UTR normalization is alphanumeric+uppercase only; **never fabricate a vendor schema —
raise instead**; deterministic matching; **zero runtime deps in the core** (enforced by CI);
**no test framework** (assert-based self-check is the standard); license stays MIT; never force-push
published history. Plus `AGENTS.md`: one change per commit, read every diff, verify don't assert,
and closeouts separate **DONE / DEFERRED / ABORTED / SKIPPED** — never mark deferred as done.

## HOW TO START

1. Read `docs/COMPLETION.md`, `docs/HANDOVER.md`, `docs/CONSTRAINTS.md`, `docs/RESEARCH-gateway-samples.md`.
2. Confirm the baseline is green **before** changing anything: `python tests/test_matching.py`
   (expect 52) and `python scripts/canary.py --base https://settleflow.atlasnex.com` (expect 5/5).
3. Create a Multica issue for the session's task in the SettleFlow project, assigned to Hermes PM.
4. Then do the naming work (thread 1) and/or pick up a parser workstream (thread 2) — ask Sanjay which
   he wants first if it is not obvious from his message.

**Report format per workstream:** status, the evidence command + its real output, the commit sha, and
the Multica issue id. Anything unverifiable is **PARTIALLY VERIFIED / BLOCKED** with exactly what is
missing — never inflated to done.
