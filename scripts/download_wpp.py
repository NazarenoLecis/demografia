from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demografia.config import INPUT_DIR
from demografia.wpp_auto import download_wpp_age_sex


# Configurazione per VS Code.
TARGET_DIR = INPUT_DIR / "wpp"
URL: str | None = None
REFRESH = False


def main(target_dir: Path = TARGET_DIR, url: str | None = URL, refresh: bool = REFRESH) -> Path:
    """Download the official WPP age-by-sex file used for OECD extra-EU countries."""
    return download_wpp_age_sex(target_dir, refresh=refresh, url=url)


if __name__ == "__main__":
    print(main())
