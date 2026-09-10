# Privacy Policy — SettleFlow hosted service

> **DRAFT — NOT LEGAL ADVICE, NOT YET REVIEWED.** This draft is published for
> transparency while the operator completes business registration. It is not
> the final policy. Where registration details are required, placeholders are
> used deliberately and will be replaced after review by a qualified lawyer.
> Draft date: 2026-09-11.

## Who we are

SettleFlow is a hosted service for reconciliation of payment-gateway
settlement files against bank statements, available at
https://settleflow.atlasnex.com (the "Service"). It is operated by an
individual prior to business registration.

- Operator: individual (pre-registration). Registered entity name, address,
  and GSTIN, once they exist: **[ENTITY/GSTIN to be completed]**
- Contact for privacy matters: sanjay@atlasnex.com
- The underlying library is open source (MIT) at
  https://github.com/AtlasNex/settleflow. This policy applies to the hosted
  Service only. Self-hosted copies of the library are outside its scope — if
  you run the code yourself, you control the data.

## What data we process

When you use the Service you upload:

1. A **settlement file** (e.g. a Razorpay settlement/recon CSV).
2. A **bank statement** (CSV or PDF) for the matching period.

Optionally, on the results page, you may choose to provide an **email
address**.

No passwords, no account credentials, and no read access to your bank or
payment-gateway APIs are requested or required. There is no user account
system.

## How your files are used and for how long

- Uploaded files are used **only** to perform the single reconciliation you
  requested. They are not used to train models, not sold, and not shared
  with third parties.
- Uploaded statement/settlement files are removed from the server after
  processing.
- The **run record** — the match result, exception list, and generated
  export CSVs — is retained for **30 days** so you can re-download your
  workpapers, and is then deleted automatically.
- If you voluntarily submitted an email address on the results page, it is
  kept only to send you the workpaper pack and occasional product updates.
  Email removal on request: write to sanjay@atlasnex.com and it will be
  removed.

## Legal basis (India)

The Service is offered in the context of Indian users and transactions. The
operator processes the data you upload on the basis of your consent, for the
sole purpose you requested. Compliance mapping to the Digital Personal Data
Protection Act, 2023 (DPDP Act) obligations — including any required data
fiduciary registration — is **[TO BE COMPLETED AFTER LEGAL REVIEW]**.

## Third parties

- **Hosting / CDN infrastructure** (server and DNS providers) necessarily
  handle traffic to and from the Service.
- No analytics or advertising trackers are embedded in the Service pages.

## Security posture

- No login surface exists to be attacked; the only inputs are file uploads
  and form fields.
- Data in transit is protected by HTTPS (TLS).
- The reconciliation logic is fully auditable in the open-source repository —
  you (or your accountant) can read exactly what happens to a statement file.
- No claim of perfect security is made. Do not upload statements containing
  data you are not comfortable processing on a beta service.

## Children

The Service is a financial-reconciliation tool for businesses. It is not
directed at children and we do not knowingly accept their data.

## Changes

Material changes to this policy will be noted on this page with a date.
Because this is a beta service, terms may change as the operator registers a
business entity.

## Contact

Questions, deletion requests, or corrections: sanjay@atlasnex.com.
Operator entity details once registered: **[ENTITY/GSTIN to be completed]**.
