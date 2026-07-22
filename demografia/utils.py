from __future__ import annotations

from collections.abc import Callable
from multiprocessing import get_context
from multiprocessing.queues import Queue
from pathlib import Path
from typing import Iterable, TypeVar

import pandas as pd

T = TypeVar("T")


def chunks(values: list[T], size: int) -> Iterable[list[T]]:
    """Yield fixed-size chunks while preserving input order."""
    for start in range(0, len(values), size):
        yield values[start : start + size]


def save_table(frame: pd.DataFrame, path: Path) -> Path:
    """Write a table in both Parquet and CSV formats.

    Parquet is the canonical analytical format. CSV is emitted alongside it so
    the same output can be inspected quickly in spreadsheet tools or plain text.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    frame.to_csv(path.with_suffix(".csv"), index=False)
    return path


def save_csv(frame: pd.DataFrame, path: Path) -> Path:
    """Write a CSV file after creating the target directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def print_outputs(outputs: dict[str, Path]) -> None:
    """Print output labels and paths in deterministic order."""
    for name, path in sorted(outputs.items()):
        print(f"{name}: {path}")


def check_call(name: str, call: Callable[[], object]) -> dict[str, object]:
    """Execute a check function and normalize success or failure metadata."""
    try:
        value = call()
        records = len(value) if hasattr(value, "__len__") else None
        return {"source": name, "status": "ok", "records": records, "message": ""}
    except Exception as exc:
        return {
            "source": name,
            "status": "error",
            "records": None,
            "message": f"{type(exc).__name__}: {exc}",
        }


def _check_call_worker(name: str, call: Callable[[], object], queue: Queue) -> None:
    queue.put(check_call(name, call))


def check_call_in_process(
    name: str,
    call: Callable[[], object],
    timeout: int,
) -> dict[str, object]:
    """Execute a check in a child process and enforce a hard timeout."""
    context = get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_check_call_worker, args=(name, call, queue))
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join()
        return {
            "source": name,
            "status": "timeout",
            "records": None,
            "message": f"Timeout dopo {timeout} secondi",
        }
    if not queue.empty():
        return queue.get()
    return {
        "source": name,
        "status": "error",
        "records": None,
        "message": f"Processo terminato con codice {process.exitcode}",
    }
