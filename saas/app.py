"""SettleFlow thin SaaS — the hosted layer on top of the open-core library.

Reconciles an uploaded settlement file against an uploaded bank-statement CSV,
persists the run, and serves accountant-facing workpapers (Tally / GST
worksheet / TDS code-1035).

ACCESS MODEL — the important part
--------------------------------
There are no accounts, and a run is reachable only through the unguessable URL
handed to whoever created it: ``/r/<run_token>``. That keeps the loop usable with
no signup while removing the previous design's fatal flaw — a public ``/runs``
listing (and integer-id exports) where anyone could read every uploaded
statement's matched UTRs, amounts, exception text and generated CSVs.

A token is the credential. It is never rendered into a page it does not own, is
not guessable (secrets.token_urlsafe(24) ~ 144 bits), and rows created before
this design existed have no token, so they are simply unreachable.

RETENTION — enforced, not promised
----------------------------------
Runs older than ``SETTLEFLOW_RETENTION_DAYS`` (default 30) are deleted on startup
and on every new run. The box this runs on is at 91% disk and will not be
expanded; a full disk fails every write, and the privacy page claims 30 days, so
the claim is backed by code rather than by intent.

Storage is stdlib sqlite3: one row per run, one row per captured lead.
"""
from __future__ import annotations

import csv
import io
import json
import os
import secrets
import smtplib
import sqlite3
import sys
import tempfile
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.mime.text import MIMEText
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # so `import helpers` works

from settleflow import __version__ as settleflow_version  # noqa: E402
from settleflow import (  # noqa: E402
    ReconLine,
    Txn,
    classify,
    export_gst_worksheet,
    export_tally_csv,
    export_tds_1035,
    format_money,
    group_batches,
    load_cashfree_recon_report,
    load_csv,
    load_settlement_csv,
    match,
    match_settlements,
    parse_payu_settlement_range,
    parse_payu_transaction_details,
    parse_razorpay_recon,
    parse_razorpay_settlements,
)

from helpers import (  # noqa: E402  (saas/ is on sys.path via the line above)
    decode_text,
    guess_columns,
    human_bytes,
    max_request_bytes,
    md_to_html,
    pick_client_ip,
    request_too_large,
    valid_email,
)

BASE = Path(__file__).resolve().parent
PROJECT_ROOT = BASE.parent
DB_PATH = BASE / "settleflow.db"
TEMPLATES = Jinja2Templates(directory=str(BASE / "templates"))

