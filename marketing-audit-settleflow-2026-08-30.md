# Marketing Audit — settleflow.atlasnex.com
2026-08-30 · Overall score: **38/100** (100% of dimensions inspected) · Basis: live site (`/`, `/runs`, `/docs`, robots.txt, openapi.json, 12 probed paths), repo README, competitor search

> Scores are heuristics from marketing judgement against the audit-rubric bands — not measured performance. No `brand-context.md` existed, so findings are un-contextualised; ICP and pricing judgements assume the obvious one (Indian merchants/accountants reconciling Razorpay → bank).

## The one thing

This is an engineering deployment, not a product page. Every judgement a stranger needs before uploading a bank statement — who built this, what happens to my data, what it costs, why not just use Razorpay's own reports — is absent, and the one page that *does* exist (`/runs`) publicly displays raw settlement output with UTRs and amounts. The result is a funnel that can't convert even when it works: a merchant who completes a reconciliation leaves no email, no account, no next step, so the only outcome the site produces is a free CSV and a stranger who will never find you again.

## Scorecard

| Dimension | Score | Weight | Weighted | Verdict |
|---|---|---|---|---|
| Messaging & positioning | 52 | 25% | 13.0 | Specific outcome, unnamed audience; the open-source moat is invisible |
| Conversion | 45 | 20% | 9.0 | One clear CTA, but zero objection handling on a data-sensitive upload |
| Search & discoverability | 30 | 20% | 6.0 | Good title tag; no meta desc, no sitemap, AI crawlers blocked |
| Competitive position | 35 | 15% | 5.25 | Four funded competitors publish comparison content; you publish nothing |
| Trust & credibility | 25 | 10% | 2.5 | No privacy/terms/contact/team; `/runs` leaks transaction-shaped data |
| Growth & retention | 20 | 10% | 2.0 | No pricing, no capture, no upgrade path, single entry point |
| **Total** | | 100% | **38** | Actively leaking band (40-59 bottom edge) |

## Fix these first

**1. Gate or scrub `/runs` — trust and legal, do today.**
A public, unauthenticated listing of reconciliation results (settlement IDs, bank UTRs, amounts, export CSVs downloadable by anyone at `/runs/4/export/tally.csv`) is the single worst signal on the site. Even if all four rows are test fixtures, a merchant's accountant who finds it will not upload a real statement. Effort: S. Confidence: high.
→ Make runs session-scoped (cookie/localStorage id), or clear the demo rows and add a "demo data" badge on each.

**2. Replace the sub-head with copy that names the audience and answers the fear.**
Current: *"Reconcile a payment-gateway settlement file against a bank statement, then export Tally / GST / TDS-1035 workpapers."* — accurate, but written by the builder for the builder.
Replacement (artifact, ready to paste):

> **For merchants and accountants reconciling Razorpay payouts against bank credits.**
> Upload your settlement file and bank CSV — get matched transactions, exception lists, and Tally / GST / TDS-194O workpapers in seconds.
> Open source (MIT). Your files are used for this one reconciliation and deleted after. No account needed.

