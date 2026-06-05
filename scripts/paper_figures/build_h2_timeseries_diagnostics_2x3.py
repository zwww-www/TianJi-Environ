"""Build the 2 x 3 layout variant of the H2 branch diagnostic figure.

This script intentionally writes to a separate basename so the original 3 x 2
figure remains available for comparison.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from build_h2_timeseries_diagnostics import (
    OUT_DIR,
    SOURCE_DIR,
    VARIABLES,
    add_panel_label,
    configure_style,
    contrast_panel,
    line_panel,
    load_records,
    mean_table,
)


OUT_BASENAME = "h2_branch_timeseries_diagnostics_2x3"


def build_figure() -> None:
    configure_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    df = load_records()
    contrasts = mean_table(df)
    df.to_csv(SOURCE_DIR / f"{OUT_BASENAME}.csv", index=False)
    contrasts.to_csv(SOURCE_DIR / f"{OUT_BASENAME}_mean_contrasts.csv", index=False)

    fig = plt.figure(figsize=(7.55, 4.78), constrained_layout=False)
    gs = fig.add_gridspec(
        2,
        3,
        left=0.070,
        right=0.985,
        bottom=0.105,
        top=0.845,
        hspace=0.55,
        wspace=0.44,
    )
    axes = [
        fig.add_subplot(gs[0, 0]),
        fig.add_subplot(gs[0, 1]),
        fig.add_subplot(gs[0, 2]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[1, 2]),
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
        bbox_to_anchor=(0.60, 0.975),
        columnspacing=1.0,
        handlelength=2.4,
    )
    fig.text(
        0.070,
        0.953,
        "H2 branch diagnostics",
        ha="left",
        va="center",
        fontsize=8.4,
        fontweight="bold",
    )
    fig.text(
        0.070,
        0.924,
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