#: Upload ceiling. Settlement recons for an SMB are kilobytes; 10 MB is generous
#: and stops a single request from filling a 91%-full disk. Over the cap is a 413
#: with a human message, never a 500.
MAX_UPLOAD_BYTES = int(os.environ.get("SETTLEFLOW_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
RETENTION_DAYS = int(os.environ.get("SETTLEFLOW_RETENTION_DAYS", "30"))

#: Reconciles are CPU-bound and write to disk, so an unauthenticated endpoint
#: needs a ceiling that is not "however many requests arrive". 60/hour is one a
#: minute sustained: enough that a CA reconciling a client's month in one sitting
#: never notices it, low enough that a scripted abuser cannot fill the box.
#: ponytail: ceiling = one process's memory, sliding window, resets on restart.
#: Correct for a single-instance service; if this ever runs multi-worker, move the
#: counter to sqlite (same table, one more column) rather than reaching for Redis.
RATE_LIMIT_PER_HOUR = int(os.environ.get("SETTLEFLOW_RATE_LIMIT_PER_HOUR", "60"))
#: Identity-independent ceiling on /reconcile. The per-identity window keys on
#: CF-Connecting-IP, so a caller that can choose that header mints a fresh bucket
#: per request; this window counts every accepted request, so the total rate stays
#: bounded even if the identity assumption is broken again. It bounds request
#: COUNT, not the cost of one request — the derived-work cap is the other half.
GLOBAL_RATE_LIMIT_PER_HOUR = int(
    os.environ.get("SETTLEFLOW_GLOBAL_RATE_LIMIT_PER_HOUR", "600")
)
_rate_hits: dict[str, deque[float]] = {}
_global_hits: deque[float] = deque()
_rate_lock = threading.Lock()

ACCEPTED_BANK_SUFFIXES = (".csv", ".txt", ".tsv")

#: Which settlement formats the hosted service accepts, and what each produces.
#: These are the formats the LIBRARY already reads — the service was exposing one of
#: six, so a Cashfree/PhonePe/Juspay/PayU user had no hosted path at all while
#: /about told them the formats were "not wired".
#:
#: A "recon" kind is per-line-item, which is what unlocks the GST and TDS workpapers;
#: a batch kind is one row per bank credit or per settlement.
_JSON_SETTLEMENT_KINDS = {
    # name -> parser -> list[Settlement] (batch) or list[ReconLine] (line item)
    "razorpay_settlements": parse_razorpay_settlements,
    "razorpay_recon": parse_razorpay_recon,
    "payu_settlement_range": parse_payu_settlement_range,
    "payu_transaction_details": parse_payu_transaction_details,
}
_CSV_SETTLEMENT_KINDS = (
    # name -> the vendor key the loader is registered under. "cashfree_recon_csv" is
    # special: its one file holds both sections, so it is read as line items.
    "razorpay_settlement_csv",
    "phonepe_settlement_csv",
    "juspay_settlement_csv",
    "cashfree_settlement_csv",
    "cashfree_recon_csv",
)
SETTLEMENT_KINDS = {**_JSON_SETTLEMENT_KINDS,
                    **{name: None for name in _CSV_SETTLEMENT_KINDS}}


def _accepted_settlement_suffixes(kind: str) -> tuple[str, ...]:
    return (".json",) if kind in _JSON_SETTLEMENT_KINDS else ACCEPTED_BANK_SUFFIXES


def _load_settlement_side(kind: str, raw: bytes) -> tuple[list | None, list | None]:
    """Read the uploaded settlement file: (batch rows, recon lines).

    Exactly one of the two is returned non-None. Batch rows are matched level-1
    (one row per bank credit); recon lines are netted per batch and matched level-2,
    which is also where the GST and TDS workpapers come from.
    """
    if kind in _JSON_SETTLEMENT_KINDS:
        payload = json.loads(
            raw.decode("utf-8-sig"),
            parse_float=Decimal,
            parse_constant=_reject_json_constant,
        )
        rows = _JSON_SETTLEMENT_KINDS[kind](payload)
        if rows and isinstance(rows[0], ReconLine):
            return None, rows
        return rows, None

    # The CSV loaders take a path, so the upload goes through a temp file — the same
    # shape the bank statement already uses, and deleted in the finally.
    suffix = ".csv"
    with tempfile.NamedTemporaryFile("wb", suffix=suffix, delete=False) as fh:
        fh.write(raw)
        path = fh.name
    try:
        if kind == "cashfree_recon_csv":
            # Two sections in one file; read the event section as line items and let
            # the line-item path do the netting (its per-UTR net equals the batch total).
            _batches, lines = load_cashfree_recon_report(path)
            return None, lines
        return load_settlement_csv(path, kind), None
    finally:
        Path(path).unlink(missing_ok=True)

#: Whitelist, so no request value ever reaches SQL string interpolation.
_EXPORTS = {
    "tally.csv": ("tally_csv", "tally"),
    "gst.csv": ("gst_csv", "gst"),
    "tds1035.csv": ("tds1035_csv", "tds1035"),
}

REPO_URL = "https://github.com/AtlasNex/settleflow"
CONTACT_EMAIL = "sanjay@atlasnex.com"

#: `docs_url=None` etc. on purpose: the default Swagger UI is developer-facing,
#: and this is a buyer-facing site (the 30 Aug audit flagged it).
app = FastAPI(
    title="SettleFlow",
    version=settleflow_version,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.middleware("http")
async def _no_store_private_paths(request: Request, call_next):
    """Never let a shared cache hold a run's data.

    Found the hard way on 11 Sep: the app stopped serving /runs/<id>/export/*.csv,
    but Cloudflare had already cached that `text/csv` at the edge (csv is in CF's
    default cacheable-extension list) and kept serving the leaked workpaper with
    cf-cache-status: HIT for the rest of its 4-hour TTL. Removing a route does not
    un-publish what the CDN already holds.

    A run URL is a bearer credential, so its response must be no-store everywhere:
    browser, proxy, or edge. /health is included because a cached health check is
    the "process is up" illusion this project keeps getting bitten by.
    """
    response = await call_next(request)
    path = request.url.path
    if (path.startswith("/r/") or path == "/reconcile"
            or path == "/health" or path.endswith("/notify")):
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


class _BodySizeLimit:
    """Refuse a request whose body exceeds the service ceiling.

    The app's own `MAX_UPLOAD_BYTES` cap only sees the two files it parses. The
    multipart parser bounds each form FIELD at 1MB but spools file parts with no
    size check, so extra parts rode straight through: a 210MB request carrying one
    unnamed part was answered 303 while a 10.5MB named file was refused with a 413.
    The advertised ceiling was therefore not the effective one, and the only real
    bound was whatever the proxy allowed.

    Checks the declared Content-Length first (cheap, and the ordinary case), then
    counts the bytes as they arrive, so a chunked request with no declared length
    cannot walk past either.
    """

    def __init__(self, app, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = next(
            (value.decode("latin-1") for key, value in scope.get("headers", [])
             if key.lower() == b"content-length"),
            None,
        )
        if request_too_large(declared, self.limit):
            await _send_413(send, self.limit)
            return

        state = {"seen": 0, "exceeded": False, "started": False}

        async def counted_receive():
            message = await receive()
            if message["type"] == "http.request":
                state["seen"] += len(message.get("body", b""))
                if state["seen"] > self.limit:
                    state["exceeded"] = True
                    # Stop feeding the parser so the request unwinds; the 413 is
                    # sent below, outside the app.
                    return {"type": "http.disconnect"}
            return message

        async def tracked_send(message):
            if message["type"] == "http.response.start":
                state["started"] = True
            await send(message)

        try:
            await self.app(scope, counted_receive, tracked_send)
        except Exception:
            # Only swallow the failure our own trip caused; a real bug still raises.
            if not state["exceeded"] or state["started"]:
                raise
        if state["exceeded"] and not state["started"]:
            await _send_413(send, self.limit)


async def _send_413(send, limit: int) -> None:
    """The too-large page, sent from middleware so it needs no route."""
    body = (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>That upload was too large</title></head><body>"
        "<h1>That upload was too large</h1>"
        f"<p>The whole request must be under {human_bytes(limit)}. Settlement and "
        "recon files are normally a few hundred KB.</p>"
        "<p>Nothing was uploaded or stored. "
        "<a href=\"/\">Go back</a> and try again with a smaller file.</p>"
        "</body></html>\n"
    ).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": 413,
        "headers": [
            (b"content-type", b"text/html; charset=utf-8"),
            (b"content-length", str(len(body)).encode("latin-1")),
            (b"cache-control", b"no-store, private"),
        ],
    })
    await send({"type": "http.response.body", "body": body})


app.add_middleware(_BodySizeLimit, limit=max_request_bytes(MAX_UPLOAD_BYTES))


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate() -> None:
    """Create/upgrade the schema. Safe to run on every start.

    `run_token` and `mapping_json` are added to a table that already exists in
    production, so they arrive by ALTER rather than by a recreate. Existing rows
    keep a NULL token and become unreachable — which is the point: they were the
    publicly listed ones.
    """
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                result_json TEXT,
                exceptions_json TEXT,
                tally_csv TEXT,
                gst_csv TEXT,
                tds1035_csv TEXT
            )
            """
        )
        existing = {row["name"] for row in c.execute("PRAGMA table_info(runs)")}
        if "run_token" not in existing:
            c.execute("ALTER TABLE runs ADD COLUMN run_token TEXT")
        if "mapping_json" not in existing:
            c.execute("ALTER TABLE runs ADD COLUMN mapping_json TEXT")
        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS runs_run_token ON runs(run_token)"
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                email TEXT NOT NULL,
                run_token TEXT,
                delivered INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS leads_email ON leads(email)")


def _prune(conn: sqlite3.Connection | None = None) -> int:
    """Delete runs past the retention window. Returns the number removed.

    Runs on startup and before every new run, so the window holds even if the
    service is never restarted. Not a background thread: a service that must be
    up to delete data will eventually stop deleting data.

    `leads` is pruned alongside `runs`: the privacy page advertises the 30-day
    window, and without this the table grew forever (verified: 10,000 rows in
    25s via the unthrottled notify route, none ever deleted).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
    own = conn is None
    c = conn or _conn()
    try:
        c.execute("DELETE FROM leads WHERE created_at < ?", (cutoff,))
        cur = c.execute("DELETE FROM runs WHERE created_at < ?", (cutoff,))
        removed = cur.rowcount or 0
        if own:
            c.commit()
        return removed
    finally:
        if own:
            c.close()


_migrate()
_prune()


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------

def _new_token() -> str:
    """URL-safe, unguessable. 24 random bytes ~ 144 bits of entropy."""
    return secrets.token_urlsafe(24)


def _client_ip(request: Request) -> str:
    """The caller's address for rate limiting.

    Delegates to helpers.pick_client_ip so the rule is testable without FastAPI and
    is stated once. The peer is passed so the rule is deployment-aware: a request
    that arrived through an intermediary (loopback cloudflared, or the docker
    bridge gateway that fronts every published-port connection) is keyed on the
    edge-set CF-Connecting-IP (D-41: the edge 403s caller-supplied values), while
    a request whose peer is public reached the origin directly and is keyed on
    that peer — a value its owner cannot mint away per request. X-Forwarded-For
    stays untrusted either way: its first hop was 70 accepted / 0 rejected.
    """
    return pick_client_ip(request.headers,
                          request.client.host if request.client else None)


def _rate_ok(ip: str) -> bool:
    now = time.time()
    with _rate_lock:
        # The identity-independent window first: the per-identity key can be
        # minted away by claiming a fresh address per request, this one cannot.
        # It bounds the request RATE, not the cost of one request.
        while _global_hits and now - _global_hits[0] > 3600:
            _global_hits.popleft()
        if len(_global_hits) >= GLOBAL_RATE_LIMIT_PER_HOUR:
            return False
        hits = _rate_hits.setdefault(ip, deque())
        while hits and now - hits[0] > 3600:
            hits.popleft()
        if len(hits) >= RATE_LIMIT_PER_HOUR:
            return False
        hits.append(now)
        _global_hits.append(now)
        return True


def _read_capped(upload: UploadFile, limit: int) -> bytes:
    """Read an upload, refusing anything over `limit`.

    Checks the declared size first, then enforces the cap while reading, so a
    lying Content-Length cannot slip through.
    """
    declared = getattr(upload, "size", None)
    if isinstance(declared, int) and declared > limit:
        raise _too_big(declared, limit)
    raw = upload.file.read(limit + 1)
    if len(raw) > limit:
        raise _too_big(len(raw), limit)
    return raw


def _too_big(actual: int, limit: int) -> HTTPException:
    return HTTPException(
        413,
        f"That file is {human_bytes(actual)} — the limit is {human_bytes(limit)}. "
        "Settlement and recon files are normally a few hundred KB.",
    )


def _require_suffix(upload: UploadFile, allowed: tuple[str, ...], what: str) -> None:
    name = (upload.filename or "").strip()
    if not name:
        raise HTTPException(400, f"No {what} file was attached.")
    if not name.lower().endswith(allowed):
        raise HTTPException(
            400,
            f"{name!r} does not look like a {what} file "
            f"(expected {' or '.join(allowed)}).",
        )


def _reject_json_constant(name: str):
    """Refuse the bare NaN / Infinity literal in a settlement payload.

    Python's `json` accepts them even though they are not JSON, and as money they
    are meaningless: they would flow into the export layer's quantize() and raise
    mid-request, turning a bad file into a 500. Raising here means the caller gets
    a 400 naming the problem.
    """
    raise ValueError(f"{name} is not a valid amount in a settlement file")


# ---------------------------------------------------------------------------
# Error pages — a person must never meet a traceback or a blank screen
# ---------------------------------------------------------------------------

def _render(request: Request, template: str, ctx: dict, status: int = 200) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, template, ctx, status_code=status)


