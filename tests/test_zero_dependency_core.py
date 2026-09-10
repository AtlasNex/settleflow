#!/usr/bin/env python3
"""Assert the core library pulls in nothing outside the standard library.

Run this in a CLEAN interpreter — no pip installs, no extras. CI does exactly that.

    python tests/test_zero_dependency_core.py

CONSTRAINTS.md #6 is the rule ("zero runtime dependencies; any new dependency
requires a DECISIONS.md entry"), and until now nothing enforced it. A stray
`import requests` in settleflow/ would ship silently.

The check is a DIFF, not an absolute audit of sys.modules. That distinction
matters: CPython bootstraps site-packages hooks at startup (on Windows, pywin32
inserts itself before user code runs), so asserting "no third-party module is
loaded" fails on a perfectly valid developer machine and trains people to ignore
the check. What we actually claim is narrower and true: *settleflow* does not drag
anything in.
"""
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Snapshot BEFORE importing settleflow — anything already loaded is the
# interpreter's own business, not ours.
_BEFORE = set(sys.modules)


def main() -> int:
    import settleflow                                # noqa: F401
    import settleflow.exceptions                     # noqa: F401
    import settleflow.exports                        # noqa: F401
    import settleflow.matching                       # noqa: F401
    import settleflow.models                         # noqa: F401
    import settleflow.ocr                            # noqa: F401
    import settleflow.parsers                        # noqa: F401
    import settleflow.pdf                            # noqa: F401
    import settleflow.schemas                        # noqa: F401

    # ...and it must actually reconcile, not merely import.
    from settleflow import Txn, match

    result = match(
        [Txn("123456789012", Decimal("100.00"), date(2026, 8, 15))],
        [Txn("1234 5678 9012", Decimal("100.00"), date(2026, 8, 16))],
    )
    assert len(result.matched) == 1, f"core matching broke: {result.matched}"

    new_roots = {
        name.split(".")[0]
        for name in set(sys.modules) - _BEFORE
        if not name.startswith("_")
    }
    allowed = set(sys.stdlib_module_names) | {
        "settleflow", "saas", "tests", "sitecustomize", "usercustomize",
    }
    third_party = sorted(m for m in new_roots if m not in allowed)

    if third_party:
        print(f"FAIL  the core imported non-stdlib modules: {third_party}")
        print("      Add a DECISIONS.md entry, or drop the import "
              "(CONSTRAINTS.md #6).")
        return 1

    print(f"PASS  zero-dependency core verified on python "
          f"{sys.version.split()[0]} ({len(new_roots)} modules loaded, all stdlib)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
