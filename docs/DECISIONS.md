# Decisions

The "why" behind every choice, not just the "what". Read before you reverse a
decision. Each entry is version-pinned: who made the call and when.

## Version pinning (context)

| Role | Model | What it did |
|---|---|---|
| Orchestration + build | deepseek-v4-pro | decided the project, wrote all code and docs, made the commits |
| Research subagents | deepseek-v4-flash | ran the market/gap deep-dives (3 rounds) that produced the evidence |

The research that led here ran 2026-08-15 in three rounds: broad landscape -> two-path
shortlist -> deep-dive head-to-head. The deep-dive *killed* three of four candidate
wedges (a Postgres job queue was already owned by `pgqueuer`; GST was already owned by
Frappe's India Compliance; SEBI algo compliance had the wrong buyer). UPI reconciliation
survived because the OSS component layer is genuinely un-owned.

## Decisions

### D-1: Build UPI/NPCI reconciliation (not geo, not crypto, not AI tooling)
- **Why:** the only wedge where (a) the gap is real and un-owned, (b) there are paying
  buyers (fintechs, CAs, D2C sellers), (c) it maps to the exact stack (FastAPI/Postgres/
  Python), (d) low regulatory risk (no license, no filing liability).
- **Rejected:** geo-agent core (Nova's vectorized zoning was broken + `1acre.in` already
  ships parcel zoning); crypto OSS (usage != income, 30% tax kills domestic); MCP
  security (Snyk/Cisco/Invariant already ship); a Postgres job queue (`pgqueuer` owns it).
- **Model:** deepseek-v4-pro + deepseek-v4-flash research. **Date:** 2026-08-15.

### D-2: Open-core + thin SaaS, not a platform
- **Why:** the enterprise recon *platform* layer is crowded (Gini, UnPay, ReconPe,
  Cointab, Paxcom). The un-owned thing is the *component layer* (parsers + matching).
  OSS core = trust + distribution; the paid layer is a thin SaaS + consulting.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-3: `Decimal` for money, never `float`
- **Why:** reconciliation math must be exact; `float` produces rounding drift
  (₹0.1 + ₹0.2 != ₹0.3). Non-negotiable.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-4: Two-pass matching (exact UTR -> amount+date fallback)
- **Why:** the real Razorpay flow uses `settlement_id` as the batch key, and the bank
  statement's UTR is the *correspondent bank's* UTR, not the gateway's `settlement_utr`.
  So UTR match alone under-matches; the (amount, date) fallback is what actually pairs
  most batches.
- **Source:** Razorpay `Fetch All Settlements` docs + Terra Insight reconciliation guide.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-5: `settlement_id` rides through as `Txn.ref`
- **Why:** `match_settlements` converts `Settlement` -> `Txn` with `ref=settlement_id`,
  so a matched/unmatched result still tells you *which batch* without a separate mapping.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-6: paise -> rupee conversion lives only in the parser
- **Why:** Razorpay returns money in the smallest currency unit (paise). Keeping the
  model in rupees and converting at the parser boundary means the matcher never has to
  know about paise.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-7: Generic CSV loader with explicit column mapping (no vendor-specific classes)
- **Why:** the Razorpay CSV column names were not verifiable in raw docs (JS-rendered),
  and fabricating a schema is exactly the failure mode that broke Nova's zoning layer
  (20 fabricated `(GUESS)` legend rows). So `load_csv` takes column names as explicit
  arguments; the vendor mapping is data, filled from a real sample, never guessed.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-8: Assert-based self-check, no pytest/tox
- **Why:** ponytail rule: non-trivial logic leaves one runnable check, no frameworks.
  `python tests/test_matching.py` is the whole suite. Add pytest only if Sanjay asks.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-9: Working name `settleflow`
- **Why:** Sanjay names products at the end. `settleflow` is a placeholder (settlement +
  flow). Rename is a known, cheap, traceable diff (see D-10).
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-10: MIT license
- **Why:** maximally permissive for an open-core strategy (OSS core MIT, paid SaaS on
  top). Copyright holder = Sanjay R.U. Kumar.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-11: Private GitHub repo until complete
- **Why:** Sanjay wants it private until the project is done, then public. Avoids a
  half-finished repo being the first public impression.
- **Model:** deepseek-v4-pro (per Sanjay's instruction). **Date:** 2026-08-15.

### D-12: Relocate under `E:/Sanjay Files/StartUp/open source/<name>`
- **Why:** Sanjay wants a dedicated "open source" home, separate from the product
  ventures (Geospatial, Trading, etc.), and a named project folder.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-13: The research used Exa MCP + GitHub/PyPI API via curl, not Firecrawl
- **Why:** Firecrawl's managed web allowance hit a billing-402 mid-session. The fallback
  (Exa search + curl against GitHub/PyPI APIs + primary sources) was actually *stronger*
  verification. Recorded so a future session does not thrash on a dead tool.
- **Model:** deepseek-v4-pro (fallback) + deepseek-v4-flash (used Exa in subagents).
  **Date:** 2026-08-15.
