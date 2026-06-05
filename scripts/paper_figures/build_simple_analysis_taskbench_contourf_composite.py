#!/usr/bin/env python3
"""Build a contourf-style Simple Analysis TaskBench composite figure."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from scipy.ndimage import gaussian_filter


REPO_ROOT = Path(__file__).resolve().parents[2]
SCORES_DIR = REPO_ROOT / "outputs" / "simple_analysis_real" / "scores" / "cases"
OUTPUT_STEM = REPO_ROOT / "paper" / "figures" / "simple_analysis_taskbench_real_composite_contourf_refstyle"
MPL_CACHE = REPO_ROOT / "outputs" / ".paper_figure_mpl_cache"
MAP_ASPECT = 1.88


def _style() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))
    MPL_CACHE.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.2,
            "axes.titlesize": 8.0,
            "axes.labelsize": 7.2,
            "axes.linewidth": 0.75,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def _case(case_id: str) -> dict[str, Any]:
    return json.loads((SCORES_DIR / f"{case_id}.json").read_text(encoding="utf-8"))


def _points(
    items: Sequence[Mapping[str, Any]],
    value_key: str,
) -> list[dict[str, float | str]]:
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


def _extent(points: Sequence[Mapping[str, float | str]], pad_fraction: float = 0.07) -> dict[str, float]:
    lon = np.asarray([float(item["lon"]) for item in points])
    lat = np.asarray([float(item["lat"]) for item in points])
    lon_span = max(float(lon.max() - lon.min()), 0.4)
    lat_span = max(float(lat.max() - lat.min()), 0.4)
    lon_min = float(lon.min() - lon_span * pad_fraction)
    lon_max = float(lon.max() + lon_span * pad_fraction)
    lat_min = float(lat.min() - lat_span * pad_fraction)
    lat_max = float(lat.max() + lat_span * pad_fraction)
    center_lon = (lon_min + lon_max) / 2.0
    center_lat = (lat_min + lat_max) / 2.0
    padded_lon_span = lon_max - lon_min
    padded_lat_span = lat_max - lat_min
    current_aspect = padded_lon_span / padded_lat_span
    if current_aspect < MAP_ASPECT:
        padded_lon_span = padded_lat_span * MAP_ASPECT
    elif current_aspect > MAP_ASPECT:
        padded_lat_span = padded_lon_span / MAP_ASPECT
    return {
        "lon_min": float(center_lon - padded_lon_span / 2.0),
        "lon_max": float(center_lon + padded_lon_span / 2.0),
        "lat_min": float(center_lat - padded_lat_span / 2.0),
        "lat_max": float(center_lat + padded_lat_span / 2.0),
    }


def _idw_grid(
    points: Sequence[Mapping[str, float | str]],
    *,
    grid_size: int = 180,
    smooth_sigma: float = 3.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ext = _extent(points)
    x = np.asarray([float(item["lon"]) for item in points])
    y = np.asarray([float(item["lat"]) for item in points])
    z = np.asarray([float(item["value"]) for item in points])
    gx = np.linspace(ext["lon_min"], ext["lon_max"], grid_size)
    gy = np.linspace(ext["lat_min"], ext["lat_max"], grid_size)
    grid_x, grid_y = np.meshgrid(gx, gy)
    distance = np.sqrt((grid_x[..., None] - x) ** 2 + (grid_y[..., None] - y) ** 2)
    weights = 1.0 / np.maximum(distance, 1e-6) ** 2
    grid_z = np.sum(weights * z, axis=2) / np.sum(weights, axis=2)
    if smooth_sigma > 0:
        grid_z = gaussian_filter(grid_z, sigma=smooth_sigma, mode="nearest")
    return grid_x, grid_y, grid_z


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


def _levels(values: np.ndarray, *, diverging: bool, bins: int = 10) -> np.ndarray:
    vmin = float(np.nanmin(values))
    vmax = float(np.nanmax(values))
    if diverging:
        bound = max(abs(vmin), abs(vmax), 1e-9)
        step = _nice_step(bound / (bins / 2))
        nice_bound = np.ceil(bound / step) * step
        return np.arange(-nice_bound, nice_bound + step * 0.5, step)
    step = _nice_step((vmax - vmin) / bins)
    nice_min = np.floor(vmin / step) * step
    nice_max = np.ceil(vmax / step) * step
    return np.arange(nice_min, nice_max + step * 0.5, step)


def _format_lon(value: float, _pos: int | None = None) -> str:
    hemi = "E" if value >= 0 else "W"
    absolute = abs(value)
    label = f"{absolute:.0f}" if np.isclose(absolute, round(absolute)) else f"{absolute:.1f}"
    return f"{label}°{hemi}"


def _format_lat(value: float, _pos: int | None = None) -> str:
    hemi = "N" if value >= 0 else "S"
    absolute = abs(value)
    label = f"{absolute:.0f}" if np.isclose(absolute, round(absolute)) else f"{absolute:.1f}"
    return f"{label}°{hemi}"


def _set_ticks(ax: Any, ext: Mapping[str, float]) -> None:
    lon_span = float(ext["lon_max"] - ext["lon_min"])
    lat_span = float(ext["lat_max"] - ext["lat_min"])
    lon_step = 10 if lon_span > 12 else 1
    lat_step = 10 if lat_span > 12 else 1
    lon_start = np.ceil(float(ext["lon_min"]) / lon_step) * lon_step
    lon_end = np.floor(float(ext["lon_max"]) / lon_step) * lon_step
    lat_start = np.ceil(float(ext["lat_min"]) / lat_step) * lat_step
    lat_end = np.floor(float(ext["lat_max"]) / lat_step) * lat_step
    ax.set_xticks(np.arange(lon_start, lon_end + lon_step * 0.5, lon_step))
    ax.set_yticks(np.arange(lat_start, lat_end + lat_step * 0.5, lat_step))
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(_format_lon))
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(_format_lat))
    ax.tick_params(length=3.2, width=0.75, pad=2)


@lru_cache(maxsize=1)
def _coastlines() -> tuple[tuple[tuple[float, float], ...], ...]:
    try:
        import cartopy.io.shapereader as shapereader
    except Exception:
        return ()
    path = shapereader.natural_earth(resolution="10m", category="physical", name="coastline")
    segments: list[tuple[tuple[float, float], ...]] = []
    for geometry in shapereader.Reader(path).geometries():
        geom_type = getattr(geometry, "geom_type", "")
        geoms = geometry.geoms if geom_type == "MultiLineString" else [geometry]
        for part in geoms:
            if getattr(part, "geom_type", "") != "LineString":
                continue
            coords = tuple((float(x), float(y)) for x, y, *_ in part.coords)
            if len(coords) >= 2:
                segments.append(coords)
    return tuple(segments)


def _draw_coast(ax: Any, ext: Mapping[str, float]) -> None:
    segments = []
    for segment in _coastlines():
        xs = [p[0] for p in segment]
        ys = [p[1] for p in segment]
        if (
            max(xs) < ext["lon_min"]
            or min(xs) > ext["lon_max"]
            or max(ys) < ext["lat_min"]
            or min(ys) > ext["lat_max"]
        ):
            continue
        segments.append(segment)
    if segments:
        ax.add_collection(
            LineCollection(segments, colors="#111111", linewidths=0.65, alpha=0.90, zorder=6)
        )


def _panel(
    ax: Any,
    cax: Any,
    points: Sequence[Mapping[str, float | str]],
    *,
    title: str,
    cmap: str,
    diverging: bool,
    label: str,
    marker_points: Sequence[Mapping[str, Any]] = (),
    smooth_sigma: float = 3.0,
    show_isolines: bool = False,
    cbar_side: str = "right",
) -> None:
    grid_x, grid_y, grid_z = _idw_grid(points, smooth_sigma=smooth_sigma)
    levels = _levels(grid_z, diverging=diverging)
    contour = ax.contourf(
        grid_x,
        grid_y,
        grid_z,
        levels=levels,
        cmap=cmap,
        extend="both" if diverging else "neither",
        antialiased=True,
    )
    if show_isolines:
        contour_levels = levels[(levels > levels.min()) & (levels < levels.max())]
        ax.contour(
            grid_x,
            grid_y,
            grid_z,
            levels=contour_levels[::2],
            colors="white",
            linewidths=0.42,
            alpha=0.42,
        )
    ext = _extent(points)
    _draw_coast(ax, ext)
    for marker in marker_points:
        ax.scatter(
            [float(marker["lon"])],
            [float(marker["lat"])],
            marker=str(marker.get("marker", "*")),
            s=float(marker.get("size", 70)),
            c=str(marker.get("color", "cyan")),
            edgecolors="black",
            linewidths=0.75,
            zorder=8,
        )
        if marker.get("text"):
            ax.text(
                float(marker["lon"]) + (ext["lon_max"] - ext["lon_min"]) * 0.02,
                float(marker["lat"]) + (ext["lat_max"] - ext["lat_min"]) * 0.03,
                str(marker["text"]),
                fontsize=5.8,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 1.0},
                zorder=9,
            )
    ax.set_title(title, pad=3)
    ax.set_xlim(ext["lon_min"], ext["lon_max"])
    ax.set_ylim(ext["lat_min"], ext["lat_max"])
    ax.set_aspect("equal", adjustable="box")
    ax.set_box_aspect(1.0 / MAP_ASPECT)
    _set_ticks(ax, ext)
    ax.set_xlabel("")
    ax.set_ylabel("")
    cbar = ax.figure.colorbar(
        contour,
        cax=cax,
        orientation="vertical",
        aspect=18,
    )
    cbar.set_label(label, fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.2, length=2.5, width=0.5)
    if cbar_side == "left":
        cbar.ax.yaxis.set_ticks_position("left")
        cbar.ax.yaxis.set_label_position("left")
        cbar.ax.yaxis.labelpad = 4
    tick_levels = levels[:: max(1, len(levels) // 5)]
    cbar.set_ticks(tick_levels)


def main() -> None:
    _style()
    sa01 = _case("sa_01_real_openmeteo_prd_o3_peak")
    sa03 = _case("sa_03_real_openmeteo_prd_mda8_delta")
    sa05 = _case("sa_05_real_openmeteo_o3_meteo_chain")

    sa01_points = _points(sa01["feature_metadata"]["spatial_field"], "mda8_ppbv")
    peak = sa01["feature_metadata"]["location_ranking"][0]
    sa03_points = _points(sa03["derived_metrics"]["spatial_delta_field"], "delta_mda8_ppbv")
    decrease = sa03["feature_metadata"]["largest_decrease"]
    increase = sa03["feature_metadata"]["largest_increase"]
    spatial_fields = sa05["feature_metadata"]["spatial_fields"]

    fig = plt.figure(figsize=(8.95, 6.95), constrained_layout=False)
    outer = fig.add_gridspec(
        3,
        4,
        width_ratios=[1.0, 0.052, 1.0, 0.052],
        height_ratios=[1.0, 1.0, 1.0],
        hspace=0.38,
        wspace=0.30,
    )
    axes = [fig.add_subplot(outer[row, col]) for row, col in [(0, 0), (0, 2), (1, 0), (1, 2), (2, 0), (2, 2)]]
    caxes = [fig.add_subplot(outer[row, col]) for row, col in [(0, 1), (0, 3), (1, 1), (1, 3), (2, 1), (2, 3)]]
    ax_a, ax_b, ax_c1, ax_c2, ax_c3, ax_c4 = axes

    _panel(
        ax_a,
        caxes[0],
        sa01_points,
        title="SA-01 MDA8 O$_3$ peak",
        cmap="YlOrRd",
        diverging=False,
        label="MDA8 O$_3$ (ppbv)",
        marker_points=[
            {
                "lon": peak["lon"],
                "lat": peak["lat"],
                "marker": "*",
                "size": 78,
                "color": "#13D4E7",
                "text": "",
            }
        ],
        smooth_sigma=3.4,
        cbar_side="left",
    )
    _panel(
        ax_b,
        caxes[1],
        sa03_points,
        title="SA-03 $\\Delta$MDA8 O$_3$",
        cmap="RdBu_r",
        diverging=True,
        label=r"$\Delta$MDA8 O$_3$ (ppbv)",
        marker_points=[
            {
                "lon": decrease["lon"],
                "lat": decrease["lat"],
                "marker": "v",
                "size": 58,
                "color": "white",
                "text": "",
            },
            {
                "lon": increase["lon"],
                "lat": increase["lat"],
                "marker": "^",
                "size": 58,
                "color": "white",
                "text": "",
            },
        ],
        smooth_sigma=2.2,
        cbar_side="right",
    )

    c_panels = [
        (ax_c1, caxes[2], "delta_o3_ppbv", "SA-05 $\\Delta$O$_3$", "ppbv"),
        (ax_c2, caxes[3], "delta_t2_k", "SA-05 $\\Delta$T2", "K"),
        (ax_c3, caxes[4], "delta_pblh_m", "SA-05 $\\Delta$PBLH", "m"),
        (ax_c4, caxes[5], "delta_swdown_wm2", "SA-05 $\\Delta$SWDOWN", "W m$^{-2}$"),
    ]
    for ax, cax, key, title, label in c_panels:
        _panel(
            ax,
            cax,
            _points(spatial_fields[key], key),
            title=title,
            cmap="RdBu_r",
            diverging=True,
            label=label,
            smooth_sigma=3.0,
            cbar_side="left" if ax in {ax_c1, ax_c3} else "right",
        )

    for label, ax in zip(["a", "b", "c", "d", "e", "f"], axes, strict=True):
        ax.text(
            -0.11,
            1.11,
            label,
            transform=ax.transAxes,
            fontsize=11,
            fontweight="bold",
            ha="left",
            va="bottom",
        )

    OUTPUT_STEM.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{OUTPUT_STEM}.png", dpi=600, bbox_inches="tight")
    fig.savefig(f"{OUTPUT_STEM}.pdf", bbox_inches="tight")
    fig.savefig(f"{OUTPUT_STEM}.svg", bbox_inches="tight")
    fig.savefig(f"{OUTPUT_STEM}.tiff", dpi=600, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