def _error_page(request: Request, status: int, title: str, message: str,
                hint: str | None = None) -> HTMLResponse:
    return _render(
        request, "error.html",
        {"title": title, "heading": title, "message": message, "hint": hint,
         "status": status, "footer": _footer()},
        status=status,
    )


@app.exception_handler(HTTPException)
def _http_error(request: Request, exc: HTTPException) -> HTMLResponse:
    titles = {
        400: "That didn't work",
        404: "Not found",
        413: "File too large",
        429: "Too many reconciliations",
    }
    body = exc.detail if isinstance(exc.detail, str) else "Something went wrong."
    hints = {
        400: "Check the file you picked, or open Advanced to name the columns "
             "yourself. Nothing was stored.",
        404: "If you came from a link to a run, that run may have expired — runs "
             f"are deleted after {RETENTION_DAYS} days.",
        413: "Nothing was uploaded. Try again with a smaller file.",
        429: f"The limit is {RATE_LIMIT_PER_HOUR} actions per hour from "
             f"one connection ({GLOBAL_RATE_LIMIT_PER_HOUR} across the whole "
             "service). Nothing was stored.",
    }
    return _error_page(request, exc.status_code, titles.get(exc.status_code, "Something went wrong"),
                       body, hints.get(exc.status_code))


@app.exception_handler(StarletteHTTPException)
def _http_error_starlette(request: Request, exc: StarletteHTTPException) -> HTMLResponse:
    """Same page for Starlette's own HTTPException.

    FastAPI's HTTPException subclasses Starlette's, and the handlers are matched by
    exact class — so a raise coming from inside Starlette (the multipart parser's
    "Part exceeded maximum size of 1024KB" is one) bypassed the handler above and
    reached the client as raw framework JSON, which is exactly the traceback-adjacent
    output a person must never meet. Delegating keeps one page and one set of hints.
    """
    return _http_error(request, exc)


