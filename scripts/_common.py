"""Shared helpers for the scripts: makes `hri_sim` importable and prints a pass or fail table."""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class Checks:
    """Collects named checks, prints a table and returns an exit code."""

    def __init__(self, title: str):
        self.title = title
        self.rows = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.rows.append((bool(ok), name, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""), flush=True)
        return bool(ok)

    def report(self) -> int:
        failed = [r for r in self.rows if not r[0]]
        print(f"\n== {self.title}: {len(self.rows) - len(failed)} passed, {len(failed)} failed ==")
        for _, name, detail in failed:
            print(f"   FAILED: {name}  {detail}")
        return 1 if failed else 0
