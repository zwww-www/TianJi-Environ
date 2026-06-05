#!/usr/bin/env python3
"""Build a gridded real-data Simple Analysis TaskBench composite figure."""

from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import FuncFormatter
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


REPO_ROOT = Path(__file__).resolve().parents[2]
SCORES_DIR = REPO_ROOT / "outputs" / "simple_analysis_real_gridded" / "scores" / "cases"
OUTPUT_STEM = REPO_ROOT / "paper" / "figures" / "simple_analysis_taskbench_real_gridded_composite"
SOURCE_DATA = REPO_ROOT / "paper" / "figures" / "source_data" / "simple_analysis_taskbench_real_gridded_composite.csv"
MPL_CACHE = REPO_ROOT / "outputs" / ".paper_figure_mpl_cache"
EXTENT = {"lon_min": 111.85, "lon_max": 116.05, "lat_min": 21.55, "lat_max": 24.15}


def _style() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))
    MPL_CACHE.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 6.4,
            "axes.titlesize": 7.1,
            "axes.labelsize": 6.3,
            "axes.linewidth": 0.65,
            "xtick.labelsize": 6.2,
            "ytick.labelsize": 6.2,
            "xtick.major.width": 0.55,
            "ytick.major.width": 0.55,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def _case(case_id: str) -> dict[str, Any]:
    return json.loads((SCORES_DIR / f"{case_id}.json").read_text(encoding="utf-8"))


def _as_points(items: Sequence[Mapping[str, Any]], value_key: str) -> list[dict[str, float | str]]:
    points: list[dict[str, float | str]] = []
    for item in items:
        if item.get(value_key) is None or item.get("lon") is None or item.get("lat") is None:
            continue
        points.append(
            {
                "location": str(item.get("location") or ""),
                "lon": float(item["lon"]),
                "lat": float(item["lat"]),
                "value": float(item[value_key]),
            }
        )
    if not points:
        raise ValueError(f"no valid values for {value_key}")
    return points


