# SettleFlow Commercial License

The core library (`settleflow/`) is MIT — free for everyone, including
commercial use. This document describes the *paid* layer on top of the open
core (the Sidekiq model, see `docs/DECISIONS.md` D-14).

## What is free (MIT)

- The parser, matching engine, and export functions in `settleflow/`.
- Using them in your own application, closed-source or open, at no cost.
- Running the thin SaaS yourself from `saas/`.

## What is paid (commercial license)

The MIT license does not entitle you to *our hosted service, support, or
warranty*. If you want any of the following, buy a commercial license:

| Offering | Price | What you get |
|---|---|---|
| **OEM / embedding license** | per-deployment or revenue-share, contact | The right to rebrand and resell SettleFlow's engine inside your product, plus our written trademark/name-use grant |
| **Support retainer** | ₹20,000–₹50,000 / month | SLA, priority fixes, onboarding help, a named human |
| **Hosted SettleFlow** | ₹4,000–₹7,000 / month | Managed instance, auto-ingest, exception queue, Tally/GST/TDS-1035 exports |

Prices are in INR; contact `kumarrusanjay@gmail.com` for terms. Nothing in
this file modifies the MIT license of the core library.
