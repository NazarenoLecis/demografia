from __future__ import annotations

import json
from functools import partial
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demografia.sources import inps, istat, rgs
from demografia.utils import check_call_in_process


SOURCE_TIMEOUT = 8
PROCESS_TIMEOUT = 12


def check_istat_dataflows(timeout: int) -> object:
    return istat.dataflows(timeout=timeout)


def check_inps_status(timeout: int) -> object:
    return inps.status(timeout=timeout)


def check_rgs_search(timeout: int) -> object:
    return rgs.package_search("pensioni", rows=1, timeout=timeout)


def main(
    source_timeout: int = SOURCE_TIMEOUT,
    process_timeout: int = PROCESS_TIMEOUT,
) -> list[dict[str, object]]:
    """Check catalog/API availability for ISTAT, INPS, and RGS/OpenBDAP."""
    checks = (
        ("ISTAT SDMX", check_istat_dataflows),
        ("INPS API", check_inps_status),
        ("RGS OpenBDAP", check_rgs_search),
    )
    return [
        check_call_in_process(name, partial(call, source_timeout), timeout=process_timeout)
        for name, call in checks
    ]


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if any(item["status"] == "error" for item in result):
        raise SystemExit(1)
