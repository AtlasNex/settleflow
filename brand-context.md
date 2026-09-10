# SettleFlow — Brand Context

> Source of truth for all public copy (site, README, launch posts, docs).
> Derived from the marketing audit dated 2026-08-30 (score 38/100). Every copy
> decision below traces to a finding in that audit. Update this file first when
> positioning changes; then propagate to `README.md` and the site.

## What SettleFlow is

Open-source (MIT, stdlib-only Python) settlement reconciliation for Indian
merchants: parse a payment-gateway settlement file and a bank statement, match
them, and export Tally / GST / TDS code-1035 (ex-194O) workpapers.

**The moat:** the matching engine is open source. Competitors (Flick AI,
ReconPe, AI Accountant) are closed SaaS — an accountant or security reviewer can
read SettleFlow's matching logic line by line and verify what it does with the
data. No competitor can copy that claim without opening their own engine.

## Audience / ICP

Named in copy — the audit's core finding was that the outcome was described but
the *audience never was*. Three segments, in priority order:

1. **D2C / online merchants in India** reconciling Razorpay payouts against the
   credit that actually landed in their bank account.
2. **CA firms and bookkeepers** doing that reconciliation on behalf of clients —
   they care about Tally/GST/TDS output formats, not "AI".
3. **Freelance accountants / developer-founders** who want to self-host or
   embed the library.

## The top three objections (every page must answer all three)

The audit: *"the top three objections to this page are 'is my bank data safe',
'is this free', 'who made this' — none is currently answered anywhere on the
site."*

1. **Is my bank data safe?** → Files are used for the single reconciliation and
   deleted; the run record (result, exceptions, generated CSVs) is retained
   30 days, then deleted automatically. No account required. The matching code
   is auditable: github.com/AtlasNex/settleflow.
2. **Is this free?** → The library is MIT — free forever, self-host free. The
   hosted service is free while in beta. No commercial tier exists yet; when
   one ships it will be announced here, not hidden in a paywall.
3. **Who made this?** → Built by AtlasNex (Sanjay R.U. Kumar), contact
   sanjay@atlasnex.com. Pre-registration individual operator; legal pages
   in `docs/legal/` are drafts pending review and say so.

## The first question in the category

**"Why not just use Razorpay's own settlement reports?"** — the audit notes this
sentence exists nowhere on the site and must. Answer: gateway reports tell you
what the gateway *says* it sent; they never check against the *bank credit*,
and they don't produce Tally/GST/TDS workpapers. SettleFlow closes that gap:
gateway file ↔ bank statement, with export-ready output.

## Positioning line (approved)

> **For merchants and accountants reconciling Razorpay payouts against bank
> credits.** Upload your settlement file and bank CSV — get matched
> transactions, exception lists, and Tally / GST / TDS-194O workpapers in
> seconds. Open source (MIT). Your files are used for this one reconciliation
> and deleted after. No account needed.

(Verified deletion claim: `saas/app.py` unlinks the uploaded bank file after
processing. Re-verify if retention logic changes — do not ship a claim that
hasn't been checked against the code.)

## Tone

- **Plain engineer-to-engineer honesty.** Concrete nouns (UTR, NEFT credit,
  MDR, TDS 1035, ex-194O) over adjectives. Never "AI-powered" — competitors
  "wave at AI matching"; our differentiation is auditable mechanics.
- **Name what is not built.** Open-source projects earn trust by stating
  limitations (formats supported vs. not, beta status). No "production ready"
  claims.
- **Accountant register is correct and stays.** Tally/GST/TDS vocabulary
  signals "built for my actual work" to segment 2.
- Never disparage competitors; contrast openly (closed SaaS vs. auditable code).

## Do / Don't for public copy

- DO: link the repo from every surface (footer, README top, launch posts).
- DO: keep pricing language to exactly: MIT library · hosted free in beta ·
  self-host free. No invented tiers or rupee figures in public copy.
- DON'T: display any reconciliation output publicly without gating (the audit's
  #1 finding on `/runs`).
- DON'T: name a registered entity or GSTIN — none exists yet; legal pages use
  `[ENTITY/GSTIN to be completed]` placeholders.
- DON'T: claim PyPI availability until it is actually published.

## Verification checklist before shipping any copy claim

1. Data-retention claim → check `saas/` code.
2. Format-support claim → check `docs/SCHEMAS.md`.
3. "Free" claim → check there is no billing gate.
4. Identity claim → contact is sanjay@atlasnex.com; nothing more specific
   until entity registration exists.
