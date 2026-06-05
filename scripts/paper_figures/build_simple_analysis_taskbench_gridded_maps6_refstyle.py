#!/usr/bin/env python3
"""Build a six-map gridded Simple Analysis TaskBench composite figure."""

from __future__ import annotations

import argparse
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
from matplotlib.ticker import FuncFormatter
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from scipy.ndimage import zoom


REPO_ROOT = Path(__file__).resolve().parents[2]
SCORES_DIR = REPO_ROOT / "outputs" / "simple_analysis_real_gridded" / "scores" / "cases"
OUTPUT_STEM = REPO_ROOT / "paper" / "figures" / "simple_analysis_taskbench_real_gridded_maps6_refstyle"
SOURCE_DATA = (
    REPO_ROOT
    / "paper"
    / "figures"
    / "source_data"
    / "simple_analysis_taskbench_real_gridded_maps6_refstyle.csv"
)
MPL_CACHE = REPO_ROOT / "outputs" / ".paper_figure_mpl_cache"
EXTENT = {"lon_min": 111.9, "lon_max": 115.7, "lat_min": 21.7, "lat_max": 24.1}


def _style() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))
    MPL_CACHE.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.1,
            "axes.titlesize": 8.4,
            "axes.labelsize": 7.0,
            "axes.linewidth": 0.72,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
            "xtick.major.width": 0.58,
            "ytick.major.width": 0.58,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def _case(case_id: str) -> dict[str, Any]:
    return json.loads((SCORES_DIR / f"{case_id}.json").read_text(encoding="utf-8"))


def _set_paths(scores_dir: Path, output_stem: Path, source_data: Path) -> None:
    global SCORES_DIR, OUTPUT_STEM, SOURCE_DATA
    SCORES_DIR = scores_dir
    OUTPUT_STEM = output_stem
    SOURCE_DATA = source_data


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


def _cell_edges(values: np.ndarray) -> np.ndarray:
    if len(values) == 1:
        return np.asarray([values[0] - 0.1, values[0] + 0.1], dtype=float)
    midpoints = (values[:-1] + values[1:]) / 2.0
    first = values[0] - (midpoints[0] - values[0])
    last = values[-1] + (values[-1] - midpoints[-1])
    return np.concatenate(([first], midpoints, [last])).astype(float)


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
    lon_grid, lat_grid = np.meshgrid(_cell_edges(lons), _cell_edges(lats))
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


def _levels(values: np.ndarray, *, bins: int = 8) -> np.ndarray:
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


def _regular_grid_contour(
    lon_edges: np.ndarray,
    lat_edges: np.ndarray,
    values: np.ndarray,
    *,
    factor: int = 5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    refined = zoom(values, factor, order=1)
    lon = np.linspace(float(lon_edges.min()), float(lon_edges.max()), refined.shape[1])
    lat = np.linspace(float(lat_edges.min()), float(lat_edges.max()), refined.shape[0])
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    return lon_grid, lat_grid, refined


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
            LineCollection(segments, colors="#202326", linewidths=0.62, alpha=0.9, zorder=8)
        )


def _set_geo_axis(ax: Any) -> None:
    ax.set_xlim(EXTENT["lon_min"], EXTENT["lon_max"])
    ax.set_ylim(EXTENT["lat_min"], EXTENT["lat_max"])
    ax.set_xticks([112, 113, 114, 115])
    ax.set_yticks([22, 23, 24])
    ax.xaxis.set_major_formatter(FuncFormatter(_format_lon))
    ax.yaxis.set_major_formatter(FuncFormatter(_format_lat))
    ax.tick_params(length=2.7, pad=1.8)
    ax.set_aspect("auto")
    ax.set_box_aspect(0.53)
    ax.grid(False)


def _plot_map(
    ax: Any,
    points: Sequence[Mapping[str, float | str]],
    *,
    title: str,
    panel_label: str,
    cmap: str,
    colorbar_label: str,
    marker: Mapping[str, Any] | None = None,
) -> None:
    lon_grid, lat_grid, values = _grid(points)
    levels = _levels(values)
    plot_lon, plot_lat, plot_values = _regular_grid_contour(lon_grid, lat_grid, values)
    cmap_obj = mpl.colormaps.get_cmap(cmap).resampled(len(levels) - 1)
    contour = ax.contourf(
        plot_lon,
        plot_lat,
        plot_values,
        levels=levels,
        cmap=cmap_obj,
        antialiased=True,
        extend="neither",
    )
    _draw_coast(ax)
    if marker is not None:
        ax.scatter(
            [float(marker["lon"])],
            [float(marker["lat"])],
            marker=str(marker.get("marker", "*")),
            s=float(marker.get("size", 68)),
            c=str(marker.get("color", "#25D1C7")),
            edgecolors="black",
            linewidths=0.82,
            zorder=10,
        )
    _set_geo_axis(ax)
    ax.set_title(title, pad=4)
    ax.text(
        -0.12,
        1.12,
        panel_label,
        transform=ax.transAxes,
        fontsize=10.5,
        fontweight="bold",
        ha="left",
        va="bottom",
    )
    cax = inset_axes(
        ax,
        width="4.8%",
        height="100%",
        loc="center left",
        bbox_to_anchor=(1.075, 0.0, 1.0, 1.0),
        bbox_transform=ax.transAxes,
        borderpad=0,
    )
    colorbar = ax.figure.colorbar(contour, cax=cax, boundaries=levels)
    colorbar.set_label(colorbar_label, fontsize=7.0, labelpad=4)
    colorbar.ax.tick_params(labelsize=6.6, length=2.4, width=0.55, pad=1.8)


