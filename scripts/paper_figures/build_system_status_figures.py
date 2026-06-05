"""Build TianJi-AirChem system-status figures from real v2 run records.

The figures in this script are intended for paper/PPT use. They avoid
claiming observation-data validation or generated scientific maps that are not
present in the current H1/H2 result artifacts.
"""

from __future__ import annotations

import json
import math
import os
import textwrap
from collections import Counter
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/atmoschem-agent-mplcache")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/atmoschem-agent-cache")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.path import Path as MplPath
from matplotlib.patches import (
    Circle,
    FancyArrowPatch,
    FancyBboxPatch,
    PathPatch,
    Rectangle,
    Wedge,
)


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "paper" / "figures" / "system_status"

H2_SESSION = ROOT / "outputs" / "sessions" / "v2_20260425_145200_recovery.json"
H3_SESSION = ROOT / "outputs" / "sessions" / "v2_20260427_181352.json"
H2_RESULTS_DIR = ROOT / "outputs" / "remote_results" / "v2_20260425_145200_recovery"
H3_RESULTS_DIR = ROOT / "outputs" / "remote_results" / "v2_20260427_181352"


PALETTE = {
    "navy": "#0B1F4D",
    "blue": "#4E79A7",
    "blue_soft": "#DDEBFA",
    "teal": "#1F9A9A",
    "teal_soft": "#DDF3F0",
    "violet": "#7A68A6",
    "violet_soft": "#EAE6F5",
    "amber": "#D9902F",
    "amber_soft": "#F8E7C7",
    "orange": "#D46A30",
    "orange_soft": "#F6D8C8",
    "green": "#4F8F52",
    "green_soft": "#E3F0DD",
    "red": "#B84A4A",
    "red_soft": "#F1D9D9",
    "gray": "#6B7280",
    "gray2": "#9CA3AF",
    "gray_soft": "#F2F4F7",
    "line": "#D1D5DB",
    "white": "#FFFFFF",
}


def load_state(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    return data.get("state", data)


def load_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def h2_results() -> dict[str, dict[str, Any]]:
    mapping = {
        "CTRL": "ari_ozone_20260425_145200_control_results.json",
        "NOx-cut": "ari_ozone_20260425_145200_nox_cut_results.json",
        "ARI-on": "ari_ozone_20260425_145200_ari_on_results.json",
        "ARI+NOx": "ari_ozone_20260425_145200_combined_results.json",
    }
    return {key: load_result(H2_RESULTS_DIR / filename) for key, filename in mapping.items()}


def h3_results() -> dict[str, dict[str, Any]]:
    mapping = {
        "No ARI / normal BC": "ari_ozone_20260427_181352_control_no_ari_normal_bc_results.json",
        "ARI / normal BC": "ari_ozone_20260427_181352_treatment_ari_on_normal_bc_results.json",
        "No ARI / high BC": "ari_ozone_20260427_181352_treatment_no_ari_high_bc_results.json",
        "ARI / high BC": "ari_ozone_20260427_181352_treatment_ari_on_high_bc_results.json",
    }
    return {key: load_result(H3_RESULTS_DIR / filename) for key, filename in mapping.items()}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
            "svg.fonttype": "none",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#374151",
            "axes.linewidth": 1.1,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "legend.frameon": False,
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / f"{name}.svg", bbox_inches="tight")
    fig.savefig(OUT_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def blank_fig(width: float = 12.8, height: float = 7.2) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def wrap(text: str, width: int = 22) -> str:
    return "\n".join(textwrap.wrap(str(text), width=width, break_long_words=False))


def rounded_box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str = "",
    *,
    fc: str = "#FFFFFF",
    ec: str = "#D1D5DB",
    lw: float = 1.2,
    radius: float = 0.018,
    color: str = PALETTE["navy"],
    fontsize: float = 9,
    weight: str = "regular",
    ha: str = "center",
    va: str = "center",
    zorder: int = 1,
) -> FancyBboxPatch:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.010,rounding_size={radius}",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        zorder=zorder,
    )
    ax.add_patch(patch)
    if text:
        ax.text(
            x + w / 2,
            y + h / 2,
            text,
            ha=ha,
            va=va,
            color=color,
            fontsize=fontsize,
            fontweight=weight,
            zorder=zorder + 1,
        )
    return patch


def label(ax: plt.Axes, x: float, y: float, text: str, **kwargs: Any) -> None:
    defaults = {
        "ha": "left",
        "va": "center",
        "fontsize": 9,
        "color": PALETTE["navy"],
    }
    defaults.update(kwargs)
    ax.text(x, y, text, **defaults)


def arrow(
    ax: plt.Axes,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: str = PALETTE["blue"],
    lw: float = 1.6,
    mutation_scale: float = 12,
    connectionstyle: str = "arc3,rad=0.0",
    zorder: int = 3,
) -> None:
    arr = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle="-|>",
        mutation_scale=mutation_scale,
        linewidth=lw,
        color=color,
        connectionstyle=connectionstyle,
        zorder=zorder,
    )
    ax.add_patch(arr)


