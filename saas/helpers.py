"""Stdlib-only helpers for the thin SaaS layer.

Kept out of ``app.py`` on purpose: the self-check (`tests/test_matching.py`)
exercises these with zero third-party imports, so the logic that decides *what a
user's uploaded file actually is* stays testable on a machine where the `[saas]`
extra was never installed (CONSTRAINTS.md #6).

Nothing here talks to FastAPI, the database, or the network.
"""
from __future__ import annotations

import html as _html
import ipaddress
import re

# ---------------------------------------------------------------------------
# Input decoding
# ---------------------------------------------------------------------------

#: Ordered candidate encodings for an uploaded bank file. Indian bank exports are
#: not uniformly UTF-8: cp1252 (accented merchant names, non-ASCII punctuation) is
#: common, and some exports write a bare 0x80 where they mean the rupee sign.
#: utf-8-sig first because a BOM is the one case where a wrong guess silently
#: corrupts the *first column name* — the worst failure mode here, since it makes
#: column detection fail for a file that was perfectly fine.
_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


def decode_text(raw: bytes) -> str:
    """Decode uploaded bytes to text without ever raising.

    latin-1 is the guaranteed fallback (it maps all 256 byte values), so this
    cannot fail. A file decoded by the fallback still goes on to fail loudly at
    the column check with a message naming the headers found — which is far more
    actionable than a UnicodeDecodeError traceback.
    """
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


# ---------------------------------------------------------------------------
# Request identity and size
# ---------------------------------------------------------------------------

#: The header whose value is the client's real address. Cloudflare's tunnel sets it
#: at the edge and the origin is reachable only through that tunnel, so it cannot be
#: forged by a caller.
TRUSTED_CLIENT_IP_HEADER = "cf-connecting-ip"

#: The bucket for a request that carries no trustworthy identity. One shared bucket,
#: not one per request: the alternative is an attacker minting a new bucket with
#: every request, which is the bug this replaced.
UNIDENTIFIED_CLIENT = "unidentified"


def _header(headers, name: str) -> str | None:
    """Case-insensitive header read that works for a dict or a Starlette Headers."""
    try:
        value = headers.get(name)
    except AttributeError:
        value = None
    if value is not None:
        return value
    lowered = name.lower()
    items = headers.items() if hasattr(headers, "items") else ()
    for key, value in items:
        if key.lower() == lowered:
            return value
    return None


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _is_intermediary_peer(peer: str | None) -> bool:
    """Whether `peer` looks like a proxy/ intermediary rather than the end client.

    Loopback (cloudflared on the host, the local dev server) and the RFC1918/link-
    local ranges (the docker bridge gateway, which is the container-side peer of
    EVERY connection through the published port, tunnel or not) both mean "the
    address the request arrived from is an intermediary, not the caller".

    Note: Python's `is_private` also covers the reserved TEST-NET ranges
    (203.0.113.0/24 etc.), which are documentation addresses that never appear as
    a real TCP peer — a socket peer is either genuinely routable or internal.
    Tests for the public-peer branch must use a real public address (8.8.8.8).
    """
    if not peer:
        return False
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return addr.is_loopback or addr.is_private


def pick_client_ip(
    headers,
    peer: str | None = None,
    trusted_header: str = TRUSTED_CLIENT_IP_HEADER,
) -> str:
    """The identity to rate-limit on. Never trusts caller-controlled input.

    Two sources look reasonable and are both caller-controlled in practice:

    * `X-Forwarded-For` is written by the caller — trusting its first hop let 70
      requests claiming 70 addresses each open a fresh bucket (verified: 70
      accepted, 0 rejected), so the per-hour limit simply vanished.
    * the socket peer is not safe on a bare host either. Uvicorn rewrites
      `scope["client"]` from X-Forwarded-For when the connection arrives from a
      trusted proxy address, and the Cloudflare tunnel connects from loopback — so
      an XFF header still changed the bucket (verified: 10 requests with rotating
      XFF after the bucket was already exhausted were all accepted).

    The rule, per D-41's probe (the edge 403s any caller-supplied
    CF-Connecting-IP, so through the tunnel the header is edge-set):

    * peer is an intermediary (loopback, or the docker bridge gateway which is the
      container-side peer of every published-port connection): the trusted header
      is the ONLY per-client identity — it must parse as an address so a junk
      value cannot mint unlimited buckets, and it is canonicalized via
      `ipaddress.ip_address` so the alternate textual spellings of one IPv6
      address (`::1`, `0::1`, `0000:...:0001`) share one bucket instead of one each.
    * peer is public: the request reached the origin WITHOUT an intermediary, so
      the caller chose whatever headers it carries and is keyed on its own peer
      address instead — a value it cannot mint away per request.
    * no peer (direct helpers callers, the self-check): header-if-valid else the
      ONE shared unidentified bucket — conservative and fail-safe.

    ponytail: in-memory windows, per-process; correct for the single-container
    deployment. Multi-worker → move the counters to sqlite before scaling out.
    """
    if peer is not None and not _is_intermediary_peer(peer):
        return str(ipaddress.ip_address(peer)) if _is_ip(peer) else UNIDENTIFIED_CLIENT
    trusted = _header(headers, trusted_header)
    if trusted:
        candidate = trusted.split(",")[0].strip()
        if candidate and _is_ip(candidate):
            # Canonicalize so one address has one bucket regardless of spelling.
            return str(ipaddress.ip_address(candidate))
    return UNIDENTIFIED_CLIENT