The third line is the objection-handler: the top three objections to this page are "is my bank data safe", "is this free", "who made this" — none is currently answered anywhere on the site. (Verify the deletion claim against `saas/` code before shipping; if files persist, say how long instead. Do not ship a claim you haven't checked.)

**3. Add a 4-line footer that makes the product real.**
Links: About (one paragraph: built by AtlasNex, open source at github.com/… — link the repo), Privacy, Contact (mailto), Pricing ("Hosted: free while in beta · Self-host: MIT"). Four links, twenty minutes, moves Trust out of the "absent" band. The GitHub link is also your only differentiation no competitor can copy — Flick AI, ReconPe and AI Accountant are all closed SaaS; "open source, audit the matching engine yourself" is the switching argument, and it currently appears nowhere on the site. Effort: S. Confidence: high.

**4. Capture the lead at the moment of value.**
The export-download click is the highest-intent moment on the site. Put one field on the results page: *"Email me this workpaper pack (Tally + GST + TDS) — and get an alert when new bank formats (Paytm, PhonePe, CRED) ship."* Zero → one email pipeline. Everything else in growth is downstream of this. Effort: M. Confidence: med (adds friction to a free tool; keep it optional, download still works).

**5. Search/GEO basics — one file and two meta tags.**
Add meta description (the replacement sub-head above works verbatim), a `sitemap.xml` with the two pages, and an `llms.txt` stating what SettleFlow is. Note the tradeoff you own: your Cloudflare-managed robots.txt currently disallows GPTBot, ClaudeBot and Perplexity-adjacent crawlers site-wide (`ai-train=no, use=reference`). That's a defensible policy for the app, but it also means ChatGPT can never cite you when a merchant asks "how do I reconcile Razorpay settlements" — the exact query your buyer types. Decide: block on `/runs`+upload, allow on a future public docs/blog surface. Effort: S. Confidence: high for the basics; the crawler policy is your call, not a fix.

## What's already working

- **The title tag is genuinely good**: "SettleFlow — UPI settlement reconciliation" — 43 chars, brand-first, exact-match keyword. Better than most funded competitors' homepages.
- **The core offer is real and specific.** Tally/GST/TDS-1035 export and multi-bank CSV support (HDFC/SBI/ICICI/Axis/Kotak/PNB/DBS, verified schemas in `docs/SCHEMAS.md`) is a concrete, differentiated capability — competitors' marketing pages mostly wave at "AI matching." The product story is stronger than the product page.
- **One clear primary CTA.** A single "Reconcile" button, no carousel of competing actions. The conversion problem is everything *around* the CTA, not the CTA hierarchy.

## Full findings

**1. Messaging (52).** Outcome is named with real specificity (Tally/GST/TDS-1035 — accountant vocabulary, correct register); audience is never named. "SettleFlow" alone as H1 forces the sub-head to carry everything. Jargon load is fine for the buyer but the copy never signals *whose* problem: a D2C merchant, a CA firm doing reconciliation for clients, and a freelance accountant have different fears and the page addresses none. The repo README says "Working name" — the site doesn't, and neither mentions open-source/MIT. Cap check: headline names the outcome, so the 60-cap doesn't apply; 52 sits at the top of "actively leaking" because the raw material for 75+ exists and is simply unwritten.

**2. Conversion (45).** Three free-text column-name inputs (UTR/amount/date) are expert-mode defaults that will lose a non-technical merchant mid-form — auto-detect or hide behind "advanced." No answer to "what happens to my bank statement" anywhere near the upload control. No post-run path except a link to a public runs table. No risk reversal (no-card, no-account is actually your strength — unstated).

**3. Search (30).** Title good; meta description absent; H1 is brand-only; no headings hierarchy in body (labels do the styling); no internal linking beyond `/runs`; no sitemap (404); no structured data; AI crawlers disallowed → citability ≈ zero. Intent match is honest (transactional page for a transactional query) — that's why it's 30, not 15.

**4. Competitive (35).** Category is clear by inference but never claimed. Flick AI, ReconPe, AI Accountant, Terra Insight all publish comparison/guide content targeting "bank reconciliation software India" — you have no answer to "why not Razorpay's own settlement reports?" (the real first question: because gateway reports don't check against the *bank* credit and don't produce Tally/GST workpapers — that sentence exists nowhere on your site). No switching story, no named alternatives. Not capped at 55 (you don't say what they all say — you say almost nothing).

**5. Trust (25).** No privacy, terms, contact, team, or security page (all 404). `/docs` is a default FastAPI Swagger UI with a tiangolo favicon — developer-facing, not buyer-facing. `/runs` public listing as detailed above. Design is clean-but-default system-ui — not embarrassing, adds nothing.

**6. Growth (20).** No pricing legibility (free? beta? who knows), homepage-only acquisition surface, no upgrade path visible, no lifecycle hooks. `funding.json` in the repo hints at an open-source sustainability model that the site never mentions.

## Appendix: lower-priority items

- Add `og:` tags before any LinkedIn/X launch post (the social module will want them).
- The "Settlement kind" select offers only Razorpay options while the README lists PayU-adjacent bank formats — label the gateway support matrix honestly on the page.
- `/health` exposed publicly (harmless, but trim).
- Consider a one-page `/how-it-works` with the two-pass matching explanation — it's the best trust artifact an open-source matcher can ship, and it doubles as GEO content.
- PDF conversion of this report for sharing: ask.

## What I couldn't determine

- **Traffic and conversion data** — no analytics detected on the page; all conversion findings are structural, not measured.
- **Whether `/runs` rows are test fixtures or real merchant data** — values look like fixtures (`BANKUTR999`), but I did not query the database. If any real statement was ever reconciled on this deployment, fix #1 escalates from "this week" to "today."
- **File retention behavior** — now verified: `saas/app.py:126` unlinks the uploaded bank file after processing, so the "deleted after" line in fix #2 is safe to ship (re-check if retention logic ever changes).
- **Pricing intent** — no signal anywhere; growth findings assume you *want* a commercial path. If SettleFlow is deliberately a free open-source utility for GitHub stars/funnel-to-AtlasNex, the growth score should be re-read as N/A and the messaging should say so loudly instead of silently.
