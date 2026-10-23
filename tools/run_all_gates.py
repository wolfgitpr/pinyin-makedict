#!/usr/bin/env python3
"""Run this repository's gates in one command, with one verdict line per gate.

Why this exists: the gates already exist, but they live in different places -- a pytest suite, a PowerShell drift
script that needs a sibling checkout, and a manifest that is only an expectation until something regenerates the
tables and compares. A release needs "did all of it pass, in this tree, now" in one answer, and CI needs the same
answer without a second, drifting copy of the rules.

WHAT IT DOES NOT DO: re-implement a comparison. Every gate below CALLS the existing instrument, so there is exactly
one authority per fact:

  * the eight tables' bytes       -> `MANIFEST.sha256`, checked by `test_manifest_matches_a_fresh_generation`
  * the dependency pins           -> `requirements.txt`, checked by `common.check_dependency_versions()`
  * cross-repository equivalence  -> `tools/check_drift.ps1` (PowerShell, needs a cpp-pinyin checkout)

Usage:
    python tools/run_all_gates.py [--list] [--cpp-root <path>]

Exit codes: 0 every gate passed (skips allowed, and each skip says why), 1 at least one gate failed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", *args, "-q"]


# name, argv (None = decided at run time), what it proves
GATES: list[tuple[str, list[str] | None, str]] = [
    (
        "delivery",
        _pytest("tests/test_data_gates.py::test_manifest_matches_a_fresh_generation"),
        "the eight tables regenerate byte-for-byte to what MANIFEST.sha256 says",
    ),
    (
        "pins",
        _pytest("tests/test_data_gates.py", "-k", "pinned"),
        "the three data dependencies are installed at their pinned versions",
    ),
    (
        "suite",
        _pytest("tests"),
        "the whole gate suite: contract, canon reading, ordering, error model, manifest",
    ),
    (
        "drift",
        None,
        "the generated tables still equal what the consumer repository ships (needs --cpp-root)",
    ),
]


def _run(argv: list[str]) -> tuple[int, list[str]]:
    completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    output = (completed.stdout + completed.stderr).strip().splitlines()
    return completed.returncode, output


def _drift_gate(cpp_root: Path | None) -> tuple[str, str]:
    """SKIP, not FAIL, when the sibling checkout or PowerShell is absent -- and say which."""
    script = ROOT / "tools" / "check_drift.ps1"
    if not script.is_file():
        return "skipped", "tools/check_drift.ps1 is not in this tree"
    if cpp_root is None:
        return "skipped", "no --cpp-root given, so there is nothing to compare against"
    # `data/dialects` is where the consumer keeps the tables since 2026-10; `data/dict` is the older name the
    # drift script still tolerates. Checking for either -- and for the CMakeLists that makes a checkout a
    # checkout -- is the shallowest test that still refuses an unrelated directory.
    if not (cpp_root / "CMakeLists.txt").is_file():
        return "skipped", f"{cpp_root} does not look like a cpp-pinyin checkout (no CMakeLists.txt)"
    if not any((cpp_root / "data" / name).is_dir() for name in ("dialects", "dict")):
        return "skipped", f"{cpp_root} has no data/dialects and no data/dict"
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell is None:
        return "skipped", "no PowerShell on PATH, and the drift script is a .ps1"
    code, output = _run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
         "-CppPinyinRoot", str(cpp_root)]
    )
    if code != 0:
        tail = " | ".join(line for line in output[-3:] if line.strip())
        return "failed", tail[:300]
    return "passed", "the two repositories still agree"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cpp-root", type=Path, default=None,
                        help="a cpp-pinyin checkout to compare against (enables the drift gate)")
    parser.add_argument("--list", action="store_true", help="print the gates and exit")
    args = parser.parse_args(argv)

    if args.list:
        for name, _argv, what in GATES:
            print(f"  {name:<10} {what}")
        return 0

    failures: list[str] = []
    skipped: list[tuple[str, str]] = []

    for name, gate_argv, what in GATES:
        if name == "drift":
            state, detail = _drift_gate(args.cpp_root)
            if state == "skipped":
                print(f"  SKIP  {name:<10} {detail}")
                skipped.append((name, detail))
                continue
            if state == "failed":
                print(f"  FAIL  {name:<10} {detail}")
                failures.append(name)
                continue
            print(f"  ok    {name:<10} {detail}")
            continue

        assert gate_argv is not None
        code, output = _run(gate_argv)
        verdict = next((line for line in reversed(output) if line.strip()), "")
        if code == 0:
            print(f"  ok    {name:<10} {verdict[:120]}")
        else:
            print(f"  FAIL  {name:<10} {verdict[:120]}")
            # Never swallow the reason: a failing gate that reports only "failed" costs a whole round.
            for line in output[-25:]:
                print(f"          {line[:160]}")
            failures.append(name)

    print()
    if failures:
        print(f"RESULT: {len(failures)} gate(s) failed: {', '.join(failures)}")
        return 1
    print(f"RESULT: {len(GATES) - len(skipped)} gate(s) passed"
          + (f", {len(skipped)} skipped (each says why above)" if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