@app.exception_handler(Exception)
def _unhandled(request: Request, exc: Exception) -> HTMLResponse:
    """Last line of defence.

    The reference is logged so a report can be matched to a stack trace; the user
    gets a sentence and a way forward, never the trace itself.
    """
    ref = secrets.token_hex(4)
    print(f"[settleflow] unhandled error ref={ref}: {type(exc).__name__}: {exc}",
          file=sys.stderr, flush=True)
    return _error_page(
        request, 500, "Something broke on our side",
        "The reconciliation could not be completed. Your files were not kept.",
        f"Quote reference {ref} if you report it, or email {CONTACT_EMAIL}.",
    )


# ---------------------------------------------------------------------------
# Page furniture
# ---------------------------------------------------------------------------

def _footer() -> dict:
    return {
        "repo_url": REPO_URL,
        "contact_email": CONTACT_EMAIL,
        "version": settleflow_version,
        "retention_days": RETENTION_DAYS,
    }


#: Public pages, written in the same markdown subset `md_to_html` renders, so
#: copy lives in one obvious place and legal text can come from disk (below).
_STATIC_PAGES: dict[str, tuple[str, str]] = {
    "about": (
        "About SettleFlow",
        """SettleFlow reconciles a payment-gateway settlement file against your bank
statement, then exports Tally / GST / TDS-1035 workpapers.

It is built by **AtlasNex**. The parsing and matching engine is open source under
the MIT licence — [github.com/AtlasNex/settleflow](https://github.com/AtlasNex/settleflow) —
so you can read exactly how a match was made, or run the whole thing on your own
machine with no account and no upload.

## Why it exists

UPI settles as bulk NEFT credits. Your bank statement shows one undifferentiated
credit; your gateway's settlement file is the only thing that breaks it back into
orders. Rebuilding that by hand is 8-12 hours a month for a business doing
200-300 UPI collections, and the match key is not the UTR — the bank's UTR is the
correspondent bank's, which is a different number.

## What this tool does not do

It does not file your returns, it does not talk to the income tax portal, and it
does not decide whether a TDS entry is correct. It matches your two files and
shows you the exceptions. Nothing here is tax advice.

## What is not built yet

Nothing here pretends. The engine reads Razorpay (API JSON and CSV), PayU's two
settlement APIs, and Cashfree, PhonePe and Juspay settlement exports. A format we
have no verified sample for is refused rather than guessed at — guessing a column
layout is how silently wrong ledgers get made — and the two still open are noted in
the repository: IDFC bank statements, and Cashfree's plain (non-recon) settlements
export.
"""
    ),
    "pricing": (
        "Pricing",
        """**The hosted service is free while in beta.** There is no card, no account
and no trial clock — upload the two files, get the workpapers.

**Self-hosting is free, permanently.** The engine is MIT-licensed. Run it on your
own machine and nothing leaves your network:

`pip install git+https://github.com/AtlasNex/settleflow.git`

(Not on PyPI yet — installing from the repository is the supported path today, so
that is the command shown rather than one that would fail.)

## Why it is free right now

The library is the product we want adopted; the hosted service is how we find out
whether the exports are actually right for real books. Charging for that discovery
would be backwards.

## What will be paid later

A hosted tier and a commercial support/embedding licence are planned. Anything
already free at launch stays free to use at the version you have — the code is
MIT, so that is not a promise, it is a licence.

Questions about your case: sanjay@atlasnex.com
""",
    ),
    "contact": (
        "Contact",
        """**Email: sanjay@atlasnex.com**

Useful things to include:

- which gateway and bank the two files came from
- what the reconciliation got wrong (or the exception you cannot explain)
- a sample export, if you are able to share one — a format we can see is a format
  we can support

We aim to reply within two working days. This is a small operation, not a
support desk, and it is honest about that.

**Bugs and feature requests** belong in the issue tracker:
[github.com/AtlasNex/settleflow/issues](https://github.com/AtlasNex/settleflow/issues)
""",
    ),
}

