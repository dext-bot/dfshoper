"""Helper script to launch DFShoper without manual PYTHONPATH setup."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    runpy.run_module("dfshoper.app", run_name="__main__")


if __name__ == "__main__":
    main()