def _grid(points: Sequence[Mapping[str, float | str]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lons = np.asarray(sorted({round(float(item["lon"]), 6) for item in points}), dtype=float)
    lats = np.asarray(sorted({round(float(item["lat"]), 6) for item in points}), dtype=float)
    values = np.full((len(lats), len(lons)), np.nan, dtype=float)
    lon_index = {value: index for index, value in enumerate(lons)}
    lat_index = {value: index for index, value in enumerate(lats)}
    for item in points:
        lon = round(float(item["lon"]), 6)
        lat = round(float(item["lat"]), 6)
        values[lat_index[lat], lon_index[lon]] = float(item["value"])
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    return lon_grid, lat_grid, values


def _nice_step(raw_step: float) -> float:
    if raw_step <= 0 or not np.isfinite(raw_step):
        return 1.0
    exponent = np.floor(np.log10(raw_step))
    scale = 10.0**exponent
    fraction = raw_step / scale
    for candidate in (1.0, 2.0, 2.5, 5.0, 10.0):
        if fraction <= candidate:
            return candidate * scale
    return 10.0 * scale


def _levels(values: np.ndarray, *, bins: int = 9) -> np.ndarray:
    finite = np.ma.compressed(np.ma.masked_invalid(values)).astype(float)
    if finite.size == 0:
        return np.linspace(0, 1, bins + 1)
    vmin = float(np.nanmin(finite))
    vmax = float(np.nanmax(finite))
    if np.isclose(vmin, vmax):
        width = max(abs(vmax) * 0.1, 1.0)
        return np.linspace(vmin - width, vmax + width, bins + 1)
    step = _nice_step((vmax - vmin) / bins)
    nice_min = np.floor(vmin / step) * step
    nice_max = np.ceil(vmax / step) * step
    return np.arange(nice_min, nice_max + step * 0.5, step)


def _format_lon(value: float, _pos: int | None = None) -> str:
    label = f"{abs(value):.0f}" if np.isclose(abs(value), round(abs(value))) else f"{abs(value):.1f}"
    return f"{label}°{'E' if value >= 0 else 'W'}"


def _format_lat(value: float, _pos: int | None = None) -> str:
    label = f"{abs(value):.0f}" if np.isclose(abs(value), round(abs(value))) else f"{abs(value):.1f}"
    return f"{label}°{'N' if value >= 0 else 'S'}"


@lru_cache(maxsize=1)
def _coastlines() -> tuple[tuple[tuple[float, float], ...], ...]:
    try:
        import cartopy.io.shapereader as shapereader
    except Exception:
        return ()
    path = shapereader.natural_earth(resolution="10m", category="physical", name="coastline")
    segments: list[tuple[tuple[float, float], ...]] = []
    for geometry in shapereader.Reader(path).geometries():
        geoms = geometry.geoms if getattr(geometry, "geom_type", "") == "MultiLineString" else [geometry]
        for part in geoms:
            if getattr(part, "geom_type", "") != "LineString":
                continue
            coords = tuple((float(x), float(y)) for x, y, *_ in part.coords)
            if len(coords) >= 2:
                segments.append(coords)
    return tuple(segments)


def _draw_coast(ax: Any) -> None:
    segments = []
    for segment in _coastlines():
        xs = [point[0] for point in segment]
        ys = [point[1] for point in segment]
        if (
            max(xs) < EXTENT["lon_min"]
            or min(xs) > EXTENT["lon_max"]
            or max(ys) < EXTENT["lat_min"]
            or min(ys) > EXTENT["lat_max"]
        ):
            continue
        segments.append(segment)
    if segments:
        ax.add_collection(
            LineCollection(segments, colors="#202326", linewidths=0.55, alpha=0.86, zorder=8)
        )


def _set_geo_axis(ax: Any) -> None:
    ax.set_xlim(EXTENT["lon_min"], EXTENT["lon_max"])
    ax.set_ylim(EXTENT["lat_min"], EXTENT["lat_max"])
    ax.set_xticks([112, 114, 116])
    ax.set_yticks([22, 23, 24])
    ax.xaxis.set_major_formatter(FuncFormatter(_format_lon))
    ax.yaxis.set_major_formatter(FuncFormatter(_format_lat))
    ax.tick_params(length=2.6, pad=1.5)
    ax.set_aspect("equal", adjustable="box")
    ax.set_box_aspect(0.62)
    ax.grid(False)


def _plot_map(
    ax: Any,
    points: Sequence[Mapping[str, float | str]],
    *,
    title: str,
    cmap: str,
    colorbar_label: str,
    marker: Mapping[str, Any] | None = None,
) -> None:
    lon_grid, lat_grid, values = _grid(points)
    levels = _levels(values)
    contour = ax.contourf(
        lon_grid,
        lat_grid,
        values,
        levels=levels,
        cmap=cmap,
        antialiased=True,
        extend="neither",
    )
    _draw_coast(ax)
    if marker is not None:
        ax.scatter(
            [float(marker["lon"])],
            [float(marker["lat"])],
            marker=str(marker.get("marker", "*")),
            s=float(marker.get("size", 52)),
            c=str(marker.get("color", "#31D2C6")),
            edgecolors="black",
            linewidths=0.6,
            zorder=10,
        )
    _set_geo_axis(ax)
    ax.set_title(title, loc="left", pad=2)
    cax = inset_axes(
        ax,
        width="4.0%",
        height="72%",
        loc="center left",
        bbox_to_anchor=(1.035, 0.0, 1.0, 1.0),
        bbox_transform=ax.transAxes,
        borderpad=0,
    )
    colorbar = ax.figure.colorbar(contour, cax=cax)
    colorbar.ax.set_title(colorbar_label, fontsize=5.7, pad=2)
    colorbar.ax.tick_params(labelsize=5.5, length=1.8, width=0.4, pad=1.2)


def _plot_series(ax: Any, series: Sequence[Mapping[str, Any]], event_date: str) -> None:
    x = np.arange(len(series))
    y = np.asarray([float(item["domain_mean"]) for item in series], dtype=float)
    labels = [str(item["date"])[5:] for item in series]
    ax.plot(x, y, color="#9A4D00", linewidth=1.65, marker="o", markersize=3.0)
    ax.fill_between(x, y, color="#F6C56B", alpha=0.22)
    for index, item in enumerate(series):
        if item.get("date") == event_date:
            ax.scatter([index], [float(item["domain_mean"])], s=45, color="#C91F1F", zorder=5)
            ax.annotate(
                "episode",
                xy=(index, float(item["domain_mean"])),
                xytext=(index + 0.25, float(item["domain_mean"]) + max(y) * 0.08),
                fontsize=5.8,
                arrowprops={"arrowstyle": "-", "linewidth": 0.6, "color": "#C91F1F"},
            )
            break
    ax.set_title("(g) PM2.5 episode selection", loc="left", pad=2)
    ax.set_ylabel("Domain mean PM2.5 (ug m-3)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.grid(axis="y", color="0.88", linewidth=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _plot_correlations(ax: Any, correlations: Mapping[str, Any]) -> None:
    labels = ["T2", "PBLH", "SWDOWN"]
    keys = ["t2_c", "pblh_m", "swdown_wm2"]
    values = [float(correlations[key]) for key in keys]
    colors = ["#C85A2E" if value >= 0 else "#3978B8" for value in values]
    ax.barh(labels, values, color=colors, height=0.55)
    ax.axvline(0, color="0.25", linewidth=0.65)
    for idx, value in enumerate(values):
        ax.text(
            value + (0.015 if value >= 0 else -0.015),
            idx,
            f"{value:+.2f}",
            va="center",
            ha="left" if value >= 0 else "right",
            fontsize=6.1,
        )
    ax.set_xlim(-0.35, 0.35)
    ax.set_xlabel("Spatial correlation with O3")
    ax.set_title("(h) Bounded co-variation summary", loc="left", pad=2)
    ax.grid(axis="x", color="0.88", linewidth=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _write_source_data(rows: list[dict[str, Any]]) -> None:
    SOURCE_DATA.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["panel", "location", "lon", "lat", "value"]
    with SOURCE_DATA.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def main() -> int:
    _style()
    sa01 = _case("sa_01_real_grid_o3_peak")
    sa03 = _case("sa_03_real_grid_pm25_episode")
    sa05 = _case("sa_05_real_grid_o3_meteo_covariation")

    sa01_features = sa01["feature_metadata"]
    sa03_features = sa03["feature_metadata"]
    sa05_features = sa05["feature_metadata"]
    sa05_fields = sa05_features["spatial_fields"]

    o3_peak = _as_points(sa01_features["spatial_field"], "mda8_ppbv")
    pm25_episode = _as_points(sa03_features["spatial_field"], "episode_pm25_ugm3")
    o3_cov = _as_points(sa05_fields["o3_mda8_ppbv"], "o3_mda8_ppbv")
    t2 = _as_points(sa05_fields["t2_c"], "t2_c")
    pblh = _as_points(sa05_fields["pblh_m"], "pblh_m")
    swdown = _as_points(sa05_fields["swdown_wm2"], "swdown_wm2")

    fig = plt.figure(figsize=(7.4, 5.25), constrained_layout=False)
    gs = GridSpec(
        3,
        3,
        figure=fig,
        height_ratios=[0.78, 0.78, 0.95],
        wspace=0.46,
        hspace=0.24,
    )
    axes = {
        "a": fig.add_subplot(gs[0, 0]),
        "b": fig.add_subplot(gs[0, 1]),
        "c": fig.add_subplot(gs[0, 2]),
        "d": fig.add_subplot(gs[1, 0]),
        "e": fig.add_subplot(gs[1, 1]),
        "f": fig.add_subplot(gs[1, 2]),
        "g": fig.add_subplot(gs[2, 0:2]),
        "h": fig.add_subplot(gs[2, 2]),
    }
    fig.subplots_adjust(left=0.055, right=0.965, top=0.965, bottom=0.095)

    peak_o3 = sa01_features["location_ranking"][0]
    peak_pm25 = sa03_features["peak_point"]
    _plot_map(
        axes["a"],
        o3_peak,
        title="(a) MDA8 O3 peak",
        cmap="YlOrRd",
        colorbar_label="ppbv",
        marker={"lon": peak_o3["lon"], "lat": peak_o3["lat"]},
    )
    _plot_map(
        axes["b"],
        pm25_episode,
        title=f"(b) PM2.5 episode ({sa03_features['event_date']})",
        cmap="YlOrBr",
        colorbar_label="ug m-3",
        marker={"lon": peak_pm25["lon"], "lat": peak_pm25["lat"]},
    )
    _plot_map(
        axes["c"],
        o3_cov,
        title=f"(c) O3 high day ({sa05_features['target_date']})",
        cmap="YlOrRd",
        colorbar_label="ppbv",
    )
    _plot_map(axes["d"], t2, title="(d) 2-m temperature", cmap="YlOrBr", colorbar_label="degC")
    _plot_map(axes["e"], pblh, title="(e) Boundary-layer height", cmap="PuBuGn", colorbar_label="m")
    _plot_map(axes["f"], swdown, title="(f) Shortwave radiation", cmap="YlGnBu", colorbar_label="W m-2")
    _plot_series(axes["g"], sa03_features["domain_timeseries"], sa03_features["event_date"])
    _plot_correlations(axes["h"], sa05_features["correlations"])

    source_rows: list[dict[str, Any]] = []
    for panel, points in (
        ("a_mda8_o3_peak", o3_peak),
        ("b_pm25_episode", pm25_episode),
        ("d_o3_covariation_day", o3_cov),
        ("e_t2", t2),
        ("f_pblh", pblh),
        ("g_swdown", swdown),
    ):
        for point in points:
            source_rows.append({"panel": panel, **point})
    _write_source_data(source_rows)

    OUTPUT_STEM.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{OUTPUT_STEM}.png", dpi=600, bbox_inches="tight")
    fig.savefig(f"{OUTPUT_STEM}.pdf", bbox_inches="tight")
    fig.savefig(f"{OUTPUT_STEM}.svg", bbox_inches="tight")
    fig.savefig(f"{OUTPUT_STEM}.tiff", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(f"{OUTPUT_STEM}.png")
    print(SOURCE_DATA)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
