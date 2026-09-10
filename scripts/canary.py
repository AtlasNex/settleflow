#!/usr/bin/env python3
"""SettleFlow end-to-end canary.

A health endpoint only proves the process is up. This proves the PRODUCT works:
it uploads a real settlement file and a real bank statement through the public
surface, follows the private run URL, reads the generated tally export, and
checks the old public listing is still closed.

That last check is the point. The 11 Sep incident was a public /runs listing and
integer-id exports leaking every uploaded statement. A canary that cannot fail if
that route comes back is not watching the thing that actually went wrong.

Stdlib only, so it runs anywhere: in CI (against a locally started uvicorn), from
the laptop against the public URL, or on the VPS against 127.0.0.1.

    python scripts/canary.py --base https://settleflow.atlasnex.com
    python scripts/canary.py --base http://127.0.0.1:8093 --json

Exit 0 = every check passed. Exit 1 = at least one failed (details on stdout).
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
import urllib.error
import urllib.request

# Fixture: two settlements, one of which has a matching bank credit. The header
# names are deliberately NOT "utr/amount/date" so the canary also exercises the
# column auto-detection — a silent regression there would break real users first.
SETTLEMENTS = {
    "entity": "collection",
    "items": [
        {"id": "setl_CANARY0000001", "entity": "settlement", "amount": 9973635,
         "status": "processed", "fees": 0, "tax": 0,
         "utr": "1568176960vxp0rj", "created_at": 1568176960},
        {"id": "setl_CANARY0000002", "entity": "settlement", "amount": 50000,
         "status": "processed", "fees": 0, "tax": 0,
         "utr": "RZRP173069230702", "created_at": 1509622306},
    ],
}
BANK_CSV = (
    "Value Date,Narration,UTR No,Credit\n"
    "11/09/19,NEFT CR RAZORPAY,1568176960vxp0rj,99736.35\n"
).encode()

EXPECTED_AMOUNT = "99736.35"
EXPECTED_UTR = "1568176960vxp0rj"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Return the 3xx itself so the caller can read the Location header."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _get(url: str, timeout: int) -> tuple[int, str, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "settleflow-canary/1.0"})
    try:
        with _opener.open(req, timeout=timeout) as r:
            return r.getcode(), r.read(262144).decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(262144).decode("utf-8", "replace"), dict(e.headers or {})


def _post_multipart(url: str, fields: dict[str, str],
                    files: dict[str, tuple[str, bytes, str]], timeout: int):
    boundary = "----settleflowcanary" + secrets.token_hex(8)
    body = bytearray()
    for name, value in fields.items():
        body += (f"--{boundary}\r\n"
                 f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                 f"{value}\r\n").encode()
    for name, (filename, content, ctype) in files.items():
        body += (f"--{boundary}\r\n"
                 f'Content-Disposition: form-data; name="{name}"; '
                 f'filename="{filename}"\r\n'
                 f"Content-Type: {ctype}\r\n\r\n").encode()
        body += content + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        url, data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                 "User-Agent": "settleflow-canary/1.0"},
    )
    try:
        with _opener.open(req, timeout=timeout) as r:
            return r.getcode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {})


def check_health(base: str, timeout: int) -> tuple[bool, str]:
    code, body, _ = _get(f"{base}/health", timeout)
    if code != 200:
        return False, f"http {code}"
    try:
        data = json.loads(body)
    except ValueError:
        return False, "unparseable JSON"
    if data.get("status") != "ok":
        return False, f"status={data.get('status')!r}"
    if not data.get("version"):
        return False, "no version reported"
    return True, f"v{data['version']}"


def check_leak_closed(base: str, timeout: int) -> tuple[bool, str]:
    """The regression guard: no unauthenticated run listing or export."""
    for path in ("/runs", "/runs/1/export/tally.csv", "/r/1/export/tally.csv",
                 "/r/1", "/docs", "/openapi.json"):
        code, body, _ = _get(f"{base}{path}", timeout)
        if code != 404:
            return False, f"{path} returned {code}, expected 404"
        # A 404 page that echoes the run's data would be worse than a 200.
        if "amount_inr" in body:
            return False, f"{path} returned CSV columns"
    return True, "6 leak paths closed"


def check_roundtrip(base: str, timeout: int) -> tuple[bool, str]:
    """Upload -> private URL -> ledger -> export, exactly as a user would."""
    code, headers = _post_multipart(
        f"{base}/reconcile",
        {"settlement_kind": "razorpay_settlements"},
        {"settlement_file": ("settlements.json", json.dumps(SETTLEMENTS).encode(),
                             "application/json"),
         "bank_file": ("bank.csv", BANK_CSV, "text/csv")},
        timeout,
    )
    if code not in (302, 303):
        return False, f"POST /reconcile returned {code} (expected a redirect)"

    location = headers.get("Location") or headers.get("location") or ""
    if "/r/" not in location:
        return False, f"no private run URL in Location: {location!r}"
    token = location.rsplit("/r/", 1)[1]
    if len(token) < 24:
        return False, f"run token too short ({len(token)} chars)"

    page_code, page, _ = _get(f"{base}/r/{token}", timeout)
    if page_code != 200:
        return False, f"run page returned {page_code}"
    if EXPECTED_AMOUNT not in page:
        return False, f"run page does not show the matched total {EXPECTED_AMOUNT}"
    if "Matched" not in page:
        return False, "run page has no matched summary"

    csv_code, csv, _ = _get(f"{base}/r/{token}/export/tally.csv", timeout)
    if csv_code != 200:
        return False, f"tally export returned {csv_code}"
    if "amount_inr" not in csv:
        return False, "tally export has no amount_inr column"
    if EXPECTED_UTR not in csv:
        return False, "tally export is missing the matched bank UTR"

    return True, f"token={token[:8]}… amount={EXPECTED_AMOUNT} export ok"


def check_public_pages(base: str, timeout: int) -> tuple[bool, str]:
    """A stranger must find the pages the audit said were missing."""
    missing = []
    for path in ("/", "/about", "/pricing", "/contact", "/sitemap.xml", "/llms.txt"):
        code, body, _ = _get(f"{base}{path}", timeout)
        if code != 200:
            missing.append(f"{path}={code}")
        elif len(body) < 200:
            missing.append(f"{path}=empty")
    return (not missing), ("all 6 pages ok" if not missing else ", ".join(missing))


def check_cache_headers(base: str, timeout: int) -> tuple[bool, str]:
    """A run URL is a bearer credential: no shared cache may hold its response.

    This check exists because of a real miss on 11 Sep — the route was removed but
    Cloudflare kept serving the cached CSV with cf-cache-status: HIT. Asserting the
    origin's Cache-Control is what stops that recurring.
    """
    code, headers = _post_multipart(
        f"{base}/reconcile",
        {"settlement_kind": "razorpay_settlements"},
        {"settlement_file": ("settlements.json", json.dumps(SETTLEMENTS).encode(),
                             "application/json"),
         "bank_file": ("bank.csv", BANK_CSV, "text/csv")},
        timeout,
    )
    if code not in (302, 303):
        return False, f"POST /reconcile returned {code}"
    token = (headers.get("Location") or headers.get("location") or "").rsplit("/r/", 1)[-1]
    if not token:
        return False, "no run token to test"

    for path in (f"/r/{token}", f"/r/{token}/export/tally.csv", "/health"):
        _, _, h = _get(f"{base}{path}", timeout)
        cc = (h.get("Cache-Control") or h.get("cache-control") or "").lower()
        if "no-store" not in cc:
            return False, f"{path} Cache-Control={cc!r} (needs no-store)"
        if path.startswith("/r/"):
            robots = (h.get("X-Robots-Tag") or h.get("x-robots-tag") or "").lower()
            if "noindex" not in robots:
                return False, f"{path} X-Robots-Tag={robots!r} (needs noindex)"
    return True, "run URLs and /health are no-store + noindex"


CHECKS = (
    ("health", check_health),
    ("leak_closed", check_leak_closed),
    ("roundtrip", check_roundtrip),
    ("cache_headers", check_cache_headers),
    ("public_pages", check_public_pages),
)


def main() -> int:
    ap = argparse.ArgumentParser(description="SettleFlow end-to-end canary")
    ap.add_argument("--base", default="http://127.0.0.1:8093",
                    help="base URL (default: the service on this host)")
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    results = []
    for name, fn in CHECKS:
        t0 = time.time()
        try:
            ok, detail = fn(base, args.timeout)
        except Exception as exc:                          # noqa: BLE001
            ok, detail = False, f"{type(exc).__name__}: {exc}"[:160]
        results.append({"name": name, "ok": ok, "detail": detail,
                        "ms": int((time.time() - t0) * 1000)})

    failed = [r for r in results if not r["ok"]]
    if args.json:
        print(json.dumps({"base": base, "ok": not failed, "checks": results}))
    else:
        for r in results:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['name']:<13} {r['detail']}"
                  f"  ({r['ms']}ms)")
        print(f"\n{base}: {'ALL CHECKS PASSED' if not failed else 'FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