#: Legal drafts live as files so they can be reviewed and edited without touching
#: code. They are drafts: an India-facing service needs them reviewed, and the
#: pages say so rather than pretending otherwise.
_LEGAL_FILES = {
    "privacy": ("Privacy", "PRIVACY.md"),
    "terms": ("Terms", "TERMS.md"),
    "refund": ("Refunds", "REFUND.md"),
}


def _legal_page(request: Request, slug: str) -> HTMLResponse:
    title, filename = _LEGAL_FILES[slug]
    path = PROJECT_ROOT / "docs" / "legal" / filename
    if not path.exists():
        return _error_page(
            request, 404, f"{title} policy not published yet",
            "This policy is still being reviewed and is not live.",
            f"Until it is, email {CONTACT_EMAIL} with any question about your data.",
        )
    return _render(
        request, "page.html",
        {"title": f"{title} — SettleFlow", "heading": title,
         "body_html": md_to_html(path.read_text(encoding="utf-8")),
         "footer": _footer()},
    )


# ---------------------------------------------------------------------------
# Routes — public pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return _render(
        request, "index.html",
        {"title": "SettleFlow — UPI settlement reconciliation",
         "max_upload": human_bytes(MAX_UPLOAD_BYTES),
         "footer": _footer()},
    )


def _static_page(request: Request, slug: str) -> HTMLResponse:
    title, body = _STATIC_PAGES[slug]
    return _render(
        request, "page.html",
        {"title": f"{title} — SettleFlow", "heading": title,
         "body_html": md_to_html(body), "footer": _footer()},
    )


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return _static_page(request, "about")


@app.get("/pricing", response_class=HTMLResponse)
def pricing(request: Request):
    return _static_page(request, "pricing")


@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return _static_page(request, "contact")


@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return _legal_page(request, "privacy")


@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return _legal_page(request, "terms")


@app.get("/refund", response_class=HTMLResponse)
def refund(request: Request):
    return _legal_page(request, "refund")


@app.get("/health")
def health():
    """Liveness + the two things worth knowing from outside."""
    try:
        with _conn() as c:
            runs = c.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]
        return {"status": "ok", "version": settleflow_version, "runs": runs,
                "retention_days": RETENTION_DAYS}
    except Exception as exc:  # a health check that cannot fail is not a check
        raise HTTPException(503, f"storage unavailable: {type(exc).__name__}") from exc


@app.get("/sitemap.xml")
def sitemap(request: Request) -> Response:
    base = str(request.base_url).rstrip("/")
    pages = ["/", "/about", "/pricing", "/contact", "/privacy", "/terms", "/refund"]
    urls = "\n".join(
        f"  <url><loc>{base}{p}</loc><changefreq>monthly</changefreq></url>" for p in pages
    )
    return Response(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
        media_type="application/xml",
    )