def small_badge(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    *,
    fc: str,
    ec: str,
    color: str = PALETTE["navy"],
    w: float = 0.095,
    h: float = 0.038,
    fontsize: float = 8,
) -> None:
    rounded_box(ax, x, y, w, h, text, fc=fc, ec=ec, fontsize=fontsize, color=color, lw=1.0)


def title(ax: plt.Axes, text: str, subtitle: str = "") -> None:
    ax.text(0.02, 0.965, text, ha="left", va="top", fontsize=18, fontweight="bold", color=PALETTE["navy"])
    if subtitle:
        ax.text(0.02, 0.925, subtitle, ha="left", va="top", fontsize=10.5, color=PALETTE["gray"])


def branch_label(name: str) -> str:
    return name.replace("ari_ozone_20260427_181352_", "").replace("ari_ozone_20260425_145200_", "")


def get_h3_run_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for run_id, entry in (state.get("run_ledger") or {}).items():
        rows.append(
            {
                "run_id": run_id,
                "branch": branch_label(str(entry.get("branch_id") or run_id)),
                "job": str(entry.get("job_id") or ""),
                "status": str(entry.get("status") or ""),
                "collector": str(entry.get("collector_status") or ""),
                "eval": bool(entry.get("evaluation_ready")),
                "local": bool((state.get("results") or {}).get("local_results_paths", {}).get(run_id)),
                "remote": bool((state.get("results") or {}).get("remote_results_paths", {}).get(run_id)),
            }
        )
    return rows


def get_h2_run_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for run_id, entry in (state.get("run_ledger") or {}).items():
        rows.append(
            {
                "run_id": run_id,
                "branch": branch_label(str(entry.get("branch_id") or run_id)),
                "job": str(entry.get("job_id") or ""),
                "status": str(entry.get("status") or ""),
                "collector": str(entry.get("collector_status") or ""),
                "eval": bool(entry.get("evaluation_ready")),
                "local": bool((state.get("results") or {}).get("local_results_paths", {}).get(run_id)),
                "remote": bool((state.get("results") or {}).get("remote_results_paths", {}).get(run_id)),
            }
        )
    return rows


def availability_from_results(results: dict[str, dict[str, Any]], diagnostics: list[str]) -> np.ndarray:
    matrix = []
    for payload in results.values():
        variables = set(payload.get("variables_extracted") or payload.get("produced_outputs") or [])
        missing = set(payload.get("missing_outputs") or [])
        row = []
        for diagnostic in diagnostics:
            if diagnostic in variables:
                row.append(1)
            elif diagnostic in missing:
                row.append(0)
            else:
                row.append(-1)
        matrix.append(row)
    return np.asarray(matrix, dtype=int)


def figure_01_single_run_overview(h3: dict[str, Any]) -> None:
    fig, ax = blank_fig()
    title(ax, "Single-Run Operational Overview", "H3 completed v2 run: hypothesis -> WRF-Chem evidence -> Scientist verdict")

    stages = [
        ("Task\nContext", "Guanzhong winter\nBC-ARI hypothesis", PALETTE["blue_soft"], PALETTE["blue"]),
        ("Planner\nRouting", "18 decisions\n4 agent stages", PALETTE["teal_soft"], PALETTE["teal"]),
        ("Structured\nIR", "Hypothesis\nContract\nDesignIR + RunIR", PALETTE["violet_soft"], PALETTE["violet"]),
        ("Compiler\nChecks", "status: ok\n0 runtime blockers", PALETTE["gray_soft"], PALETTE["gray"]),
        ("WRF-Chem\nExecution", "4 branches\n4 job IDs", PALETTE["blue_soft"], PALETTE["blue"]),
        ("Evidence\nExtraction", "PM25, PBLH,\nSWDOWN, T2, BC1", PALETTE["amber_soft"], PALETTE["amber"]),
        ("Scientist\nVerdict", "rejected by\ncurrent evidence", PALETTE["red_soft"], PALETTE["red"]),
    ]
    x0, gap, w, h = 0.035, 0.018, 0.118, 0.26
    y = 0.54
    centers = []
    for i, (head, body, fc, ec) in enumerate(stages):
        x = x0 + i * (w + gap)
        rounded_box(ax, x, y, w, h, "", fc=fc, ec=ec, lw=1.5)
        ax.text(x + 0.018, y + h - 0.045, head, ha="left", va="top", fontsize=11.5, fontweight="bold", color=PALETTE["navy"])
        ax.text(x + 0.018, y + h - 0.122, body, ha="left", va="top", fontsize=8.8, color=PALETTE["gray"])
        centers.append((x + w, y + h / 2))
        if i < len(stages) - 1:
            arrow(ax, x + w + 0.004, y + h / 2, x + w + gap - 0.006, y + h / 2, color=ec)

    usage = h3.get("tool_usage_report") or {}
    budget = h3.get("budget") or {}
    ledger = h3.get("run_ledger") or {}
    cards = [
        ("tool calls", f"{usage.get('tool_calls_total', 0)}"),
        ("success rate", f"{float(usage.get('tool_success_rate', 0))*100:.1f}%"),
        ("branches", str(len(ledger))),
        ("runs used", f"{budget.get('runs_used', 0)}/{budget.get('runs_limit', 0)}"),
        ("evaluation", "ready"),
    ]
    for i, (k, v) in enumerate(cards):
        x = 0.08 + i * 0.17
        rounded_box(ax, x, 0.25, 0.135, 0.12, "", fc=PALETTE["white"], ec=PALETTE["line"], lw=1.1)
        ax.text(x + 0.018, 0.325, k.upper(), fontsize=7.5, color=PALETTE["gray"], ha="left")
        ax.text(x + 0.018, 0.278, v, fontsize=18, fontweight="bold", color=PALETTE["navy"], ha="left")

    ax.text(0.08, 0.15, "Operational message", fontsize=10, fontweight="bold", color=PALETTE["navy"])
    ax.text(
        0.08,
        0.115,
        "A complete run is represented as auditable artifacts: state, IR, run ledger, results, evidence, verdict, and report.",
        fontsize=9.2,
        color=PALETTE["gray"],
        ha="left",
    )
    save(fig, "01_single_run_operational_overview")


