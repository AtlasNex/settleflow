"""SettleFlow thin SaaS — Phase 4.

The paid layer on top of the open-core library. Reconciles an uploaded
settlement file against an uploaded bank-statement CSV, persists the run,
surfaces an exception queue, and exports accountant-facing CSVs (Tally,
GST worksheet, TDS code-1035).

Deliberately thin: no ORM (stdlib sqlite3), no auth, no user model. Those are
later-stage SaaS concerns; this is the working reconcile-expose-export loop
the open-core model monetizes.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from settleflow import (  # noqa: E402
    Txn,
    classify,
    export_gst_worksheet,
    export_tally_csv,
    export_tds_1035,
    group_batches,
    load_csv,
    match,
    match_settlements,
    parse_razorpay_recon,
    parse_razorpay_settlements,
)

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "settleflow.db"
TEMPLATES = Jinja2Templates(directory=str(BASE / "templates"))

app = FastAPI(title="SettleFlow", version="0.3.0")


# ---------------------------------------------------------------------------
# Storage: one row per run. Files, result, exceptions, and generated CSVs are
# stored as text so exports are served verbatim (no lossy reconstruction).
# ---------------------------------------------------------------------------

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
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


_init_db()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return TEMPLATES.TemplateResponse(request, "index.html", {"title": "SettleFlow"})


@app.get("/runs", response_class=HTMLResponse)
def runs(request: Request):
    with _conn() as c:
        rows = c.execute(
            "SELECT id, created_at, kind, result_json FROM runs ORDER BY id DESC LIMIT 50"
        ).fetchall()
    return TEMPLATES.TemplateResponse(request, "runs.html", {"runs": rows})


@app.post("/reconcile")
async def reconcile(
    settlement_file: UploadFile = File(...),
    bank_file: UploadFile = File(...),
    settlement_kind: str = Form("razorpay_settlements"),
    bank_utr_col: str = Form("utr"),
    bank_amount_col: str = Form("amount"),
    bank_date_col: str = Form("date"),
):
    """Run level-1 reconciliation: settlement file vs bank statement CSV."""
    settlement_raw = await settlement_file.read()
    bank_raw = await bank_file.read()

    # Parse the settlement side by its declared kind.
    settlements, recon_lines = None, None
    if settlement_kind == "razorpay_settlements":
        settlements = parse_razorpay_settlements(json.loads(settlement_raw))
    elif settlement_kind == "razorpay_recon":
        recon_lines = parse_razorpay_recon(json.loads(settlement_raw))
    else:
        raise HTTPException(400, f"unknown settlement_kind {settlement_kind!r}")

    # Parse the bank side from the uploaded CSV with the explicit column map.
    bank_path = BASE / "upload_bank.csv"
    bank_path.write_bytes(bank_raw)
    try:
        bank = load_csv(bank_path, bank_utr_col, bank_amount_col, bank_date_col)
    finally:
        bank_path.unlink(missing_ok=True)

    # Reconcile. Recon lines group into batches and match at batch level;
    # settlement entities match directly.
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
    else:
        result = match_settlements(settlements, bank)

    tally_csv = export_tally_csv(result)
    exceptions = classify(result)

    def _result_json():
        return json.dumps({
            "matched": [{"settlement": m.settlement.ref, "bank": m.bank.utr,
                         "amount": str(m.settlement.amount), "status": m.status.value}
                        for m in result.matched],
            "settlement_only": [{"ref": t.ref, "amount": str(t.amount)} for t in result.settlement_only],
            "bank_only": [{"utr": t.utr, "amount": str(t.amount)} for t in result.bank_only],
            "matched_total": str(result.matched_total),
            "unmatched_settlement_total": str(result.unmatched_settlement_total),
            "unmatched_bank_total": str(result.unmatched_bank_total),
        })

    def _exc_json():
        return json.dumps([{"category": e.category, "amount": str(e.amount),
                            "detail": e.detail, "utr": e.utr, "ref": e.ref}
                           for e in exceptions])

    with _conn() as c:
        cur = c.execute(
            "INSERT INTO runs (created_at, kind, result_json, exceptions_json, "
            "tally_csv, gst_csv, tds1035_csv) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), settlement_kind,
             _result_json(), _exc_json(), tally_csv, gst_csv, tds1035_csv),
        )
        run_id = cur.lastrowid

    return {
        "run_id": run_id,
        "matched": len(result.matched),
        "settlement_only": len(result.settlement_only),
        "bank_only": len(result.bank_only),
        "matched_total": str(result.matched_total),
        "exceptions": json.loads(_exc_json()),
        "exports": ["/runs/%d/export/tally.csv" % run_id] +
                   (["/runs/%d/export/gst.csv" % run_id,
                     "/runs/%d/export/tds1035.csv" % run_id] if recon_lines else []),
    }


@app.get("/runs/{run_id}/exceptions", response_class=PlainTextResponse)
def run_exceptions(run_id: int):
    with _conn() as c:
        row = c.execute("SELECT exceptions_json FROM runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "run not found")
    return PlainTextResponse(row["exceptions_json"], media_type="application/json")


def _export_col(run_id: int, column: str, name: str) -> PlainTextResponse:
    with _conn() as c:
        row = c.execute(f"SELECT {column} FROM runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "run not found")
    if not row[column]:
        raise HTTPException(404, f"run {run_id} has no {name} export (wrong settlement kind)")
    return PlainTextResponse(row[column], media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={name}.csv"})


@app.get("/runs/{run_id}/export/tally.csv", response_class=PlainTextResponse)
def run_tally_export(run_id: int):
    return _export_col(run_id, "tally_csv", "tally")


@app.get("/runs/{run_id}/export/gst.csv", response_class=PlainTextResponse)
def run_gst_export(run_id: int):
    return _export_col(run_id, "gst_csv", "gst")


@app.get("/runs/{run_id}/export/tds1035.csv", response_class=PlainTextResponse)
def run_tds1035_export(run_id: int):
    return _export_col(run_id, "tds1035_csv", "tds1035")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.3.0"}
