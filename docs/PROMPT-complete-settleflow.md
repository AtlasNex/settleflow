# Prompt — Complete SettleFlow end-to-end (100%)

Paste everything below the line into a fresh session.

---

## MISSION

Take the SettleFlow repo from "working engineering deployment" to a **launchable, safe, publicly-installable open-source product**, end to end, in this session. 100% of Phase 1–6 done and verified, or explicitly reported as blocked.

**Repo:** `E:/Sanjay Files/StartUp/open source/settleflow` (branch `master`, remote `https://github.com/AtlasNex/settleflow`)
**Live:** `https://settleflow.atlasnex.com` (systemd host-run service `settleflow.service`, `127.0.0.1:8093`, Cloudflare Tunnel)
**VPS:** `<deploy-host>` (not committed — see `scripts/deploy.sh`; the origin address is deliberately absent from this public repo) — deploy target is `/opt/settleflow`

**Established baseline, already verified — do not re-litigate:**
- `python tests/test_matching.py` → **all 42 checks passed** (green; that's your regression gate).
- Version `0.7.3`; core library is **stdlib-only**; extras are `[saas]`, `[pdf]`, `[ocr]`.
- Live `/health` → `{"status":"ok","version":"0.7.3"}`.
- Repo has **no CI workflows** (`.github/` holds only `FUNDING.yml`).
- Repo is **PRIVATE** on GitHub while `README.md`, `MASTER-PLAN.md` and the live site all claim "open source, MIT".

**Do not touch NexTrade or Nova.** NexTrade is on hold (no capital) — out of scope, no exceptions.

---

## READ FIRST (binding, in this order)

1. `docs/CONSTRAINTS.md` — never-violate rules. Highest authority in this repo.
2. `AGENTS.md` — working rules (one change per request, read every diff, verify don't assert).
3. `docs/HANDOVER.md` — current state and gotchas.
4. `docs/ARCHITECTURE.md` + `docs/FLOW.md` — trace the real flow before you change it.
5. `docs/marketing-audit-2026-08-30.md` — the 38/100 audit. Its fix list is your Phase 3 spec.

Non-negotiable constraints you must not break: money is `Decimal` never `float`; paise→rupee only inside parsers; UTR normalization is alphanumeric+uppercase only; **never fabricate a vendor schema** (raise instead); deterministic matching; **zero runtime deps in the core**; **no test framework** (assert-based self-check is the standard); license stays MIT; never force-push or rewrite published history.

---

## DEFINITION OF DONE — "100%" means every line below, with pasted evidence

**Phase 1 — Data safety (blocker; nothing else matters until this is closed)**
1. No unauthenticated data surface. `/runs`, `/runs/{id}/exceptions` and all three export endpoints must be unreachable without the owner's credential. Verified by: `curl` returns 404/403 without it and 200 with it.
   - Recommended minimal design (no login, no user model, stays in the repo's spirit): on `/reconcile`, mint a random `run_token`; the caller's results URL is `/r/<run_token>`; `/r/<token>/export/*.csv` is the only export path. Unauthenticated `/runs` listing either disappears or shows only the caller's own runs. Do not build accounts/OAuth — that is a different product.
2. **Fix the shared-upload race**: `saas/app.py` writes every bank upload to the single fixed path `BASE/upload_bank.csv`. Two concurrent requests clobber each other. Prove the fix with a parallel two-request test that yields two distinct run ids and two correct results.
3. **Bound the inputs**: max upload size enforced server-side (reject with a clear 413/400), reject unexpected content types/extensions, and confirm a garbage/oversized payload fails cleanly rather than 500-ing.
4. **Make retention true**: choose and implement one — delete run rows + exports after N days (a cleanup on startup and/or a cron), or state the real retention period in the UI. The current code persists every run's matched UTRs, amounts and exception text in sqlite indefinitely. **Do not ship any copy claiming "files deleted after" unless the code provably does it** — the audit explicitly warns about this.
5. `/runs/{id}/exceptions` currently returns raw exception text as plaintext — treat it as a data surface, not a debug endpoint.

**Phase 2 — Product completeness (the app itself)**
6. Results page that a non-technical merchant can read: matched / unmatched totals, exception list, and working download buttons. No raw JSON as the only output.
7. Replace the expert-mode-only form: auto-detect the bank CSV columns where possible, and tuck the three manual column inputs behind an "advanced" toggle.
8. `/docs` — the default FastAPI Swagger UI with a tiangolo favicon is developer-facing on a buyer-facing site. Hide it in production or replace it with a plain-language API page.
9. Errors surface as human messages (upload too big, wrong format, unparseable row) — never a stack trace or a blank page.
10. Self-check grows for every new behavior and **stays green**.

**Phase 3 — Public surface (target: fix all six audit dimensions)**
11. Pages that exist and are linked from the footer: **About** (one paragraph, built by AtlasNex, link the repo), **Privacy**, **Terms**, **Contact** (working mailto), **Pricing**.
12. Use the audit's ready-to-paste sub-head verbatim as the starting copy (it names the audience and answers the data-safety fear).
13. One-field **lead capture on the results page** — "email me this workpaper pack" — with the download still working if they decline. Prove it writes a row.
14. SEO/GEO basics, each verified with `curl`: meta description, `sitemap.xml` (200), `llms.txt`, `og:` tags, real heading hierarchy, no orphan pages.
15. Decide and implement the crawler policy. Today Cloudflare's managed robots.txt disallows GPTBot/ClaudeBot site-wide, so ChatGPT can never cite the page for the exact query your buyer types. Recommended: block on `/runs` and upload paths, **allow** on the public docs/landing surface.
16. Add `brand-context.md` first (audience, ICP, objection-handling, tone), then write copy from it. The audit scored without one and said so.

**Phase 4 — Make "open source" true**
17. `LICENSE` present and correct (MIT) — and then **ask Sanjay before flipping the repo to public** (see Founder Gates).
18. CI workflow that runs `python tests/test_matching.py` on push and PR, green in the Actions tab. Also wire the Strix security scan used elsewhere in AtlasNex if it applies.
19. Add `CONTRIBUTING.md`, `SECURITY.md`, issue/PR templates, and a `NOTICE` that makes the existing fixture provenance (`tests/fixtures/*/NOTICE.md`) unmissable.
20. First tagged release `v1.0.0` (or the honest next version) with release notes, and a **real install path**: `pip install` from PyPI (TestPyPI first is acceptable, but end on a real public install that a stranger can run). Publish only with approval.
21. README becomes a front door: install line, 10-line usage, badges, links, and a truthful status section.

**Phase 5 — Ops (so this stops being manual)**
22. One idempotent deploy command/script that ships the repo to `/opt/settleflow` and restarts the systemd unit, with a **post-deploy health assertion** that fails loudly. Today every deploy is hand-typed.
23. Monitoring: an uptime-kuma monitor on `/health` **plus a synthetic canary that performs a real reconcile round-trip** (a health check that only proves the process is up is how a broken app stays "healthy" for weeks). Alert route to Telegram.
24. Exercise the rollback once (`docs/ROLLBACK.md`) and record what actually happened — a rollback path you have never run is a guess.

**Phase 6 — Closeout**
25. `docs/COMPLETION.md`: one table, every item above, marked **DONE / DEFERRED / ABORTED / SKIPPED** with the exact command and output as evidence. Never mark deferred as done.
26. Update `docs/HANDOVER.md` (state + next step), append to `logs/SESSION-LOG.md`, add `docs/DECISIONS.md` entries for every judgment call (with model + date), and commit in small traceable commits — one change per request.
27. Multica board: create one issue per phase in the **SettleFlow** project (id `1e5c2be2-9967-46b5-8958-4275b73b6ad5`), assign the **Hermes PM** agent (`a1a9bdd5-f9b8-4505-854a-a4f943a6b17f`), comment at milestones, `done` only when verified. Verify every status change with `multica issue get`.

---

## FOUNDER GATES — STOP AND ASK. Do not invent these.

Ask Sanjay these **up front, in one batch**, so the session isn't blocked mid-flight. Everything in Phases 1–5 that does not depend on an answer proceeds immediately.

1. **Name.** `settleflow` is a documented working placeholder and `docs/CONSTRAINTS.md` #10 forbids renaming without a decision. Final name now, or ship as-is?
2. **Publish the repo public?** It cannot be "open source" while private — that's the product's entire differentiation. Yes/no, and if no, every marketing claim must change instead.
3. **Pricing.** Free tier? Paid? Price points? Who pays (merchant vs CA firm)? The plan currently floats ₹4–7k/mo through CAs plus a commercial embed licence. This is a decision, not research.
4. **Money movement.** Merchant-of-record (Gumroad-style) vs own gateway. **This is GSTIN-gated** and must be answered before any payment integration is built.
5. **Legal sign-off.** Privacy policy + terms + refund policy for an India SaaS handling bank statements. Do you have an entity/GSTIN now, or is this pre-registration (<₹20L)? Written sign-off on the policy text before it goes live.
6. **Lead email destination** + sending mechanism (mailbox + SMTP/Resend/Composio).
7. **Real sample files — the only hard blocker on parser coverage.** Cashfree / PhonePe / Juspay / PayU settlement+recon exports, and your real SBI statement PDF(s). `docs/SCHEMAS.md` has the captured schemas but **`docs/CONSTRAINTS.md` #2 forbids building a parser against a fabricated schema**, and D-7/D-24 confirmed these exports are merchant-private. Without a sample these stay DEFERRED — that is the honest outcome, not a failure.
8. **Crawler policy** (citation vs training) if you want to override the recommendation in Phase 3.15.

---

## HARD-WON PITFALLS (each of these has already cost time once)

- **This VPS is a Proxmox LXC with no AppArmor → `docker compose build` FAILS.** `settleflow` runs host-run under systemd at `/opt/settleflow` (`D-28`). Deploy by shipping files + `systemctl restart settleflow`, never by image build.
- **The Cloudflare tunnel is REMOTE-managed.** A local `/etc/cloudflared/config.yml` edit is IGNORED. Ingress changes must go through `PUT /accounts/{acct}/cfd_tunnel/{tun}/configurations`. Tunnel id `9a8936c6-d343-41da-b792-d7e6b5489037`. Current ingress: atlasnex.com→8090, app→8080, nova→8000, trade-ui→8091, **settleflow→8093**, s1→8094.
- **Port 8091 belongs to trade-ui.** settleflow owns **8093**. Bind `127.0.0.1` only; the tunnel reaches it locally. Never expose the port directly.
- **VPS disk is at 91%.** The box will not be expanded. Any storage you add (run history, uploads, exports) needs a retention policy from day one, not a note.
- **Windows dev box (git-bash):** pass native forward-slash paths (`E:/...`) to native tools; heredocs eat backticks (write a `.sh` and run it); `/tmp` is invisible to Windows Python (use `$LOCALAPPDATA/Temp`); big inline shell commands hit the blocklist.
- **Do not add runtime dependencies to the core** and do not introduce pytest. If you believe you need either, write a `DECISIONS.md` entry and ask first.
- **`run_exceptions` and the export endpoints are plaintext, unauthenticated, and enumerate by integer id** — trivially scrapeable. That is Phase 1's whole reason for existing.

---

## EXECUTION SHAPE

- Work in **phases, in order, one commit per change**, running `python tests/test_matching.py` before every commit. Phase 1 is a hard gate: do not polish marketing while real merchant data can leak.
- **Two parallel tracks at most, on disjoint files** — (a) app/security code, (b) public surface + docs + CI/PyPI. Both editing `README.md` and `saas/app.py` means merge pain on a 3,200-line repo; parallelise by *file ownership*, not by vibes. Keep deploy and every live verification single-threaded and in one place.
- Every "done" claim needs the command and its real output pasted. If something cannot be verified, mark it **PARTIALLY VERIFIED / BLOCKED** and name exactly what's missing. Never narrate past a failure or a contradiction in your own tool output.
- If you find the audit or any doc contradicting the live system, **the live system wins** — and fix the doc.

---

## FINAL REPORT FORMAT

For each phase: status (DONE / DEFERRED / ABORTED / SKIPPED), the evidence command + output, the commit sha, and the Multica issue id. Then a one-screen summary: what a stranger can now do with SettleFlow that they could not do before, and the single biggest remaining risk.
