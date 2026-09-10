"""Stdlib-only helpers for the thin SaaS layer.

Kept out of ``app.py`` on purpose: the self-check (`tests/test_matching.py`)
exercises these with zero third-party imports, so the logic that decides *what a
user's uploaded file actually is* stays testable on a machine where the `[saas]`
extra was never installed (CONSTRAINTS.md #6).

Nothing here talks to FastAPI, the database, or the network.
"""
from __future__ import annotations

import html as _html
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
