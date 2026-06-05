#!/usr/bin/env python3
"""Run offline Simple Analysis TaskBench cases and write paper-facing artifacts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
DEFAULT_CACHE_ROOT = REPO_ROOT / "outputs" / ".simple_analysis_cache"
DEFAULT_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(DEFAULT_CACHE_ROOT / "matplotlib")
os.environ["XDG_CACHE_HOME"] = str(DEFAULT_CACHE_ROOT / "xdg")
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

with redirect_stdout(sys.stderr):
    from atmoschem_agent.bench.simple_analysis import (  # noqa: E402
        load_simple_analysis_registry,
        render_simple_analysis_summary,
        run_simple_analysis_benchmarks,
    )


def _failure_payload(exc: Exception) -> dict[str, Any]:
    return {
        "status": "fail",
        "errors": [f"{type(exc).__name__}: {exc}"],
        "case_results": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the offline Simple Analysis TaskBench without WRF-Chem, Tianhe, "
            "SSH, remote postprocessing, or large NetCDF inputs."
        )
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="Optional path to a simple-analysis benchmark registry YAML file.",
    )
    parser.add_argument(
        "--task",
        dest="tasks",
        action="append",
        default=None,
        help="Task family id to run, such as SA-01. May be repeated.",
    )
    parser.add_argument(
        "--split",
        choices=("all", "dev", "heldout"),
        default="all",
        help="Run all cases, only development cases, or only held-out cases.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for JSON scores, Markdown reports, PNG figures, and summary artifacts.",
    )
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="Write JSON score artifacts but skip Markdown reports and PNG figures.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full machine-readable suite report as JSON.",
    )
    args = parser.parse_args()

    try:
        registry = load_simple_analysis_registry(args.registry)
        report = run_simple_analysis_benchmarks(
            registry,
            task_family_ids=args.tasks,
            split=args.split,
            output_dir=args.output_dir,
            write_artifacts=not args.score_only,
        )
    except Exception as exc:  # pragma: no cover - CLI boundary
        report = _failure_payload(exc)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(render_simple_analysis_summary(report), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_simple_analysis_summary(report))
    return 0 if report.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
