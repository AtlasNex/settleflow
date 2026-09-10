# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.7.x (latest on `master`) | ✅ |
| anything older | ❌ — no backport policy during beta |

The project is pre-1.0 beta. Fixes ship to `master` and in the next tagged
release.

## Reporting a vulnerability

**Do not open a public GitHub issue** for security problems — SettleFlow
handles bank statements and settlement files, and a public report can itself
disclose user data.

Email **sanjay@atlasnex.com** with:

- a description of the issue and which component (`settleflow/` core,
  `saas/` web layer, or a parser),
- steps or a minimal reproducer (use fake/redacted data — never a real
  statement),
- the potential impact as you see it.

You should get an acknowledgement within **7 days**; expect a fix or a
published rationale within **30 days** for anything confirmed. The reporter's
name can be credited in the release notes on request (say so if you would
rather stay anonymous).

## Scope

In scope:

- The reconciliation/matching engine and all parsers (`settleflow/`).
- The hosted service at https://settleflow.atlasnex.com and the thin SaaS
  layer (`saas/`): upload handling, run-record access control, retention.
- Path traversal, injection, or data leakage through file uploads (the SaaS
  accepts CSV/PDF from untrusted users — malformed-input handling is a trust
  boundary, see `docs/CONSTRAINTS.md`).

Out of scope:

- Vulnerabilities in third-party dependencies *of the optional extras*
  (pymupdf, fastapi, uvicorn) — report those upstream, then tell us so we can
  bump pins. The core has no runtime dependencies by design.
- Social engineering of users; physical security.
- Findings requiring already-authenticated access to another user's run
  record during beta (report anyway if easy — we'll triage).

## Known posture

- Core library: stdlib only, no network calls of any kind from
  `settleflow/` — the entire data path is local file in → local file out.
- The hosted beta deletes uploaded files after processing; run records are
  retained 30 days (see `docs/legal/PRIVACY.md`).
- OCR (`[ocr]` extra) shells out to a locally installed Tesseract binary via
  `subprocess` with fixed arguments; no user-controlled string reaches a
  shell.

## Policy changes

This policy, like the legal drafts in `docs/legal/`, is maintained by an
individual operator pre-registration and may be updated as the project
matures.
