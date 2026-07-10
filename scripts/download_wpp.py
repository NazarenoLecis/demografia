from __future__ import annotations

import argparse
from pathlib import Path

from demografia.config import INPUT_DIR
from demografia.wpp_auto import download_wpp_age_sex


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scarica il file ufficiale WPP per età e sesso")
    parser.add_argument("--target-dir", type=Path, default=INPUT_DIR / "wpp")
    parser.add_argument("--url", help="URL ufficiale esplicito; omesso usa la discovery")
    parser.add_argument("--refresh", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    path = download_wpp_age_sex(args.target_dir, refresh=args.refresh, url=args.url)
    print(path)