@app.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt(request: Request) -> str:
    """What an AI assistant should know about this site, in one file."""
    return f"""# SettleFlow

> Open-source UPI/NPCI settlement reconciliation for India. Upload a payment-gateway
> settlement file and a bank statement CSV; get matched transactions, an exception
> list, and Tally / GST / TDS code-1035 workpapers. MIT-licensed engine.

- What it solves: UPI settles as bulk NEFT credits, so a bank statement shows one
  undivided credit while the gateway's settlement file disagrees. The match key is
  the gateway settlement_id plus (settlement date + net amount) — NOT the UTR,
  because the bank statement carries the correspondent bank's UTR.
- Hosted service: {str(request.base_url).rstrip('/')} (free while in beta)
- Source code: {REPO_URL} (MIT)
- Documentation: {REPO_URL}#readme
- Contact: {CONTACT_EMAIL}
- Data handling: uploaded files are used for the single reconciliation; the run
  record is deleted after {RETENTION_DAYS} days.
- Settlement formats accepted: Razorpay (API JSON and CSV exports), PayU (the two
  settlement APIs), Cashfree (Settlement Recon report), PhonePe, Juspay.
- Not available here: IDFC bank statements and Cashfree's plain (non-recon)
  settlements export — no verified sample exists, so they are refused rather than
  guessed at. Also not offered: e-filing, tax advice.
"""


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots(request: Request) -> str:
    """Origin robots.txt.

    NOTE: this zone's robots.txt is currently served by Cloudflare's *managed*
    robots.txt, which disallows GPTBot/ClaudeBot site-wide and takes precedence
    over this handler. Serving it here is still correct (it is what applies if the
    managed policy is turned off, and it is what self-hosters get), but flipping
    the managed policy is a Cloudflare-dashboard/API change, not a code change.
    """
    base = str(request.base_url).rstrip("/")
    return f"""User-agent: *
Allow: /
Disallow: /reconcile
Disallow: /r/

# The private per-run URLs must never be crawled or indexed.
User-agent: GPTBot
Allow: /$
Allow: /about
Allow: /pricing
Allow: /contact
Disallow: /r/
Disallow: /reconcile

User-agent: ClaudeBot
Allow: /$
Allow: /about
Allow: /pricing
Allow: /contact
Disallow: /r/
Disallow: /reconcile

User-agent: PerplexityBot
Allow: /$
Allow: /about
Allow: /pricing
Allow: /contact
Disallow: /r/
Disallow: /reconcile

Sitemap: {base}/sitemap.xml
"""


# ---------------------------------------------------------------------------
# The reconciler
# ---------------------------------------------------------------------------

def _detect_mapping(bank_text: str) -> tuple[list[str], dict[str, str | None]]:
    """Return (header cells, guessed role -> column) for an uploaded bank CSV."""
    reader = csv.reader(io.StringIO(bank_text))
    for row in reader:
        if any(cell.strip() for cell in row):
            return row, guess_columns(row)
    return [], {"utr": None, "amount": None, "date": None}


def _resolve_columns(
    header: list[str],
    guessed: dict[str, str | None],
    overrides: dict[str, str],
) -> dict[str, str]:
    """Decide the final column mapping, refusing to guess silently.

    An explicit value from the form always wins (that is what Advanced is for),
    but it has to actually exist in the file — otherwise the loader would raise a
    bare KeyError and the user would learn nothing.
    """
    resolved: dict[str, str] = {}
    lowered = {cell.strip().lower(): cell for cell in header}
    for role, override in overrides.items():
        candidate = (override or "").strip()
        if candidate:
            if candidate.lower() not in lowered:
                raise HTTPException(
                    400,
                    f"Column {candidate!r} is not in that CSV. Columns found: "
                    f"{', '.join(header) or '(none)'}.",
                )
            resolved[role] = lowered[candidate.lower()]
        elif guessed.get(role):
            resolved[role] = guessed[role]  # type: ignore[assignment]
        else:
            raise HTTPException(
                400,
                f"Could not tell which column is the {role} column. Columns "
                f"found: {', '.join(header) or '(none)'}. Open Advanced and name "
                "it, and nothing is stored until the mapping is right.",
            )
    return resolved


