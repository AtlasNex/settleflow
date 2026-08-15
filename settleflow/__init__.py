"""settleflow: open-source UPI/NPCI settlement reconciliation for India."""

from .models import (
    BatchRecon,
    Match,
    MatchStatus,
    OrderMatch,
    OrderReconResult,
    ReconLine,
    ReconResult,
    Settlement,
    Txn,
    normalize_utr,
)
from .matching import group_batches, match, match_orders, match_settlements, normalize_ref
from .parsers import (
    RAZORPAY_RECON_KEYS,
    RAZORPAY_RECON_REQUIRED,
    load_csv,
    load_razorpay_recon_json,
    load_recon_csv,
    parse_amount,
    parse_date,
    parse_razorpay_recon,
    parse_razorpay_settlements,
)
from .exports import (
    TDS_1035_CODE,
    TDS_1035_RATE,
    export_gst_worksheet,
    export_tally_csv,
    export_tds_1035,
)
from .exceptions import Exception, build_llm_prompt, classify
from .schemas import (
    BANK_STATEMENT_MAPS,
    RECON_CSV_MAPS,
    SETTLEMENT_CSV_MAPS,
    ColumnMap,
    ReconColumnMap,
    load_bank_statement,
    load_settlement_csv,
    load_vendor_recon_csv,
)

__version__ = "0.3.0"

__all__ = [
    "BatchRecon",
    "Match",
    "MatchStatus",
    "OrderMatch",
    "OrderReconResult",
    "ReconLine",
    "ReconResult",
    "Settlement",
    "Txn",
    "normalize_utr",
    "normalize_ref",
    "group_batches",
    "match",
    "match_orders",
    "match_settlements",
    "RAZORPAY_RECON_KEYS",
    "RAZORPAY_RECON_REQUIRED",
    "load_csv",
    "load_razorpay_recon_json",
    "load_recon_csv",
    "parse_amount",
    "parse_date",
    "parse_razorpay_recon",
    "parse_razorpay_settlements",
    "TDS_1035_CODE",
    "TDS_1035_RATE",
    "export_gst_worksheet",
    "export_tally_csv",
    "export_tds_1035",
    "Exception",
    "build_llm_prompt",
    "classify",
    "BANK_STATEMENT_MAPS",
    "RECON_CSV_MAPS",
    "SETTLEMENT_CSV_MAPS",
    "ColumnMap",
    "ReconColumnMap",
    "load_bank_statement",
    "load_settlement_csv",
    "load_vendor_recon_csv",
]
