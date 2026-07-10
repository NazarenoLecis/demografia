from __future__ import annotations

import json

from demografia.sources.inps import InpsClient
from demografia.sources.istat import IstatClient
from demografia.sources.rgs import RgsClient


def check(name: str, function) -> dict[str, object]:
    try:
        value = function()
        size = len(value) if hasattr(value, "__len__") else None
        return {"source": name, "status": "ok", "records": size, "message": ""}
    except Exception as exc:
        return {
            "source": name,
            "status": "error",
            "records": None,
            "message": f"{type(exc).__name__}: {exc}",
        }


if __name__ == "__main__":
    checks = [
        check("ISTAT SDMX", lambda: IstatClient().dataflows()),
        check("INPS API", lambda: InpsClient().status()),
        check("RGS OpenBDAP", lambda: RgsClient().package_search("pensioni", rows=1)),
    ]
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    if any(item["status"] == "error" for item in checks):
        raise SystemExit(1)