@app.post("/reconcile")
async def reconcile(
    request: Request,
    settlement_file: UploadFile = File(...),
    bank_file: UploadFile = File(...),
    settlement_kind: str = Form("razorpay_settlements"),
    bank_utr_col: str = Form(""),
    bank_amount_col: str = Form(""),
    bank_date_col: str = Form(""),
):
    """Reconcile, store the run, and hand back the owner's private URL."""
    if not _rate_ok(_client_ip(request)):
        raise HTTPException(429, "Too many reconciliations from this connection.")

    kind = (settlement_kind or "").strip()
    if kind not in SETTLEMENT_KINDS:
        raise HTTPException(
            400,
            f"Unknown settlement kind {kind!r}. Supported: "
            f"{', '.join(sorted(SETTLEMENT_KINDS))}.",
        )

    _require_suffix(settlement_file, _accepted_settlement_suffixes(kind), "settlement")
    _require_suffix(bank_file, ACCEPTED_BANK_SUFFIXES, "bank statement (CSV)")

    settlement_raw = _read_capped(settlement_file, MAX_UPLOAD_BYTES)
    bank_raw = _read_capped(bank_file, MAX_UPLOAD_BYTES)

    # --- settlement side -------------------------------------------------
    try:
        settlements, recon_lines = _load_settlement_side(kind, settlement_raw)
    except (UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
        # ValueError covers json.JSONDecodeError (a subclass) and the parsers'
        # fail-closed refusals, whose own sentence is the most useful text we have;
        # KeyError/TypeError cover a payload that is merely the wrong shape. Those
        # are the CALLER's file, not our bug, so they are a 400 and not a 500.
        raise HTTPException(400, f"That settlement file could not be read: {exc}") from exc

    if not settlements and not recon_lines:
        raise HTTPException(
            400,
            f"That {kind} file contained no rows we could read. Check that it is the "
            "right export for that settlement kind, and that the period is not empty.",
        )

    # --- bank side -------------------------------------------------------
    bank_text = decode_text(bank_raw)
    header, guessed = _detect_mapping(bank_text)
    if not header:
        raise HTTPException(400, "The bank statement CSV appears to be empty.")
    mapping = _resolve_columns(
        header, guessed,
        {"utr": bank_utr_col, "amount": bank_amount_col, "date": bank_date_col},
    )

    # A unique temp file per request. The previous single fixed path meant two
    # simultaneous uploads overwrote each other's statement.
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix=".csv", delete=False, encoding="utf-8", newline=""
    )
    try:
        tmp.write(bank_text)
        tmp.close()
        try:
            bank = load_csv(tmp.name, mapping["utr"], mapping["amount"], mapping["date"])
        except KeyError as exc:
            raise HTTPException(
                400, f"Column mapping failed on {exc}. Columns found: {', '.join(header)}."
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                400,
                f"A row in the bank statement could not be read: {exc}. Check that "
                f"the amount column ({mapping['amount']}) holds numbers and the date "
                f"column ({mapping['date']}) holds dates.",
            ) from exc
    finally:
        Path(tmp.name).unlink(missing_ok=True)

    if not bank:
        raise HTTPException(
            400,
            f"No usable rows in the bank statement. Columns found: {', '.join(header)}.",
        )

    # --- reconcile -------------------------------------------------------
    gst_csv = ""
    tds1035_csv = ""
    if recon_lines is not None:
        batches = group_batches(recon_lines)
        settlement_txns = [
            Txn(utr=b.utr, amount=b.net,
                txn_date=(b.lines[0].settled_at or b.lines[0].created_at),
                ref=b.settlement_id)
            for b in batches
        ]
        result = match(settlement_txns, bank)
        gst_csv = export_gst_worksheet(recon_lines)
        tds1035_csv = export_tds_1035(recon_lines)
    elif settlements and isinstance(settlements[0], Txn):
        # A CSV vendor loader already yields bank-credit rows (Txn); an API parser
        # yields Settlement batches, which match_settlements converts. Same engine,
        # two input shapes.
        result = match(settlements, bank)
    else:
        result = match_settlements(settlements, bank)

    tally_csv = export_tally_csv(result)
    exceptions = classify(result)

    result_json = json.dumps({
        # format_money, not str(): the page and the CSV it links to are the same
        # workpaper, and they used to disagree ('100' on the page, '100.00' in the
        # export) because a raw Decimal drops trailing zeros.
        "matched": [{"settlement": m.settlement.ref, "bank": m.bank.utr,
                     "amount": format_money(m.settlement.amount), "status": m.status.value}
                    for m in result.matched],
        "settlement_only": [{"ref": t.ref, "amount": format_money(t.amount)}
                            for t in result.settlement_only],
        "bank_only": [{"utr": t.utr, "amount": format_money(t.amount)}
                      for t in result.bank_only],
        "matched_total": format_money(result.matched_total),
        "unmatched_settlement_total": format_money(result.unmatched_settlement_total),
        "unmatched_bank_total": format_money(result.unmatched_bank_total),
    })
    exceptions_json = json.dumps([
        {"category": e.category, "amount": format_money(e.amount), "detail": e.detail,
         "utr": e.utr, "ref": e.ref}
        for e in exceptions
    ])

    token = _new_token()
    with _conn() as c:
        _prune(c)
        cur = c.execute(
            "INSERT INTO runs (created_at, kind, result_json, exceptions_json, "
            "tally_csv, gst_csv, tds1035_csv, run_token, mapping_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), kind, result_json,
             exceptions_json, tally_csv, gst_csv, tds1035_csv, token,
             json.dumps(mapping)),
        )
        run_id = cur.lastrowid

    print(f"[settleflow] run {run_id} kind={kind} "
          f"matched={len(result.matched)} exceptions={len(exceptions)}",
          flush=True)

    # POST -> redirect -> GET: the private URL is the credential, so it belongs
    # in the URL bar and the back button, not in a one-shot response body.
    return RedirectResponse(f"/r/{token}", status_code=303)


