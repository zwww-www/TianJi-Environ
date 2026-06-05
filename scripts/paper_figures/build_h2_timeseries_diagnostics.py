"""Build a publication-ready H2 branch time-series diagnostic figure.

The figure is based on collected Tianhe WRF-Chem branch result JSON files for
the Guanzhong BC absorbing-ARI case. It combines daily diagnostic trajectories
with a compact mean-contrast matrix so overlapping branch lines remain
scientifically interpretable rather than visually ambiguous.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/atmoschem-agent-mplcache")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/atmoschem-agent-cache")

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "outputs" / "remote_results" / "v2_20260427_181352"
OUT_DIR = ROOT / "paper" / "figures"
SOURCE_DIR = OUT_DIR / "source_data"
OUT_BASENAME = "h2_branch_timeseries_diagnostics"


BRANCH_FILES = {
    "noari_normalbc": "ari_ozone_20260427_181352_control_no_ari_normal_bc_results.json",
    "ari_normalbc": "ari_ozone_20260427_181352_treatment_ari_on_normal_bc_results.json",
    "noari_highbc": "ari_ozone_20260427_181352_treatment_no_ari_high_bc_results.json",
    "ari_highbc": "ari_ozone_20260427_181352_treatment_ari_on_high_bc_results.json",
}

BRANCH_LABELS = {
    "noari_normalbc": "No ARI, normal BC",
    "noari_highbc": "No ARI, high BC",
    "ari_normalbc": "ARI, normal BC",
    "ari_highbc": "ARI, high BC",
}

BRANCH_STYLES = {
    "noari_normalbc": {
        "color": "#5B6472",
        "linestyle": "-",
        "marker": "o",
        "markerfacecolor": "#5B6472",
        "zorder": 3,
    },
    "noari_highbc": {
        "color": "#5B6472",
        "linestyle": (0, (3.0, 2.0)),
        "marker": "D",
        "markerfacecolor": "white",
        "zorder": 4,
    },
    "ari_normalbc": {
        "color": "#286DA8",
        "linestyle": "-",
        "marker": "o",
        "markerfacecolor": "#286DA8",
        "zorder": 3,
    },
    "ari_highbc": {
        "color": "#286DA8",
        "linestyle": (0, (3.0, 2.0)),
        "marker": "D",
        "markerfacecolor": "white",
        "zorder": 4,
    },
}


@dataclass(frozen=True)
class VariableSpec:
    key: str
    label: str
    ylabel: str
    scale: float = 1.0
    value_format: str = "{:.2f}"


VARIABLES = [
    VariableSpec("pm25", "PM$_{2.5}$", r"$\mu$g m$^{-3}$", 1.0, "{:.3f}"),
    VariableSpec("swdown", "SWDOWN", r"W m$^{-2}$", 1.0, "{:.1f}"),
    VariableSpec("pblh", "PBLH", "m", 1.0, "{:.1f}"),
    VariableSpec("t2", "T2", "K", 1.0, "{:.2f}"),
    VariableSpec("bc1", "BC1", r"$10^{-3}$ model units", 1000.0, "{:.2f}"),
]


def configure_style() -> None:
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
    plt.rcParams["svg.fonttype"] = "none"
    mpl.rcParams.update(
        {
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.size": 7.0,
            "axes.titlesize": 7.4,
            "axes.labelsize": 7.0,
            "axes.linewidth": 0.65,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.labelsize": 6.4,
            "ytick.labelsize": 6.4,
            "legend.fontsize": 6.4,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def load_records() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for branch, filename in BRANCH_FILES.items():
        data = json.loads((RESULTS_DIR / filename).read_text())
        for spec in VARIABLES:
            values = data[f"{spec.key}_daily"]
            dates = pd.to_datetime(data[f"{spec.key}_dates"])
            for date, value in zip(dates, values, strict=True):
                rows.append(
                    {
                        "branch": branch,
                        "branch_label": BRANCH_LABELS[branch],
                        "variable": spec.key,
                        "variable_label": spec.label,
                        "date": date,
                        "value": float(value),
                        "plot_value": float(value) * spec.scale,
                    }
                )
    return pd.DataFrame(rows)


def mean_table(df: pd.DataFrame) -> pd.DataFrame:
    means = (
        df.groupby(["variable", "branch"], as_index=False)["value"]
        .mean()
        .pivot(index="variable", columns="branch", values="value")
    )
    records = []
    for spec in VARIABLES:
        row = means.loc[spec.key]
        ctrl = row["noari_normalbc"]
        ari = row["ari_normalbc"]
        bc_noari = row["noari_highbc"]
        bc_ari = row["ari_highbc"]
        contrasts = {
            "ARI effect": ari - ctrl,
            "BC effect\n(no ARI)": bc_noari - ctrl,
            "BC effect\n(ARI)": bc_ari - ari,
        }
        percent = {
            "ARI effect": 100.0 * (ari - ctrl) / ctrl,
            "BC effect\n(no ARI)": 100.0 * (bc_noari - ctrl) / ctrl,
            "BC effect\n(ARI)": 100.0 * (bc_ari - ari) / ari,
        }
        for contrast in contrasts:
            records.append(
                {
                    "variable": spec.key,
                    "variable_label": spec.label,
                    "contrast": contrast,
                    "delta": contrasts[contrast],
                    "percent_change": percent[contrast],
                    "plot_delta": contrasts[contrast] * spec.scale,
                    "scaled_units": spec.ylabel,
                }
            )
    return pd.DataFrame(records)


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.11,
        1.08,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontweight="bold",
        fontsize=8.2,
    )


def line_panel(ax: plt.Axes, df: pd.DataFrame, spec: VariableSpec) -> None:
    sub = df[df["variable"] == spec.key]
    for branch in ["noari_normalbc", "noari_highbc", "ari_normalbc", "ari_highbc"]:
        bdf = sub[sub["branch"] == branch].sort_values("date")
        style = BRANCH_STYLES[branch]
        line, = ax.plot(
            bdf["date"],
            bdf["plot_value"],
            label=BRANCH_LABELS[branch],
            linewidth=1.35,
            markersize=3.2,
            markeredgewidth=0.8,
            markeredgecolor=style["color"],
            alpha=0.94,
            **style,
        )
        if "highbc" in branch:
            line.set_path_effects([pe.Stroke(linewidth=2.1, foreground="white"), pe.Normal()])

    ax.set_title(spec.label, loc="left", fontweight="bold", pad=2)
    ax.set_ylabel(spec.ylabel)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_xticks(pd.to_datetime(["2014-12-10", "2014-12-11", "2014-12-12"]))
    ax.grid(axis="y", color="#E6E8EC", linewidth=0.55)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="both", width=0.6, length=2.4, color="#3F4650")

    ax.margins(x=0.08, y=0.12)


def contrast_panel(ax: plt.Axes, contrasts: pd.DataFrame) -> None:
    pivot = contrasts.pivot(index="variable_label", columns="contrast", values="percent_change")
    pivot = pivot.loc[[v.label for v in VARIABLES], ["ARI effect", "BC effect\n(no ARI)", "BC effect\n(ARI)"]]
    vals = pivot.to_numpy(dtype=float)
    vmax = max(0.5, float(np.nanmax(np.abs(vals))))
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    im = ax.imshow(vals, cmap="RdBu_r", norm=norm, aspect="auto")

    ax.set_xticks(np.arange(pivot.shape[1]), pivot.columns)
    ax.set_yticks(np.arange(pivot.shape[0]), pivot.index)
    ax.tick_params(axis="x", labelrotation=0, length=0)
    ax.tick_params(axis="y", length=0)
    ax.set_title("Mean branch contrasts", loc="left", fontweight="bold", pad=2)
    ax.set_xlabel("Percent change relative to paired reference")

    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            val = vals[i, j]
            label = f"{val:+.2f}%"
            color = "white" if abs(val) > vmax * 0.48 else "#222222"
            ax.text(j, i, label, ha="center", va="center", fontsize=6.2, color=color)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(-0.5, vals.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-0.5, vals.shape[0], 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", bottom=False, left=False)

    cbar = plt.colorbar(im, ax=ax, fraction=0.050, pad=0.025)
    cbar.ax.tick_params(labelsize=5.8, width=0.4, length=2)
    cbar.outline.set_linewidth(0.4)
    cbar.set_label("%", fontsize=6.2)

    ax.text(
        0.0,
        -0.26,
        "Near-zero BC contrasts mark coincident high-BC and normal-BC branch trajectories.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.0,
        color="#5B6472",
        wrap=True,
    )


def build_figure() -> None:
    configure_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    df = load_records()
    contrasts = mean_table(df)
    df.to_csv(SOURCE_DIR / f"{OUT_BASENAME}.csv", index=False)
    contrasts.to_csv(SOURCE_DIR / f"{OUT_BASENAME}_mean_contrasts.csv", index=False)

    fig = plt.figure(figsize=(7.2, 6.45), constrained_layout=False)
    gs = fig.add_gridspec(
        3,
        2,
        left=0.075,
        right=0.985,
        bottom=0.075,
        top=0.91,
        hspace=0.50,
        wspace=0.34,
    )
    axes = [
        fig.add_subplot(gs[0, 0]),
        fig.add_subplot(gs[0, 1]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[2, 0]),
        fig.add_subplot(gs[2, 1]),
    ]
    for ax, spec, label in zip(axes[:5], VARIABLES, list("abcde"), strict=True):
        line_panel(ax, df, spec)
        add_panel_label(ax, label)

    contrast_panel(axes[5], contrasts)
    add_panel_label(axes[5], "f")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        ncol=4,
        loc="upper center",
        bbox_to_anchor=(0.54, 0.982),
        columnspacing=1.2,
        handlelength=2.8,
    )
    fig.text(
        0.075,
        0.965,
        "H2 branch diagnostics",
        ha="left",
        va="center",
        fontsize=8.4,
        fontweight="bold",
    )
    fig.text(
        0.075,
        0.943,
        "Daily domain means from the 2 x 2 ARI and BC-load branch experiment",
        ha="left",
        va="center",
        fontsize=6.6,
        color="#5B6472",
    )

    for suffix, kwargs in {
        "svg": {},
        "pdf": {},
        "png": {"dpi": 600},
        "tiff": {"dpi": 600},
    }.items():
        fig.savefig(OUT_DIR / f"{OUT_BASENAME}.{suffix}", bbox_inches="tight", **kwargs)
    plt.close(fig)


if __name__ == "__main__":
    build_figure()