def _write_source_data(rows: list[dict[str, Any]]) -> None:
    SOURCE_DATA.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["panel", "location", "lon", "lat", "value"]
    with SOURCE_DATA.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scores-dir",
        type=Path,
        default=SCORES_DIR,
        help="Directory containing system-produced case score JSON files.",
    )
    parser.add_argument(
        "--output-stem",
        type=Path,
        default=OUTPUT_STEM,
        help="Output path without extension for PNG/PDF/SVG/TIFF exports.",
    )
    parser.add_argument(
        "--source-data",
        type=Path,
        default=SOURCE_DATA,
        help="CSV source-data export for the composite figure.",
    )
    args = parser.parse_args()
    _set_paths(args.scores_dir, args.output_stem, args.source_data)
    _style()
    sa01 = _case("sa_01_real_grid_o3_peak")
    sa03 = _case("sa_03_real_grid_pm25_episode")
    sa05 = _case("sa_05_real_grid_o3_meteo_covariation")

    sa01_features = sa01["feature_metadata"]
    sa03_features = sa03["feature_metadata"]
    sa05_features = sa05["feature_metadata"]
    sa05_fields = sa05_features["spatial_fields"]

    panels = [
        {
            "key": "a_mda8_o3_peak",
            "points": _as_points(sa01_features["spatial_field"], "mda8_ppbv"),
            "title": "SA-01 MDA8 O$_3$ peak",
            "label": "a",
            "cmap": "YlOrRd",
            "cbar": "MDA8 O$_3$ (ppbv)",
            "marker": sa01_features["location_ranking"][0],
        },
        {
            "key": "b_pm25_episode",
            "points": _as_points(sa03_features["spatial_field"], "episode_pm25_ugm3"),
            "title": f"SA-03 PM$_{{2.5}}$ episode ({sa03_features['event_date']})",
            "label": "b",
            "cmap": "YlOrBr",
            "cbar": "PM$_{2.5}$ (ug m$^{-3}$)",
            "marker": sa03_features["peak_point"],
        },
        {
            "key": "c_o3_high_day",
            "points": _as_points(sa05_fields["o3_mda8_ppbv"], "o3_mda8_ppbv"),
            "title": f"SA-05 O$_3$ high day ({sa05_features['target_date']})",
            "label": "c",
            "cmap": "YlOrRd",
            "cbar": "MDA8 O$_3$ (ppbv)",
            "marker": None,
        },
        {
            "key": "d_t2",
            "points": _as_points(sa05_fields["t2_c"], "t2_c"),
            "title": "SA-05 2-m temperature",
            "label": "d",
            "cmap": "YlOrBr",
            "cbar": "T2 (degC)",
            "marker": None,
        },
        {
            "key": "e_pblh",
            "points": _as_points(sa05_fields["pblh_m"], "pblh_m"),
            "title": "SA-05 boundary-layer height",
            "label": "e",
            "cmap": "PuBuGn",
            "cbar": "PBLH (m)",
            "marker": None,
        },
        {
            "key": "f_swdown",
            "points": _as_points(sa05_fields["swdown_wm2"], "swdown_wm2"),
            "title": "SA-05 shortwave radiation",
            "label": "f",
            "cmap": "YlGnBu",
            "cbar": "SWDOWN (W m$^{-2}$)",
            "marker": None,
        },
    ]

    fig, axes = plt.subplots(3, 2, figsize=(7.6, 7.15), constrained_layout=False)
    fig.subplots_adjust(left=0.07, right=0.93, top=0.965, bottom=0.075, wspace=0.42, hspace=0.52)
    source_rows: list[dict[str, Any]] = []
    for ax, panel in zip(axes.ravel(), panels, strict=True):
        marker = panel["marker"]
        _plot_map(
            ax,
            panel["points"],
            title=str(panel["title"]),
            panel_label=str(panel["label"]),
            cmap=str(panel["cmap"]),
            colorbar_label=str(panel["cbar"]),
            marker=marker if isinstance(marker, Mapping) else None,
        )
        for point in panel["points"]:
            source_rows.append({"panel": panel["key"], **point})
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