@app.get("/r/{token}", response_class=HTMLResponse)
def run_page(request: Request, token: str, saved: str = "", error: str = ""):
    with _conn() as c:
        row = c.execute("SELECT * FROM runs WHERE run_token = ?", (token,)).fetchone()
    if row is None:
        raise HTTPException(404, "run not found")

    result = json.loads(row["result_json"] or "{}")
    exceptions = json.loads(row["exceptions_json"] or "[]")
    exports = [name for name, (col, _label) in _EXPORTS.items() if row[col]]
    mapping = json.loads(row["mapping_json"] or "{}")

    try:
        created = datetime.fromisoformat(row["created_at"])
    except (TypeError, ValueError):
        created = None

    return _render(
        request, "results.html",
        {
            "title": "Reconciliation result — SettleFlow",
            "token": token,
            "created": created,
            "kind": row["kind"],
            "result": result,
            "exceptions": exceptions,
            "exports": exports,
            "mapping": mapping,
            "saved": saved == "1",
            "form_error": error,
            "smtp_ready": _smtp_configured(),
            "noindex": True,
            "footer": _footer(),
        },
    )


@app.get("/r/{token}/exceptions", response_class=PlainTextResponse)
def run_exceptions(token: str) -> str:
    with _conn() as c:
        row = c.execute(
            "SELECT exceptions_json FROM runs WHERE run_token = ?", (token,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, "run not found")
    return PlainTextResponse(row["exceptions_json"], media_type="application/json")


@app.get("/r/{token}/export/{name}", response_class=PlainTextResponse)
def run_export(token: str, name: str):
    if name not in _EXPORTS:
        raise HTTPException(404, "no such export")
    column, label = _EXPORTS[name]
    with _conn() as c:
        row = c.execute(
            f"SELECT {column} FROM runs WHERE run_token = ?", (token,)  # noqa: S608
        ).fetchone()
    if row is None:
        raise HTTPException(404, "run not found")
    if not row[column]:
        raise HTTPException(
            404, f"this run has no {label} export (that export belongs to the "
                 "line-item settlement kind, not the batch-level one)")
    return PlainTextResponse(
        row[column], media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=settleflow-{label}.csv"},
    )


# ---------------------------------------------------------------------------
# Lead capture — the export click is the highest-intent moment on the site
# ---------------------------------------------------------------------------

def _smtp_configured() -> bool:
    return all(os.environ.get(k) for k in
               ("SETTLEFLOW_SMTP_HOST", "SETTLEFLOW_SMTP_USER", "SETTLEFLOW_SMTP_PASS"))


def _send_pack_email(to: str, token: str, exports: list[str]) -> bool:
    """Email the workpaper links. Returns True only on a real send.

    Same rule as S1's lead store: never simulate a send. If SMTP is not
    configured this returns False, the lead is still stored, and the page says so
    in as many words rather than implying an email went out.
    """
    if not _smtp_configured():
        return False
    base = os.environ.get("SETTLEFLOW_PUBLIC_URL", "https://settleflow.atlasnex.com").rstrip("/")
    body = "\n".join(["Your reconciliation workpapers:", ""] +
                     [f"- {base}/r/{token}/export/{name}" for name in exports] +
                     ["", f"These links are private — anyone who has them can read the "
                      f"run. They stop working after {RETENTION_DAYS} days.",
                      "", "— SettleFlow"])
    msg = MIMEText(body)
    msg["Subject"] = "Your SettleFlow workpaper pack"
    msg["From"] = os.environ.get("SETTLEFLOW_SMTP_FROM", os.environ["SETTLEFLOW_SMTP_USER"])
    msg["To"] = to
    try:
        with smtplib.SMTP(
            os.environ["SETTLEFLOW_SMTP_HOST"],
            int(os.environ.get("SETTLEFLOW_SMTP_PORT", "587")),
            timeout=20,
        ) as smtp:
            smtp.starttls()
            smtp.login(os.environ["SETTLEFLOW_SMTP_USER"], os.environ["SETTLEFLOW_SMTP_PASS"])
            smtp.send_message(msg)
        return True
    except Exception as exc:
        print(f"[settleflow] lead email failed: {type(exc).__name__}: {exc}",
              file=sys.stderr, flush=True)
        return False


@app.post("/r/{token}/notify")
def notify(request: Request, token: str, email: str = Form("")):
    # Throttle before anything else, namespaced so notify traffic and reconcile
    # traffic do not consume each other's per-identity budget. Without this the
    # route was the service's only unthrottled write: 10,000 leads rows in 25s,
    # token free from the unauthenticated /reconcile (vuln-0001).
    if not _rate_ok(f"notify:{_client_ip(request)}"):
        raise HTTPException(429, "Too many requests from this connection.")
    with _conn() as c:
        row = c.execute("SELECT tally_csv, gst_csv, tds1035_csv FROM runs "
                        "WHERE run_token = ?", (token,)).fetchone()
    if row is None:
        raise HTTPException(404, "run not found")

    address = valid_email(email)
    if address is None:
        return RedirectResponse(f"/r/{token}?error=email#pack", status_code=303)

    exports = [name for name, (col, _l) in _EXPORTS.items() if row[col]]
    delivered = _send_pack_email(address, token, exports)
    with _conn() as c:
        c.execute(
            "INSERT INTO leads (created_at, email, run_token, delivered) "
            "VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), address, token, 1 if delivered else 0),
        )
    return RedirectResponse(f"/r/{token}?saved=1#pack", status_code=303)
