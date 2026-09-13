# UI accessibility audit (2026-09-13)

WCAG 2.2 Level AA sweep of the hosted UI. Method: every foreground/background
pair the stylesheet can actually produce, measured with the WCAG relative-
luminance formula (the same math axe-core uses), then re-checked with
axe-core in a real browser (Chromium) in both colour schemes, then a visual
review pass. The claims in this file are reproducible: the ratio script is
stdlib-only (see bottom).

## What was broken

The old stylesheet overrode almost everything for `prefers-color-scheme: dark`
— except the three status classes that carry the product's meaning. On the
dark background they measured (pre-fix):

| Element | Pair (pre-fix) | Ratio | AA needs |
|---|---|---|---|
| `.ok` status number | `#0a7d32` on `#131313` | **3.53:1** | 4.5:1 — FAIL |
| `.warn` status number | `#a35b00` on `#131313` | **3.59:1** | 4.5:1 — FAIL |
| `.danger` status number | `#b00020` on `#131313` | **2.54:1** | 4.5:1 — FAIL (also fails the 3:1 large-text bar) |

Matched / exception / error counts are precisely the text a user scans for
status, so the failure was also a functional failure. Secondary findings from
the same sweep: `.btn` in dark mode had no colour rule at all (white text on a
light-blue accent in the new palette would have failed), no focus-visible
style anywhere, the file input rendered as a bare browser default, no
`<main>` landmark (axe `region` violation on every page), and no favicon /
OpenGraph image / theme-colour.

## The palette as shipped (0.7.5)

All values from `saas/templates/_style.html`; ratios computed, not estimated.

Light (`--bg #ffffff`, `--surface #f7f8fa`, `--surface-2 #eef0f3`, `--text #14171a`):

| Pair | Ratio | Verdict |
|---|---|---|
| body text on bg | 17.99:1 | PASS |
| muted on bg / on card | 6.00:1 / 5.64:1 | PASS |
| link on bg / on card | 6.70:1 / 6.31:1 | PASS |
| white on accent button | 6.70:1 | PASS |
| ok / warn / danger on bg | 5.46 / 6.51 / 7.33 | PASS |
| ok on card | 5.13:1 | PASS |
| code on surface-2 | 15.76:1 | PASS |
| table header on surface | 16.93:1 | PASS |
| input border vs bg (UI, 3:1) | 3.11:1 | PASS |

Dark (`--bg #101317`, `--surface #1a1e24`, `--surface-2 #242a31`, `--text #e6e9ed`):

| Pair | Ratio | Verdict |
|---|---|---|
| body text on bg | 15.29:1 | PASS |
| muted on bg / on card | 8.20:1 / 7.36:1 | PASS |
| link on bg / on card | 8.96:1 / 8.05:1 | PASS |
| ink `#0b0d10` on accent button | 9.36:1 | PASS |
| ok / warn / danger on bg | 10.12 / 10.46 / 7.67 | PASS |
| ok / warn / danger on card | 9.09 / 9.40 / 6.89 | PASS |
| code on surface-2 | 11.89:1 | PASS |
| table header on surface | 13.74:1 | PASS |

Colour is never the only signal: every status colour sits under a text label
(Matched / Exceptions / …), so status survives greyscale and screen-reader
reading. Focus is a 3px `:focus-visible` ring at accent colour with offset —
keyboard-operable throughout.

## Automated verification

- **axe-core 4.10.2** (rules run: color-contrast, heading-order, link-name,
  label, button-name, html-has-lang, document-title, region, meta-viewport)
  against a live server, both schemes, on every page type:
  `/`, `/about`, `/pricing`, `/contact`, `/privacy`, `/terms`, `/refund`,
  a real `/r/<token>` results page, and the 404 error page →
  **0 violations, all 18 page×scheme combinations.**
- **Real-browser screenshots** (Chromium, 2× DPI) reviewed for the dark-theme
  status trio and the file-input styling; a second review pass after the
  brand rasters were regenerated confirmed all six earlier visual defects
  fixed (the remaining reviewer notes were grid-wrap polish, not contrast).
- **The ratio math** is reproducible with this stdlib snippet (same formula as
  axe-core's color-contrast):

```python
def _srgb(c):
    c /= 255.0
    return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
def L(h):
    h = h.lstrip('#')
    if len(h) == 3: h = ''.join(x*2 for x in h)
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return 0.2126*_srgb(r) + 0.7152*_srgb(g) + 0.0722*_srgb(b)
def ratio(fg, bg):
    a, b = sorted((L(fg), L(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)
assert ratio("#e6e9ed", "#101317") > 4.5   # dark body text
```

## Brand assets

- `saas/static/logo.svg`, `favicon.svg` — the mark: two ledgers converging
  (gateway file + bank statement) with the matched tick. Favicon ships as
  SVG + a real `favicon.ico` (16/32/48) + PNG.
- `saas/static/og-image.png` — 1200×630 share card (dark theme, real product
  screenshot inset); `banner.png` — README masthead.
- `saas/static/screenshot-index.png` / `-dark.png` / `-results.png` — real
  renders of the app itself (produced by the asset pipeline at 2× DPI, not
  mock-ups), used in the README.
- Served at `/static/*` (public, cacheable, no user data) and
  `/favicon.ico` → 302 → `/static/favicon.svg`; the templates reference them
  from `_head.html` and `_brand.html`.

## Guard rails for the future

- Any new colour token must pass the same math before it ships — extend the
  snippet above or re-run the sweep rather than eyeballing.
- `.ok/.warn/.danger` overrides exist in the dark block on purpose; a PR that
  "simplifies" the dark block by removing them re-opens this exact bug.
- Status text must keep its label; do not introduce colour-only state in this UI.
- The axe sweep was scripted (see `docs/TESTING.md` SaaS checklist) — re-run it
  against any future template change worth shipping.