def max_request_bytes(max_upload_bytes: int) -> int:
    """Largest whole request body the service will read.

    `MAX_UPLOAD_BYTES` caps the two FILES the app parses, but not the request: the
    multipart parser bounds each form FIELD at 1MB while file parts spool with no
    size check, so extra parts rode through untouched — a 210MB request carrying one
    unnamed part was accepted. This is the ceiling for everything, with slack for
    multipart framing and the form fields.
    """
    return max_upload_bytes * 2 + 64 * 1024


def request_too_large(content_length, limit: int) -> bool:
    """Whether a DECLARED body size exceeds the limit.

    A missing or unparseable Content-Length is not "large": a chunked request
    declares nothing, and refusing on a header we cannot read would reject
    legitimate uploads. The streaming guard covers that case instead.
    """
    if content_length is None:
        return False
    try:
        declared = int(content_length)
    except (TypeError, ValueError):
        return False
    return declared > limit


# ---------------------------------------------------------------------------
# Bank-CSV column detection
# ---------------------------------------------------------------------------

#: Header vocabulary per role, derived from the real statements already parsed by
#: `settleflow/schemas.py` (HDFC/SBI/ICICI/Axis/Kotak/PNB/DBS) plus the obvious
#: synonyms. This is a *suggestion* engine: the caller must still show the user
#: what was chosen and let them override it, because a wrong column mapping
#: produces a confident, wrong reconciliation.
_COL_PATTERNS: dict[str, tuple[str, ...]] = {
    "utr": (
        "utr", "utr no", "utr_no", "bank utr", "reference", "reference no",
        "ref no", "ref_no", "cheque no", "chq no", "transaction id", "txn id",
        "transaction reference", "instrument id",
    ),
    "amount": (
        "amount", "credit", "credit amount", "cr", "cr amount", "deposit",
        "deposit amount", "net amount", "credit(inr)", "withdrawal amt",
    ),
    "date": (
        "date", "value date", "value_date", "txn date", "transaction date",
        "posting date", "value dt", "tran date",
    ),
}

#: Substring matching is only trusted for patterns at least this long. Short
#: tokens ("cr", "date") appear inside unrelated headers ("description",
#: "updated_at"), and a false positive here is invisible to the user.
_MIN_SUBSTRING_LEN = 4


def guess_columns(header: list[str]) -> dict[str, str | None]:
    """Map a bank CSV's header cells to the three roles the loader needs.

    Returns the ORIGINAL header cell for each role (case and spacing preserved,
    because the loader looks the column up by its literal name) or ``None`` when
    nothing matched — so the caller asks the user rather than guessing.

    Exact matches always beat substring matches, so a sheet containing both
    "Value Date" and "Date" resolves deterministically instead of by dict order.
    """
    cells = [(h, h.strip().lower()) for h in header if isinstance(h, str) and h.strip()]
    found: dict[str, str | None] = {}
    for role, patterns in _COL_PATTERNS.items():
        pick = None
        for pat in patterns:                       # pass 1: exact
            for original, low in cells:
                if low == pat:
                    pick = original
                    break
            if pick:
                break
        if pick is None:                           # pass 2: safe substring
            for pat in patterns:
                if len(pat) < _MIN_SUBSTRING_LEN:
                    continue
                for original, low in cells:
                    if pat in low:
                        pick = original
                        break
                if pick:
                    break
        found[role] = pick
    return found


# ---------------------------------------------------------------------------
# Lead capture
# ---------------------------------------------------------------------------

#: RFC 5321 practical maximum, same bound S1's lead store uses.
MAX_EMAIL_LEN = 254
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_email(value: str) -> str | None:
    """Return a canonical lowercase address, or None if it is not one.

    Deliberately strict at the trust boundary: we only store something that is
    actually an email. No trimming tricks, no unicode normalisation.
    """
    candidate = (value or "").strip().lower()
    if not candidate or len(candidate) > MAX_EMAIL_LEN:
        return None
    return candidate if _EMAIL_RE.match(candidate) else None


# ---------------------------------------------------------------------------
# Minimal markdown -> HTML
# ---------------------------------------------------------------------------

#: The subset the legal drafts and the static pages use: h1-h3, unordered and
#: ordered lists, fenced-free inline code, bold, links, horizontal rules, and
#: blank-line-separated paragraphs. Anything richer gets a new dependency, which
#: this repo does not take without a DECISIONS.md entry (CONSTRAINTS.md #6).
def md_to_html(text: str) -> str:
    """Render the small markdown subset above to HTML.

    Input is escaped FIRST, so a document containing raw markup cannot inject it
    into a page. Only the constructs listed above are converted; everything else
    survives as its own escaped paragraph.
    """
    out: list[str] = []
    list_open: str | None = None

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            out.append(f"</{list_open}>")
            list_open = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            close_list()
            continue

        if stripped in ("---", "***", "___"):
            close_list()
            out.append("<hr>")
            continue

        heading = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading:
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            continue

        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet:
            if list_open != "ul":
                close_list()
                out.append("<ul>")
                list_open = "ul"
            out.append(f"<li>{_inline(bullet.group(1))}</li>")
            continue

        numbered = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if numbered:
            if list_open != "ol":
                close_list()
                out.append("<ol>")
                list_open = "ol"
            out.append(f"<li>{_inline(numbered.group(1))}</li>")
            continue

        close_list()
        out.append(f"<p>{_inline(stripped)}</p>")

    close_list()
    return "\n".join(out)


def _inline(text: str) -> str:
    """Escape, then apply the inline constructs (code, bold, links)."""
    escaped = _html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        r'<a href="\2" rel="noopener">\1</a>',
        escaped,
    )
    return escaped


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------

def human_bytes(n: int) -> str:
    """Render a byte count the way a person would say it."""
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