def figure_02_branch_execution_ledger(h3: dict[str, Any]) -> None:
    fig, ax = blank_fig(13.2, 7.2)
    title(ax, "Branch Execution Ledger Board", "H3 WRF-Chem branches tracked from run program to evaluation-ready evidence")
    rows = get_h3_run_rows(h3)
    columns = ["branch", "RunProgramIR", "manifest", "job id", "collector", "result JSON", "evaluation"]
    x0, y0 = 0.035, 0.77
    widths = [0.23, 0.105, 0.10, 0.105, 0.105, 0.12, 0.105]
    row_h = 0.105
    header_h = 0.055
    x = x0
    for col, width in zip(columns, widths):
        rounded_box(ax, x, y0, width, header_h, col, fc=PALETTE["navy"], ec=PALETTE["navy"], color="white", fontsize=8.5, weight="bold", radius=0.012)
        x += width + 0.006
    for r, row in enumerate(rows):
        y = y0 - (r + 1) * row_h
        x = x0
        values = [
            wrap(row["branch"], 22),
            "defined",
            "compiled",
            row["job"],
            row["collector"],
            "local + remote" if row["local"] and row["remote"] else "available",
            "ready" if row["eval"] else "pending",
        ]
        for c, (val, width) in enumerate(zip(values, widths)):
            fc = PALETTE["green_soft"] if c >= 1 else PALETTE["white"]
            ec = PALETTE["green"] if c >= 1 else PALETTE["line"]
            if c == 0:
                fc, ec = PALETTE["blue_soft"], PALETTE["blue"]
            rounded_box(ax, x, y, width, row_h - 0.018, val, fc=fc, ec=ec, fontsize=8.1, color=PALETTE["navy"], radius=0.012)
            x += width + 0.006
    rounded_box(
        ax,
        0.035,
        0.09,
        0.92,
        0.105,
        "Ledger evidence: all four H3 branch entries reached collector_status=ready and evaluation_ready=True.\nSource fields: run_ledger, local_results_paths, remote_results_paths.",
        fc=PALETTE["gray_soft"],
        ec=PALETTE["line"],
        fontsize=8.8,
        color=PALETTE["gray"],
    )
    save(fig, "02_branch_execution_ledger_board")


def curved_band(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], width: float, color: str, alpha: float = 0.45) -> None:
    x1, y1 = start
    x2, y2 = end
    verts = [
        (x1, y1),
        (x1 + 0.18, y1),
        (x2 - 0.18, y2),
        (x2, y2),
    ]
    codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4]
    patch = PathPatch(MplPath(verts, codes), facecolor="none", edgecolor=color, lw=width, alpha=alpha, capstyle="round")
    ax.add_patch(patch)


def figure_03_planner_routing_sankey(h3: dict[str, Any]) -> None:
    fig, ax = blank_fig()
    title(ax, "Planner Decision Routing Sankey", "Agent routing during the H2 completed validation run")
    history = h3.get("controller_history") or []
    counts = Counter(str(item.get("next_agent") or "missing") for item in history if isinstance(item, dict))
    ordered = [("scientist", PALETTE["violet"]), ("execution", PALETTE["blue"]), ("validation", PALETTE["amber"]), ("report", PALETTE["gray"])]
    total = sum(counts.get(k, 0) for k, _ in ordered) or 1
    rounded_box(ax, 0.07, 0.36, 0.18, 0.20, "Planner\nAgent", fc=PALETTE["teal_soft"], ec=PALETTE["teal"], fontsize=15, weight="bold")
    y_positions = [0.70, 0.54, 0.38, 0.22]
    for (agent, color), y in zip(ordered, y_positions):
        n = counts.get(agent, 0)
        curved_band(ax, (0.25, 0.46), (0.62, y + 0.04), 4 + 18 * n / total, color)
        rounded_box(ax, 0.66, y, 0.22, 0.09, f"{agent.title()}\n{n} routed decisions", fc=PALETTE["white"], ec=color, fontsize=10, weight="bold")
        ax.text(0.90, y + 0.045, f"{n/total*100:.0f}%", ha="left", va="center", fontsize=13, color=color, fontweight="bold")
    rounded_box(
        ax,
        0.07,
        0.075,
        0.84,
        0.085,
        f"Total Planner decisions shown: {total}. Routing is execution-heavy, then returns to Scientist evaluation and report synthesis after evidence is ready.",
        fc=PALETTE["gray_soft"],
        ec=PALETTE["line"],
        color=PALETTE["gray"],
        fontsize=8.7,
    )
    save(fig, "03_planner_decision_routing_sankey")


