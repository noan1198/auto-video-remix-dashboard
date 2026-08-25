#!/usr/bin/env python3
"""Prepare the private Python runtime used by the standalone shot splitter."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import venv
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = SKILL_ROOT / ".splitter-runtime"
REQUIREMENTS = SKILL_ROOT / "requirements-splitter.txt"


def runtime_python(runtime: Path) -> Path:
    if sys.platform == "win32":
        return runtime / "Scripts" / "python.exe"
    return runtime / "bin" / "python"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    args = parser.parse_args()

    runtime = args.runtime.expanduser().resolve()
    python = runtime_python(runtime)
    if not python.is_file():
        runtime.parent.mkdir(parents=True, exist_ok=True)
        venv.EnvBuilder(with_pip=True, clear=False).create(runtime)

    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "-r",
            str(REQUIREMENTS),
        ],
        check=True,
    )
    print(json.dumps({"ok": True, "python": str(python)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