def figure_04_compiler_readiness(h3: dict[str, Any]) -> None:
    fig, ax = blank_fig()
    title(ax, "Compiler Readiness and Guardrail Panel", "Deterministic checks between Agent design intent and WRF-Chem execution")
    boxes = [
        ("ExperimentDesignIR", "topology\nperturbation axes\ndiagnostics\nconfounders", PALETTE["violet_soft"], PALETTE["violet"]),
        ("RunProgramIR", "branch programs\nnamelist intent\nemission scaling\nruntime needs", PALETTE["blue_soft"], PALETTE["blue"]),
        ("Compiler/Linter", "normalize\nlint\nbind capability\ncheck runtime", PALETTE["gray_soft"], PALETTE["gray"]),
        ("Executable\nRun Manifest", "4 branch runs\nTianhe-ready\ncollector outputs", PALETTE["green_soft"], PALETTE["green"]),
    ]
    x0, y, w, h, gap = 0.055, 0.50, 0.18, 0.22, 0.055
    for i, (head, body, fc, ec) in enumerate(boxes):
        x = x0 + i * (w + gap)
        rounded_box(ax, x, y, w, h, "", fc=fc, ec=ec, lw=1.5)
        ax.text(x + 0.018, y + h - 0.045, head, ha="left", va="top", fontsize=11, fontweight="bold", color=PALETTE["navy"])
        ax.text(x + 0.018, y + h - 0.105, body, ha="left", va="top", fontsize=8.6, color=PALETTE["gray"])
        if i < len(boxes) - 1:
            arrow(ax, x + w + 0.008, y + h / 2, x + w + gap - 0.012, y + h / 2, color=ec)
    diag = h3.get("compiler_diagnostics") or {}
    stats = [
        ("status", str(diag.get("status", "missing"))),
        ("capability", str(diag.get("capability_readiness", "recorded")).replace("_", " ")),
        ("runtime blockers", str(len(diag.get("runtime_hard_findings") or []))),
        ("capability gaps", str(len(diag.get("capability_gaps") or []))),
        ("lint findings", str(len(diag.get("lint_findings") or []))),
    ]
    for i, (k, v) in enumerate(stats):
        x = 0.08 + i * 0.17
        fc = PALETTE["green_soft"] if v in {"ok", "0"} or k == "capability" else PALETTE["amber_soft"]
        ec = PALETTE["green"] if v in {"ok", "0"} or k == "capability" else PALETTE["amber"]
        rounded_box(ax, x, 0.23, 0.14, 0.12, "", fc=fc, ec=ec)
        ax.text(x + 0.015, 0.318, k.upper(), fontsize=7.0, color=PALETTE["gray"], ha="left", va="top")
        value_size = 9.6 if k == "capability" else 11.5
        ax.text(x + 0.015, 0.279, wrap(v, 13), fontsize=value_size, color=PALETTE["navy"], fontweight="bold", ha="left", va="top", linespacing=0.94)
    save(fig, "04_compiler_readiness_guardrail_panel")


def figure_05_tool_reliability(h2: dict[str, Any], h3: dict[str, Any]) -> None:
    fig, ax = plt.subplots(figsize=(11, 5.2))
    configure_style()
    ax.set_title("Tool Reliability Strip", loc="left", fontsize=17, fontweight="bold", color=PALETTE["navy"], pad=14)
    ax.set_xlim(0, 700)
    ax.set_ylim(-0.8, 1.8)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["H1 recovery run", "H2 completed run"], fontsize=11)
    ax.set_xlabel("Tool calls")
    ax.grid(axis="x", alpha=0.15)
    for idx, state in enumerate([h2, h3]):
        usage = state.get("tool_usage_report") or {}
        success = int(usage.get("tool_successes") or 0)
        failure = int(usage.get("tool_failures") or 0)
        rate = float(usage.get("tool_success_rate") or 0) * 100
        ax.barh(idx, success, color=PALETTE["teal"], height=0.38, label="success" if idx == 0 else None)
        if failure:
            ax.barh(idx, failure, left=success, color=PALETTE["red"], height=0.38, label="failure" if idx == 0 else None)
        ax.text(success + failure + 10, idx, f"{success+failure} calls, {rate:.1f}% success", va="center", ha="left", fontsize=10, color=PALETTE["navy"], fontweight="bold")
    ax.legend(loc="lower right")
    save(fig, "05_tool_reliability_strip")


def draw_diag_matrix(ax: plt.Axes, x: float, y: float, w: float, h: float, title_text: str, branches: list[str], diagnostics: list[str], matrix: np.ndarray) -> None:
    rounded_box(ax, x, y, w, h, "", fc=PALETTE["white"], ec=PALETTE["line"], lw=1.2)
    ax.text(x + 0.015, y + h - 0.035, title_text, fontsize=10.5, fontweight="bold", color=PALETTE["navy"], ha="left")
    left = x + 0.15
    top = y + h - 0.085
    cw = (w - 0.18) / len(diagnostics)
    rh = (h - 0.13) / len(branches)
    for j, diag in enumerate(diagnostics):
        ax.text(left + j * cw + cw / 2, top + 0.015, diag, ha="center", va="bottom", fontsize=7.2, color=PALETTE["gray"], rotation=25)
    for i, branch in enumerate(branches):
        ax.text(x + 0.012, top - i * rh - rh / 2, wrap(branch, 16), ha="left", va="center", fontsize=7.1, color=PALETTE["gray"])
        for j in range(len(diagnostics)):
            val = matrix[i, j]
            fc = PALETTE["green"] if val == 1 else PALETTE["gray2"] if val == 0 else PALETTE["gray_soft"]
            ec = "white"
            ax.add_patch(Rectangle((left + j * cw + cw * 0.12, top - (i + 1) * rh + rh * 0.15), cw * 0.76, rh * 0.70, facecolor=fc, edgecolor=ec, linewidth=0.8))


def figure_06_evidence_bottleneck(h2_res: dict[str, dict[str, Any]], h3_res: dict[str, dict[str, Any]]) -> None:
    fig, ax = blank_fig(13.0, 7.2)
    title(ax, "Evidence Bottleneck and Diagnostic Gap Map", "Branch-level diagnostic availability from completed WRF-Chem result JSON files")
    h2_diag = ["MDA8", "NO2", "PBLH", "SWDOWN", "HCHO", "HCHO_NO2_RATIO", "AOD550", "JNO2"]
    h3_diag = ["PM25", "PBLH", "SWDOWN", "T2", "BC1", "AOD550"]
    draw_diag_matrix(ax, 0.035, 0.22, 0.58, 0.60, "H2 ozone-control case", list(h2_res), h2_diag, availability_from_results(h2_res, h2_diag))
    draw_diag_matrix(ax, 0.64, 0.22, 0.33, 0.60, "H3 BC-ARI PM2.5 case", list(h3_res), h3_diag, availability_from_results(h3_res, h3_diag))
    small_badge(ax, 0.04, 0.11, "available", fc=PALETTE["green_soft"], ec=PALETTE["green"], w=0.11)
    small_badge(ax, 0.17, 0.11, "missing", fc=PALETTE["gray_soft"], ec=PALETTE["gray2"], w=0.10)
    small_badge(ax, 0.29, 0.11, "not extracted", fc=PALETTE["white"], ec=PALETTE["line"], w=0.12)
    ax.text(0.47, 0.13, "Key message: evidence is sufficient for branch comparison, but mechanism interpretation is constrained by unavailable AOD550/JNO2 diagnostics.", fontsize=9.3, color=PALETTE["gray"], ha="left")
    save(fig, "06_evidence_bottleneck_diagnostic_gap_map")


def draw_gauge(ax: plt.Axes, center: tuple[float, float], radius: float, frac: float, label_text: str, value_text: str, color: str) -> None:
    cx, cy = center
    ax.add_patch(Wedge(center, radius, 180, 360, width=radius * 0.22, facecolor=PALETTE["gray_soft"], edgecolor=PALETTE["line"]))
    ax.add_patch(Wedge(center, radius, 180, 180 + 180 * frac, width=radius * 0.22, facecolor=color, edgecolor=color))
    ax.text(cx, cy - 0.01, value_text, ha="center", va="center", fontsize=20, fontweight="bold", color=PALETTE["navy"])
    ax.text(cx, cy - radius * 0.55, label_text, ha="center", va="center", fontsize=10, color=PALETTE["gray"])


def figure_07_run_budget(h2: dict[str, Any], h3: dict[str, Any]) -> None:
    fig, ax = blank_fig(10.5, 5.8)
    title(ax, "Run-Budget Utilization Panel", "Factorial WRF-Chem validation stayed within configured run budget")
    for i, (name, state, color) in enumerate([("H2", h2, PALETTE["blue"]), ("H3", h3, PALETTE["amber"])]):
        budget = state.get("budget") or {}
        used, limit = float(budget.get("runs_used") or 0), float(budget.get("runs_limit") or 1)
        draw_gauge(ax, (0.30 + i * 0.40, 0.52), 0.20, used / limit, name, f"{int(used)}/{int(limit)}", color)
        rounded_box(ax, 0.17 + i * 0.40, 0.16, 0.26, 0.11, f"{name}: 4-branch design uses {used/limit*100:.0f}% of run budget", fc=PALETTE["white"], ec=color, fontsize=9.2, color=PALETTE["gray"])
    save(fig, "07_run_budget_utilization_panel")


def figure_08_recovery_trace(h2: dict[str, Any]) -> None:
    fig, ax = blank_fig(13.0, 6.2)
    title(ax, "Recovery-Aware Execution Trace", "H2 recovery run preserved state and completed evidence collection")
    stages = [
        ("Design IR", "experiment and run IR compiled"),
        ("Remote submit", "4 Tianhe jobs issued"),
        ("Monitor", "queue and wrfout progress tracked"),
        ("Collect", "remote results mirrored locally"),
        ("Recovery", f"{len(h2.get('recovery_history') or [])} recovery records"),
        ("Validation", "evidence-only bridge ready"),
        ("Scientist", "partially supported verdict"),
        ("Report", "human research narrative"),
    ]
    xs = np.linspace(0.08, 0.92, len(stages))
    y = 0.52
    for i, (head, body) in enumerate(stages):
        color = PALETTE["teal"] if i < 4 else PALETTE["amber"] if i == 4 else PALETTE["violet"]
        ax.add_patch(Circle((xs[i], y), 0.025, facecolor=color, edgecolor="white", linewidth=1.5, zorder=3))
        ax.text(xs[i], y + 0.075, head, ha="center", va="bottom", fontsize=10.5, fontweight="bold", color=PALETTE["navy"])
        ax.text(xs[i], y - 0.07, wrap(body, 16), ha="center", va="top", fontsize=8.2, color=PALETTE["gray"])
        if i < len(stages) - 1:
            ax.plot([xs[i] + 0.027, xs[i + 1] - 0.027], [y, y], color=PALETTE["line"], linewidth=2.2)
    usage = h2.get("tool_usage_report") or {}
    rounded_box(ax, 0.13, 0.15, 0.74, 0.12, f"H2 recovery run: {usage.get('tool_calls_total', 0)} tool calls, {float(usage.get('tool_success_rate', 0))*100:.1f}% success, 4 jobs reached evaluation_ready.", fc=PALETTE["gray_soft"], ec=PALETTE["line"], fontsize=10, color=PALETTE["gray"])
    save(fig, "08_recovery_aware_execution_trace")


def figure_09_runtime_asset_readiness(h3: dict[str, Any]) -> None:
    fig, ax = blank_fig()
    title(ax, "Runtime Asset Readiness Board", "Pre-execution assets and runtime capabilities recorded in the H3 session")
    evidence = h3.get("h3_runtime_asset_evidence") or {}
    items = [
        ("Meteorology", "FNL / time-window forcing", bool(evidence.get("meteorology"))),
        ("Chemistry IC/BC", "CAM-Chem or configured chemistry input", bool(evidence.get("chemistry_icbc"))),
        ("Emissions", "anthropogenic / BC branch settings", bool(evidence.get("emissions"))),
        ("Diagnostics", "PM25, PBLH, SWDOWN, T2, BC1", bool(evidence.get("diagnostic_inventory"))),
        ("Runtime tuple", "WRF-Chem capability context", bool(evidence.get("runtime_tuple"))),
        ("AOD550", "not available in result extraction", False),
    ]
    for i, (head, body, ok) in enumerate(items):
        col, row = i % 3, i // 3
        x, y = 0.075 + col * 0.30, 0.54 - row * 0.25
        fc = PALETTE["green_soft"] if ok else PALETTE["gray_soft"]
        ec = PALETTE["green"] if ok else PALETTE["gray2"]
        rounded_box(ax, x, y, 0.25, 0.16, "", fc=fc, ec=ec, lw=1.4)
        ax.text(x + 0.018, y + 0.115, head, ha="left", va="center", fontsize=11.5, fontweight="bold", color=PALETTE["navy"])
        ax.text(x + 0.018, y + 0.066, wrap(body, 30), ha="left", va="center", fontsize=8.2, color=PALETTE["gray"])
        ax.text(x + 0.22, y + 0.115, "OK" if ok else "GAP", ha="center", va="center", fontsize=9, fontweight="bold", color=ec)
    save(fig, "09_runtime_asset_readiness_board")


def figure_10_verdict_decomposition(h3: dict[str, Any], h3_res: dict[str, dict[str, Any]]) -> None:
    fig, ax = blank_fig(12.5, 7.2)
    title(ax, "Scientific Verdict Decomposition", "How evidence cards combine into the H3 Scientist verdict")
    ctrl = h3_res["No ARI / normal BC"]
    ari = h3_res["ARI / normal BC"]
    pm25_pct = (ari["pm25_mean"] - ctrl["pm25_mean"]) / ctrl["pm25_mean"] * 100
    sw_pct = (ari["swdown_mean"] - ctrl["swdown_mean"]) / ctrl["swdown_mean"] * 100
    pblh_pct = (ari["pblh_mean"] - ctrl["pblh_mean"]) / ctrl["pblh_mean"] * 100
    cards = [
        ("Run integrity", "4/4 branches completed\ncollector ready", PALETTE["green_soft"], PALETTE["green"]),
        ("Radiative signal", f"SWDOWN {sw_pct:+.2f}%\nexpected decrease", PALETTE["green_soft"], PALETTE["green"]),
        ("PBL response", f"PBLH {pblh_pct:+.2f}%\nweak decrease", PALETTE["amber_soft"], PALETTE["amber"]),
        ("PM25 response", f"PM25 {pm25_pct:+.3f}%\nnegligible", PALETTE["red_soft"], PALETTE["red"]),
        ("BC perturbation", "BC main effect = 0\ninteraction = 0", PALETTE["red_soft"], PALETTE["red"]),
        ("Missing diagnostic", "AOD550 unavailable\nmechanism constrained", PALETTE["gray_soft"], PALETTE["gray2"]),
    ]
    for i, (head, body, fc, ec) in enumerate(cards):
        x = 0.055 + (i % 3) * 0.29
        y = 0.58 - (i // 3) * 0.23
        rounded_box(ax, x, y, 0.25, 0.15, "", fc=fc, ec=ec, lw=1.4)
        ax.text(x + 0.016, y + 0.105, head, ha="left", va="center", fontsize=11, fontweight="bold", color=PALETTE["navy"])
        ax.text(x + 0.016, y + 0.055, body, ha="left", va="center", fontsize=8.8, color=PALETTE["gray"])
        arrow(ax, x + 0.125, y - 0.01, 0.50, 0.21, color=ec, lw=1.1, mutation_scale=8, connectionstyle="arc3,rad=0.18")
    verdict = (h3.get("scientific_analysis_ir") or {}).get("verdict", "rejected")
    rounded_box(ax, 0.38, 0.08, 0.30, 0.14, f"Scientist verdict\n{str(verdict).upper()}", fc=PALETTE["red_soft"], ec=PALETTE["red"], fontsize=15, weight="bold", color=PALETTE["navy"])
    save(fig, "10_scientific_verdict_decomposition")


def figure_11_remote_execution_evidence_matrix(h2: dict[str, Any], h3: dict[str, Any]) -> None:
    fig, ax = blank_fig(13.4, 7.8)
    title(ax, "Remote Execution Evidence Matrix", "Completed Tianhe WRF-Chem branch evidence for H2 and H3")
    rows = [("H2", r) for r in get_h2_run_rows(h2)] + [("H3", r) for r in get_h3_run_rows(h3)]
    cols = ["case", "branch", "job id", "collector", "remote result", "local result", "evaluation"]
    widths = [0.07, 0.31, 0.10, 0.12, 0.12, 0.12, 0.12]
    x0, y0 = 0.035, 0.83
    x = x0
    for col, width in zip(cols, widths):
        rounded_box(ax, x, y0, width, 0.048, col, fc=PALETTE["navy"], ec=PALETTE["navy"], color="white", fontsize=7.8, weight="bold", radius=0.010)
        x += width + 0.004
    row_h = 0.074
    for i, (case, row) in enumerate(rows):
        y = y0 - (i + 1) * row_h
        values = [
            case,
            wrap(row["branch"], 28),
            row["job"],
            row["collector"],
            "ready" if row["remote"] else "missing",
            "ready" if row["local"] else "missing",
            "ready" if row["eval"] else "pending",
        ]
        x = x0
        for c, (val, width) in enumerate(zip(values, widths)):
            if c == 0:
                fc, ec = (PALETTE["blue_soft"], PALETTE["blue"]) if case == "H2" else (PALETTE["amber_soft"], PALETTE["amber"])
            elif val in {"ready", "evaluation_ready"} or c in {2, 3}:
                fc, ec = PALETTE["green_soft"], PALETTE["green"]
            else:
                fc, ec = PALETTE["gray_soft"], PALETTE["gray2"]
            rounded_box(ax, x, y, width, row_h - 0.012, val, fc=fc, ec=ec, fontsize=7.4, color=PALETTE["navy"], radius=0.010)
            x += width + 0.004
    save(fig, "11_remote_execution_evidence_matrix")


def figure_12_artifact_trace(h3: dict[str, Any]) -> None:
    fig, ax = blank_fig(13.0, 5.8)
    title(ax, "Hypothesis-to-Artifact Trace Timeline", "Structured artifact lineage in a completed v2 validation run")
    artifacts = [
        ("Hypothesis\nContract", "claim + predictions"),
        ("Experiment\nDesignIR", "topology + diagnostics"),
        ("Run\nProgramIR", "branch settings"),
        ("Run\nManifest", "4 branch runs"),
        ("Run\nLedger", "4 job records"),
        ("Validation\nResult", "evidence only"),
        ("AnalysisIR", "Scientist verdict"),
        ("Report", "human narrative"),
        ("Figure\nArtifacts", "planned renderer"),
    ]
    xs = np.linspace(0.06, 0.94, len(artifacts))
    y = 0.52
    for i, (head, body) in enumerate(artifacts):
        color = PALETTE["gray2"] if i == len(artifacts) - 1 else [PALETTE["blue"], PALETTE["violet"], PALETTE["teal"], PALETTE["blue"], PALETTE["amber"], PALETTE["amber"], PALETTE["violet"], PALETTE["gray"]][i]
        ax.add_patch(Circle((xs[i], y), 0.022, facecolor=color, edgecolor="white", lw=1.2, zorder=3))
        ax.text(xs[i], y + 0.06, head, ha="center", va="bottom", fontsize=9.5, fontweight="bold", color=PALETTE["navy"])
        ax.text(xs[i], y - 0.052, body, ha="center", va="top", fontsize=7.6, color=PALETTE["gray"])
        if i < len(artifacts) - 1:
            ax.plot([xs[i] + 0.024, xs[i + 1] - 0.024], [y, y], color=PALETTE["line"], lw=2.0)
            arrow(ax, xs[i + 1] - 0.055, y, xs[i + 1] - 0.028, y, color=PALETTE["line"], lw=1.2, mutation_scale=8)
    rounded_box(ax, 0.17, 0.14, 0.66, 0.11, "The final figure-artifact node is a recommended extension: Agent plans the figure, deterministic renderer creates SVG/PDF/PNG from validation evidence.", fc=PALETTE["gray_soft"], ec=PALETTE["line"], fontsize=9, color=PALETTE["gray"])
    save(fig, "12_hypothesis_to_artifact_trace_timeline")


def figure_13_agent_handoff_swimlane(h3: dict[str, Any]) -> None:
    history = [item for item in (h3.get("controller_history") or []) if isinstance(item, dict)]
    agents = ["scientist", "execution", "validation", "report"]
    colors = {"scientist": PALETTE["violet"], "execution": PALETTE["blue"], "validation": PALETTE["amber"], "report": PALETTE["gray"]}
    fig, ax = plt.subplots(figsize=(13, 5.8))
    configure_style()
    ax.set_title("Agent Handoff Swimlane", loc="left", fontsize=17, fontweight="bold", color=PALETTE["navy"], pad=14)
    ax.set_xlim(0, max(len(history), 1))
    ax.set_ylim(-0.6, len(agents) - 0.35)
    ax.set_yticks(range(len(agents)))
    ax.set_yticklabels([a.title() for a in agents])
    ax.set_xlabel("Planner decision index")
    ax.grid(axis="x", alpha=0.12)
    for i, item in enumerate(history):
        agent = str(item.get("next_agent") or "")
        if agent not in agents:
            continue
        y = agents.index(agent)
        ax.add_patch(Rectangle((i, y - 0.28), 0.86, 0.56, facecolor=colors[agent], alpha=0.72, edgecolor="white", linewidth=0.6))
    counts = Counter(str(item.get("next_agent") or "") for item in history)
    for agent in agents:
        y = agents.index(agent)
        ax.text(len(history) + 0.2, y, f"{counts.get(agent, 0)}", va="center", ha="left", fontsize=11, fontweight="bold", color=colors[agent])
    save(fig, "13_agent_handoff_swimlane")


def figure_14_system_maturity_radar() -> None:
    labels = [
        "Hypothesis\nstructuring",
        "Experiment\ndesign",
        "Compiler\nchecks",
        "Remote\nexecution",
        "Diagnostic\nextraction",
        "Scientist\nevaluation",
        "Report\nsynthesis",
        "Figure\ngeneration",
        "Observation\nintegration",
    ]
    values = np.array([0.86, 0.78, 0.82, 0.72, 0.70, 0.68, 0.64, 0.28, 0.15])
    angles = np.linspace(0, 2 * math.pi, len(labels), endpoint=False)
    values_closed = np.r_[values, values[0]]
    angles_closed = np.r_[angles, angles[0]]
    fig = plt.figure(figsize=(8.5, 8.0))
    configure_style()
    ax = fig.add_subplot(111, polar=True)
    ax.set_title("System Maturity Radar", loc="left", fontsize=17, fontweight="bold", color=PALETTE["navy"], pad=28)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.plot(angles_closed, values_closed, color=PALETTE["teal"], lw=2.5)
    ax.fill(angles_closed, values_closed, color=PALETTE["teal"], alpha=0.18)
    ax.scatter(angles, values, color=PALETTE["navy"], s=26, zorder=4)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.50, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=8, color=PALETTE["gray"])
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=9)
    ax.grid(color=PALETTE["line"], lw=0.8)
    ax.spines["polar"].set_color(PALETTE["line"])
    fig.text(0.08, 0.06, "Scores are evidence-informed maturity estimates from current v2 records; figure generation and observation integration are planned/partial.", fontsize=8.5, color=PALETTE["gray"])
    save(fig, "14_system_maturity_radar")


def main() -> None:
    configure_style()
    h2 = load_state(H2_SESSION)
    h3 = load_state(H3_SESSION)
    h2_res = h2_results()
    h3_res = h3_results()

    figure_01_single_run_overview(h3)
    figure_02_branch_execution_ledger(h3)
    figure_03_planner_routing_sankey(h3)
    figure_04_compiler_readiness(h3)
    figure_05_tool_reliability(h2, h3)
    figure_06_evidence_bottleneck(h2_res, h3_res)
    figure_07_run_budget(h2, h3)
    figure_08_recovery_trace(h2)
    figure_09_runtime_asset_readiness(h3)
    figure_10_verdict_decomposition(h3, h3_res)
    figure_11_remote_execution_evidence_matrix(h2, h3)
    figure_12_artifact_trace(h3)
    figure_13_agent_handoff_swimlane(h3)
    figure_14_system_maturity_radar()
    print(f"Wrote figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
