#!/usr/bin/env python3
"""
Sprite Sheet Processor V4 for TinyRoommate

This is the canonical and only supported sprite-sheet processor.

V4 switches to HSV-based background detection instead of the older
"red/blue high, green low" heuristic. That matters for dark-furred
animals: black mouths, brown noses, and deep shadow shapes should not
be mistaken for magenta spill just because they have low green.

This version:
1. slices a fixed grid,
2. removes only border-connected pixels that are truly magenta-like in HSV,
3. de-spills only magenta-hued edge contamination,
4. rescales the full cell into the target output frame.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process a magenta-background sprite sheet")
    parser.add_argument("input", help="Input PNG/JPG sprite sheet")
    parser.add_argument("-o", "--output", required=True, help="Output PNG path")
    parser.add_argument("--name", default="Unnamed Sprite", help="Human-readable sprite name")
    parser.add_argument("--cols", type=int, default=8, help="Number of columns in source sheet")
    parser.add_argument("--rows", type=int, required=True, help="Number of rows in source sheet")
    parser.add_argument("--target", type=int, default=128, help="Output frame size in pixels")
    parser.add_argument(
        "--bg-hue-center",
        type=float,
        default=0.86,
        help="Hue center for the keyed background in HSV space (magenta ~= 0.83-0.88)",
    )
    parser.add_argument(
        "--bg-hue-tolerance",
        type=float,
        default=0.11,
        help="Allowed hue distance around the background center",
    )
    parser.add_argument(
        "--bg-min-saturation",
        type=float,
        default=0.42,
        help="Minimum saturation for a pixel to count as magenta background",
    )
    parser.add_argument(
        "--bg-min-value",
        type=float,
        default=0.45,
        help="Minimum brightness/value for a pixel to count as magenta background",
    )
    parser.add_argument(
        "--spill-min-saturation",
        type=float,
        default=0.22,
        help="Minimum saturation before edge despill considers a pixel contaminated",
    )
    parser.add_argument(
        "--spill-min-value",
        type=float,
        default=0.20,
        help="Minimum value before edge despill considers a pixel contaminated",
    )
    parser.add_argument(
        "--hard-purge-saturation",
        type=float,
        default=0.5,
        help="Minimum saturation for fully removing obvious leftover magenta after layout",
    )
    parser.add_argument(
        "--hard-purge-value",
        type=float,
        default=0.52,
        help="Minimum value for fully removing obvious leftover magenta after layout",
    )
    parser.add_argument(
        "--soft-purge-saturation",
        type=float,
        default=0.32,
        help="Minimum saturation for fading medium leftover magenta after layout",
    )
    parser.add_argument(
        "--soft-purge-value",
        type=float,
        default=0.34,
        help="Minimum value for fading medium leftover magenta after layout",
    )
    parser.add_argument(
        "--edge-search",
        type=int,
        default=25,
        help="Pixels to search around each nominal grid edge to find the emptiest gutter",
    )
    parser.add_argument(
        "--border-clean",
        type=int,
        default=3,
        help="Clear magenta-like separator fragments within this many pixels of each cell border",
    )
    parser.add_argument(
        "--line-search-band",
        type=int,
        default=18,
        help="How far from each cell edge to search for long separator lines",
    )
    parser.add_argument(
        "--line-coverage",
        type=float,
        default=0.35,
        help="Required row/column coverage before a magenta trace is treated as a separator line",
    )
    parser.add_argument(
        "--artifact-search-band",
        type=int,
        default=18,
        help="How far from each cell edge to search for detached border-line artifacts",
    )
    parser.add_argument(
        "--artifact-max-thickness",
        type=int,
        default=4,
        help="Maximum thickness for a detached border artifact component",
    )
    parser.add_argument(
        "--artifact-min-length",
        type=int,
        default=12,
        help="Minimum length for a detached border artifact component",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(input_path).convert("RGBA")
    width, height = img.size
    rgb = np.array(img[:, :, :3] if isinstance(img, np.ndarray) else img)[..., :3]
    x_edges = refined_grid_edges(
        rgb,
        count=args.cols,
        axis=1,
        bg_hue_center=args.bg_hue_center,
        bg_hue_tolerance=args.bg_hue_tolerance,
        bg_min_saturation=args.bg_min_saturation,
        bg_min_value=args.bg_min_value,
        search_radius=args.edge_search,
    )
    y_edges = refined_grid_edges(
        rgb,
        count=args.rows,
        axis=0,
        bg_hue_center=args.bg_hue_center,
        bg_hue_tolerance=args.bg_hue_tolerance,
        bg_min_saturation=args.bg_min_saturation,
        bg_min_value=args.bg_min_value,
        search_radius=args.edge_search,
    )

    print(f"Name: {args.name}")
    print(f"Source: {input_path}")
    print(f"Size: {width}x{height}")
    print(f"Grid: {args.cols}x{args.rows}")
    print(f"X edges: {x_edges}")
    print(f"Y edges: {y_edges}")

    out = Image.new("RGBA", (args.cols * args.target, args.rows * args.target), (0, 0, 0, 0))

    for row in range(args.rows):
        for col in range(args.cols):
            x0, x1 = x_edges[col], x_edges[col + 1]
            y0, y1 = y_edges[row], y_edges[row + 1]
            cell = img.crop((x0, y0, x1, y1))
            processed = process_cell(
                cell,
                target=args.target,
                bg_hue_center=args.bg_hue_center,
                bg_hue_tolerance=args.bg_hue_tolerance,
                bg_min_saturation=args.bg_min_saturation,
                bg_min_value=args.bg_min_value,
                spill_min_saturation=args.spill_min_saturation,
                spill_min_value=args.spill_min_value,
                border_clean=args.border_clean,
                line_search_band=args.line_search_band,
                line_coverage=args.line_coverage,
                artifact_search_band=args.artifact_search_band,
                artifact_max_thickness=args.artifact_max_thickness,
                artifact_min_length=args.artifact_min_length,
            )
            out.alpha_composite(processed, (col * args.target, row * args.target))

        print(f"  Row {row + 1}/{args.rows} done")

    out = purge_remaining_magenta(
        out,
        bg_hue_center=args.bg_hue_center,
        bg_hue_tolerance=args.bg_hue_tolerance,
        hard_purge_saturation=args.hard_purge_saturation,
        hard_purge_value=args.hard_purge_value,
        soft_purge_saturation=args.soft_purge_saturation,
        soft_purge_value=args.soft_purge_value,
    )
    out = cleanup_output_frames(
        out,
        cols=args.cols,
        rows=args.rows,
        frame_size=args.target,
        bg_hue_center=args.bg_hue_center,
        bg_hue_tolerance=args.bg_hue_tolerance,
    )
    out.save(output_path)
    print(f"Saved: {output_path}")
    print(f"Output size: {out.width}x{out.height}")


def grid_edges(total: int, count: int) -> list[int]:
    return [round(i * total / count) for i in range(count + 1)]


def cleanup_output_frames(
    img: Image.Image,
    *,
    cols: int,
    rows: int,
    frame_size: int,
    bg_hue_center: float,
    bg_hue_tolerance: float,
) -> Image.Image:
    arr = np.array(img, dtype=np.uint8)
    search_band = max(6, frame_size // 10)
    max_thickness = max(2, frame_size // 32)
    min_length = max(8, frame_size // 10)

    for row in range(rows):
        for col in range(cols):
            y0 = row * frame_size
            y1 = y0 + frame_size
            x0 = col * frame_size
            x1 = x0 + frame_size
            frame = arr[y0:y1, x0:x1]
            frame = remove_line_components(
                frame,
                search_band=search_band,
                hue_center=bg_hue_center,
                hue_tolerance=bg_hue_tolerance,
                min_saturation=0.16,
                min_value=0.08,
            )
            frame = remove_border_magenta_runs(
                frame,
                search_band=search_band,
                min_run_length=max(8, frame_size // 12),
                max_thickness=max_thickness,
                hue_center=bg_hue_center,
                hue_tolerance=bg_hue_tolerance,
                min_saturation=0.16,
                min_value=0.08,
            )
            frame = despill_border_tint(
                frame,
                search_band=search_band,
                hue_center=bg_hue_center,
                hue_tolerance=bg_hue_tolerance,
                min_saturation=0.16,
                min_value=0.08,
            )
            frame = remove_border_artifact_components(
                frame,
                search_band=search_band,
                max_thickness=max_thickness,
                min_length=min_length,
            )
            arr[y0:y1, x0:x1] = frame

    return Image.fromarray(arr, mode="RGBA")


def refined_grid_edges(
    rgb: np.ndarray,
    *,
    count: int,
    axis: int,
    bg_hue_center: float,
    bg_hue_tolerance: float,
    bg_min_saturation: float,
    bg_min_value: float,
    search_radius: int,
) -> list[int]:
    total = rgb.shape[1] if axis == 1 else rgb.shape[0]
    nominal = grid_edges(total, count)
    bg_like = background_candidate_mask(
        rgb,
        bg_hue_center=bg_hue_center,
        bg_hue_tolerance=bg_hue_tolerance,
        bg_min_saturation=bg_min_saturation,
        bg_min_value=bg_min_value,
    )
    content = ~bg_like
    density = content.sum(axis=0 if axis == 1 else 1)

    edges = [0]
    for i in range(1, count):
        center = nominal[i]
        lo = max(edges[-1] + 1, center - search_radius)
        hi = min(total - 1, center + search_radius)
        window = list(range(lo, hi + 1))
        min_density = min(int(density[idx]) for idx in window)
        candidates = [idx for idx in window if int(density[idx]) == min_density]
        best = min(candidates, key=lambda idx: abs(idx - center))
        edges.append(best)
    edges.append(total)
    return edges


def background_candidate_mask(
    rgb: np.ndarray,
    *,
    bg_hue_center: float,
    bg_hue_tolerance: float,
    bg_min_saturation: float,
    bg_min_value: float,
) -> np.ndarray:
    return magenta_hsv_mask(
        rgb,
        hue_center=bg_hue_center,
        hue_tolerance=bg_hue_tolerance,
        min_saturation=bg_min_saturation,
        min_value=bg_min_value,
    )


def process_cell(
    cell: Image.Image,
    *,
    target: int,
    bg_hue_center: float,
    bg_hue_tolerance: float,
    bg_min_saturation: float,
    bg_min_value: float,
    spill_min_saturation: float,
    spill_min_value: float,
    border_clean: int,
    line_search_band: int,
    line_coverage: float,
    artifact_search_band: int,
    artifact_max_thickness: int,
    artifact_min_length: int,
) -> Image.Image:
    arr = np.array(cell, dtype=np.uint8)
    bg = border_connected_background(
        arr[:, :, :3],
        bg_hue_center=bg_hue_center,
        bg_hue_tolerance=bg_hue_tolerance,
        bg_min_saturation=bg_min_saturation,
        bg_min_value=bg_min_value,
    )
    arr[bg, 3] = 0
    arr = clear_cell_border_gutter(
        arr,
        border=border_clean,
        hue_center=bg_hue_center,
        hue_tolerance=bg_hue_tolerance * 0.9,
        min_saturation=max(0.35, bg_min_saturation * 0.85),
        min_value=max(0.35, bg_min_value * 0.8),
    )
    arr = strip_separator_lines(
        arr,
        search_band=line_search_band,
        coverage=line_coverage,
        hue_center=bg_hue_center,
        hue_tolerance=bg_hue_tolerance,
        min_saturation=max(0.34, bg_min_saturation * 0.82),
        min_value=max(0.34, bg_min_value * 0.78),
    )
    arr = remove_line_components(
        arr,
        search_band=max(line_search_band, border_clean + 8),
        hue_center=bg_hue_center,
        hue_tolerance=bg_hue_tolerance,
        min_saturation=max(0.34, bg_min_saturation * 0.82),
        min_value=max(0.34, bg_min_value * 0.78),
    )
    arr = remove_border_artifact_components(
        arr,
        search_band=artifact_search_band,
        max_thickness=artifact_max_thickness,
        min_length=artifact_min_length,
    )
    arr = despill_edges(
        arr,
        bg,
        hue_center=bg_hue_center,
        hue_tolerance=bg_hue_tolerance * 1.1,
        min_saturation=spill_min_saturation,
        min_value=spill_min_value,
    )
    resized = np.array(Image.fromarray(arr, mode="RGBA").resize((target, target), Image.LANCZOS), dtype=np.uint8)
    resized = remove_border_artifact_components(
        resized,
        search_band=max(6, target // 10),
        max_thickness=max(2, target // 32),
        min_length=max(8, target // 10),
    )
    return Image.fromarray(resized, mode="RGBA")


def border_connected_background(
    rgb: np.ndarray,
    *,
    bg_hue_center: float,
    bg_hue_tolerance: float,
    bg_min_saturation: float,
    bg_min_value: float,
) -> np.ndarray:
    h, w = rgb.shape[:2]
    bg = np.zeros((h, w), dtype=bool)
    bg_like = magenta_hsv_mask(
        rgb,
        hue_center=bg_hue_center,
        hue_tolerance=bg_hue_tolerance,
        min_saturation=bg_min_saturation,
        min_value=bg_min_value,
    )
    queue: deque[tuple[int, int]] = deque()

    def candidate(x: int, y: int) -> bool:
        return bool(bg_like[y, x])

    def push(x: int, y: int) -> None:
        if 0 <= x < w and 0 <= y < h and not bg[y, x] and candidate(x, y):
            bg[y, x] = True
            queue.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    while queue:
        x, y = queue.popleft()
        push(x + 1, y)
        push(x - 1, y)
        push(x, y + 1)
        push(x, y - 1)

    return bg


def despill_edges(
    arr: np.ndarray,
    bg: np.ndarray,
    *,
    hue_center: float,
    hue_tolerance: float,
    min_saturation: float,
    min_value: float,
) -> np.ndarray:
    out = arr.copy()
    alpha = out[:, :, 3]
    fg = alpha > 0
    if not np.any(fg):
        return out

    neighbor_bg = np.zeros_like(bg)
    neighbor_bg[1:, :] |= bg[:-1, :]
    neighbor_bg[:-1, :] |= bg[1:, :]
    neighbor_bg[:, 1:] |= bg[:, :-1]
    neighbor_bg[:, :-1] |= bg[:, 1:]

    edge = fg & neighbor_bg
    if not np.any(edge):
        return out

    rgb = out[:, :, :3].astype(np.uint8)
    spill_like = magenta_hsv_mask(
        rgb,
        hue_center=hue_center,
        hue_tolerance=hue_tolerance,
        min_saturation=min_saturation,
        min_value=min_value,
    )
    borrow = edge & spill_like
    if not np.any(borrow):
        return out

    clean = fg & (~spill_like)
    out = borrow_clean_edge_colors(out, spill=borrow, clean=clean, bg=bg)

    # A second pass gently neutralizes any residual magenta tint without dropping alpha.
    rgb = out[:, :, :3].astype(np.uint8)
    residual = edge & magenta_hsv_mask(
        rgb,
        hue_center=hue_center,
        hue_tolerance=hue_tolerance * 0.9,
        min_saturation=min_saturation,
        min_value=min_value,
    )
    if np.any(residual):
        rgb16 = out[:, :, :3].astype(np.int16)
        rgb16[:, :, 0][residual] = np.maximum(rgb16[:, :, 0][residual] - 24, 0)
        rgb16[:, :, 2][residual] = np.maximum(rgb16[:, :, 2][residual] - 24, 0)
        out[:, :, :3] = rgb16.astype(np.uint8)
    return out


def clear_cell_border_gutter(
    arr: np.ndarray,
    *,
    border: int,
    hue_center: float,
    hue_tolerance: float,
    min_saturation: float,
    min_value: float,
) -> np.ndarray:
    if border <= 0:
        return arr

    out = arr.copy()
    h, w = out.shape[:2]
    mask = np.zeros((h, w), dtype=bool)
    border = min(border, h // 2, w // 2)
    mask[:border, :] = True
    mask[h - border:, :] = True
    mask[:, :border] = True
    mask[:, w - border:] = True

    magenta_like = magenta_hsv_mask(
        out[:, :, :3],
        hue_center=hue_center,
        hue_tolerance=hue_tolerance,
        min_saturation=min_saturation,
        min_value=min_value,
    )
    out[mask & magenta_like, 3] = 0
    return out


def strip_separator_lines(
    arr: np.ndarray,
    *,
    search_band: int,
    coverage: float,
    hue_center: float,
    hue_tolerance: float,
    min_saturation: float,
    min_value: float,
) -> np.ndarray:
    if search_band <= 0:
        return arr

    out = arr.copy()
    h, w = out.shape[:2]
    search_band = min(search_band, h // 2, w // 2)
    magenta_like = magenta_hsv_mask(
        out[:, :, :3],
        hue_center=hue_center,
        hue_tolerance=hue_tolerance,
        min_saturation=min_saturation,
        min_value=min_value,
    )

    rows_to_clear = np.zeros(h, dtype=bool)
    cols_to_clear = np.zeros(w, dtype=bool)

    row_counts = magenta_like.sum(axis=1)
    col_counts = magenta_like.sum(axis=0)

    row_threshold = max(6, int(w * coverage))
    col_threshold = max(6, int(h * coverage))

    rows_to_clear[:search_band] = row_counts[:search_band] >= row_threshold
    rows_to_clear[h - search_band:] = row_counts[h - search_band:] >= row_threshold
    cols_to_clear[:search_band] = col_counts[:search_band] >= col_threshold
    cols_to_clear[w - search_band:] = col_counts[w - search_band:] >= col_threshold

    if np.any(rows_to_clear):
        expanded_rows = rows_to_clear.copy()
        expanded_rows[1:] |= rows_to_clear[:-1]
        expanded_rows[:-1] |= rows_to_clear[1:]
        out[expanded_rows, :, 3] = np.where(magenta_like[expanded_rows], 0, out[expanded_rows, :, 3])

    if np.any(cols_to_clear):
        expanded_cols = cols_to_clear.copy()
        expanded_cols[1:] |= cols_to_clear[:-1]
        expanded_cols[:-1] |= cols_to_clear[1:]
        out[:, expanded_cols, 3] = np.where(magenta_like[:, expanded_cols], 0, out[:, expanded_cols, 3])

    return out


def remove_line_components(
    arr: np.ndarray,
    *,
    search_band: int,
    hue_center: float,
    hue_tolerance: float,
    min_saturation: float,
    min_value: float,
) -> np.ndarray:
    out = arr.copy()
    h, w = out.shape[:2]
    search_band = min(search_band, h // 2, w // 2)
    if search_band <= 0:
      return out

    alpha = out[:, :, 3] > 0
    magenta_like = alpha & magenta_hsv_mask(
        out[:, :, :3],
        hue_center=hue_center,
        hue_tolerance=hue_tolerance,
        min_saturation=min_saturation,
        min_value=min_value,
    )
    if not np.any(magenta_like):
        return out

    visited = np.zeros_like(magenta_like, dtype=bool)
    for sy, sx in np.argwhere(magenta_like):
        if visited[sy, sx]:
            continue

        stack = [(int(sy), int(sx))]
        component = []
        visited[sy, sx] = True

        min_x = max_x = int(sx)
        min_y = max_y = int(sy)

        while stack:
            y, x = stack.pop()
            component.append((y, x))
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h and magenta_like[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    stack.append((ny, nx))

        comp_w = max_x - min_x + 1
        comp_h = max_y - min_y + 1
        area = len(component)
        near_border = (
            min_x < search_band or max_x >= w - search_band or
            min_y < search_band or max_y >= h - search_band
        )
        horizontal = comp_w >= 8 and comp_h <= 3 and area >= 8
        vertical = comp_h >= 8 and comp_w <= 3 and area >= 8

        if near_border and (horizontal or vertical):
            for y, x in component:
                out[y, x, 3] = 0

    return out


def remove_border_artifact_components(
    arr: np.ndarray,
    *,
    search_band: int,
    max_thickness: int,
    min_length: int,
) -> np.ndarray:
    out = arr.copy()
    alpha = out[:, :, 3] > 0
    h, w = alpha.shape
    if not np.any(alpha):
        return out

    search_band = min(search_band, h // 2, w // 2)
    max_thickness = max(1, max_thickness)
    min_length = max(2, min_length)
    if search_band <= 0:
        return out

    visited = np.zeros_like(alpha, dtype=bool)
    starts = np.argwhere(alpha)

    for sy, sx in starts:
        sy = int(sy)
        sx = int(sx)
        if visited[sy, sx]:
            continue

        stack = [(sy, sx)]
        visited[sy, sx] = True
        component: list[tuple[int, int]] = []
        min_x = max_x = sx
        min_y = max_y = sy

        while stack:
            y, x = stack.pop()
            component.append((y, x))
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and alpha[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    stack.append((ny, nx))

        comp_w = max_x - min_x + 1
        comp_h = max_y - min_y + 1
        thickness = min(comp_w, comp_h)
        length = max(comp_w, comp_h)
        area = len(component)
        near_border = (
            min_x < search_band
            or max_x >= w - search_band
            or min_y < search_band
            or max_y >= h - search_band
        )
        elongated = length >= min_length and length >= thickness * 4
        thin = thickness <= max_thickness
        sparse_enough = area <= length * max(max_thickness, 2)

        if near_border and elongated and thin and sparse_enough:
            for y, x in component:
                out[y, x, 3] = 0

    return out


def remove_border_magenta_runs(
    arr: np.ndarray,
    *,
    search_band: int,
    min_run_length: int,
    max_thickness: int,
    hue_center: float,
    hue_tolerance: float,
    min_saturation: float,
    min_value: float,
) -> np.ndarray:
    out = arr.copy()
    alpha = out[:, :, 3] > 0
    h, w = alpha.shape
    if not np.any(alpha):
        return out

    search_band = min(search_band, h // 2, w // 2)
    if search_band <= 0:
        return out

    mag = alpha & magenta_hsv_mask(
        out[:, :, :3],
        hue_center=hue_center,
        hue_tolerance=hue_tolerance,
        min_saturation=min_saturation,
        min_value=min_value,
    )
    if not np.any(mag):
        return out

    row_indices = list(range(search_band)) + list(range(h - search_band, h))
    col_indices = list(range(search_band)) + list(range(w - search_band, w))

    def clear_horizontal_run(y: int, x0: int, x1: int) -> None:
        y_lo = y
        y_hi = y
        threshold = max(3, (x1 - x0) // 2)

        yy = y - 1
        while yy >= 0 and (y_hi - y_lo + 1) < max_thickness:
            if int(mag[yy, x0:x1].sum()) < threshold:
                break
            y_lo = yy
            yy -= 1

        yy = y + 1
        while yy < h and (y_hi - y_lo + 1) < max_thickness:
            if int(mag[yy, x0:x1].sum()) < threshold:
                break
            y_hi = yy
            yy += 1

        sl = mag[y_lo : y_hi + 1, x0:x1]
        out[y_lo : y_hi + 1, x0:x1, 3] = np.where(sl, 0, out[y_lo : y_hi + 1, x0:x1, 3])

    def clear_vertical_run(x: int, y0: int, y1: int) -> None:
        x_lo = x
        x_hi = x
        threshold = max(3, (y1 - y0) // 2)

        xx = x - 1
        while xx >= 0 and (x_hi - x_lo + 1) < max_thickness:
            if int(mag[y0:y1, xx].sum()) < threshold:
                break
            x_lo = xx
            xx -= 1

        xx = x + 1
        while xx < w and (x_hi - x_lo + 1) < max_thickness:
            if int(mag[y0:y1, xx].sum()) < threshold:
                break
            x_hi = xx
            xx += 1

        sl = mag[y0:y1, x_lo : x_hi + 1]
        out[y0:y1, x_lo : x_hi + 1, 3] = np.where(sl, 0, out[y0:y1, x_lo : x_hi + 1, 3])

    for y in row_indices:
        x = 0
        while x < w:
            while x < w and not mag[y, x]:
                x += 1
            x0 = x
            while x < w and mag[y, x]:
                x += 1
            x1 = x
            if x1 - x0 >= min_run_length:
                clear_horizontal_run(y, x0, x1)

    for x in col_indices:
        y = 0
        while y < h:
            while y < h and not mag[y, x]:
                y += 1
            y0 = y
            while y < h and mag[y, x]:
                y += 1
            y1 = y
            if y1 - y0 >= min_run_length:
                clear_vertical_run(x, y0, y1)

    return out


def despill_border_tint(
    arr: np.ndarray,
    *,
    search_band: int,
    hue_center: float,
    hue_tolerance: float,
    min_saturation: float,
    min_value: float,
) -> np.ndarray:
    out = arr.copy()
    alpha = out[:, :, 3] > 0
    h, w = alpha.shape
    if not np.any(alpha):
        return out

    search_band = min(search_band, h // 2, w // 2)
    if search_band <= 0:
        return out

    band = np.zeros((h, w), dtype=bool)
    band[:search_band, :] = True
    band[h - search_band :, :] = True
    band[:, :search_band] = True
    band[:, w - search_band :] = True

    spill = alpha & band & magenta_hsv_mask(
        out[:, :, :3],
        hue_center=hue_center,
        hue_tolerance=hue_tolerance,
        min_saturation=min_saturation,
        min_value=min_value,
    )
    if not np.any(spill):
        return out

    support = np.zeros((h, w), dtype=np.uint8)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            shifted = np.zeros_like(alpha, dtype=np.uint8)
            y_src0 = max(0, -dy)
            y_src1 = min(h, h - dy)
            x_src0 = max(0, -dx)
            x_src1 = min(w, w - dx)
            y_dst0 = max(0, dy)
            y_dst1 = min(h, h + dy)
            x_dst0 = max(0, dx)
            x_dst1 = min(w, w + dx)
            shifted[y_dst0:y_dst1, x_dst0:x_dst1] = alpha[y_src0:y_src1, x_src0:x_src1]
            support += shifted

    fringe = spill & (support <= 6)
    if not np.any(fringe):
        return out

    clean = alpha & (~spill)
    out = borrow_clean_edge_colors(out, spill=fringe, clean=clean, bg=np.zeros_like(alpha, dtype=bool))
    return out


def magenta_score(rgb: np.ndarray) -> np.ndarray:
    rgb16 = rgb.astype(np.int16)
    r = rgb16[:, :, 0].astype(np.float32)
    g = rgb16[:, :, 1].astype(np.float32)
    b = rgb16[:, :, 2].astype(np.float32)
    return ((r + b) / 2.0) - g


def rgb_to_hsv_channels(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rgbf = rgb.astype(np.float32) / 255.0
    r = rgbf[:, :, 0]
    g = rgbf[:, :, 1]
    b = rgbf[:, :, 2]

    maxc = np.max(rgbf, axis=2)
    minc = np.min(rgbf, axis=2)
    delta = maxc - minc

    h = np.zeros_like(maxc)
    s = np.zeros_like(maxc)
    v = maxc

    nonzero = maxc > 1e-6
    s[nonzero] = delta[nonzero] / maxc[nonzero]

    mask = delta > 1e-6
    rmask = mask & (maxc == r)
    gmask = mask & (maxc == g)
    bmask = mask & (maxc == b)

    h[rmask] = np.mod((g[rmask] - b[rmask]) / delta[rmask], 6.0)
    h[gmask] = ((b[gmask] - r[gmask]) / delta[gmask]) + 2.0
    h[bmask] = ((r[bmask] - g[bmask]) / delta[bmask]) + 4.0
    h = (h / 6.0) % 1.0

    return h, s, v


def hue_distance(hue: np.ndarray, center: float) -> np.ndarray:
    delta = np.abs(hue - center)
    return np.minimum(delta, 1.0 - delta)


def magenta_hsv_mask(
    rgb: np.ndarray,
    *,
    hue_center: float,
    hue_tolerance: float,
    min_saturation: float,
    min_value: float,
) -> np.ndarray:
    h, s, v = rgb_to_hsv_channels(rgb.astype(np.uint8))
    return (hue_distance(h, hue_center) <= hue_tolerance) & (s >= min_saturation) & (v >= min_value)


def borrow_clean_edge_colors(
    arr: np.ndarray,
    *,
    spill: np.ndarray,
    clean: np.ndarray,
    bg: np.ndarray,
) -> np.ndarray:
    out = arr.copy()
    h, w = spill.shape
    ys, xs = np.nonzero(spill)

    for y, x in zip(ys.tolist(), xs.tolist()):
        candidates: list[np.ndarray] = []
        for radius in (1, 2, 3):
            y0 = max(0, y - radius)
            y1 = min(h, y + radius + 1)
            x0 = max(0, x - radius)
            x1 = min(w, x + radius + 1)

            region_clean = clean[y0:y1, x0:x1]
            if np.any(region_clean):
                local = out[y0:y1, x0:x1, :3][region_clean]
                if len(local) > 0:
                    candidates.append(local)
                    break

        if not candidates:
            continue

        source = np.concatenate(candidates, axis=0).astype(np.float32)
        replacement = np.median(source, axis=0)
        original = out[y, x, :3].astype(np.float32)

        # Keep some local contrast while removing the magenta contamination.
        blended = replacement * 0.92 + original * 0.08
        out[y, x, :3] = np.clip(blended, 0.0, 255.0).astype(np.uint8)

    return out


def touches_background(bg: np.ndarray, x: int, y: int) -> bool:
    h, w = bg.shape
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx = x + dx
        ny = y + dy
        if 0 <= nx < w and 0 <= ny < h and bg[ny, nx]:
            return True
    return False


def purge_remaining_magenta(
    img: Image.Image,
    *,
    bg_hue_center: float,
    bg_hue_tolerance: float,
    hard_purge_saturation: float,
    hard_purge_value: float,
    soft_purge_saturation: float,
    soft_purge_value: float,
) -> Image.Image:
    arr = np.array(img, dtype=np.uint8)
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3].astype(np.uint8)

    strong = (alpha > 0) & magenta_hsv_mask(
        rgb,
        hue_center=bg_hue_center,
        hue_tolerance=bg_hue_tolerance * 0.85,
        min_saturation=hard_purge_saturation,
        min_value=hard_purge_value,
    )
    medium = (alpha > 0) & (~strong) & magenta_hsv_mask(
        rgb,
        hue_center=bg_hue_center,
        hue_tolerance=bg_hue_tolerance,
        min_saturation=soft_purge_saturation,
        min_value=soft_purge_value,
    )

    arr[strong, 3] = 0
    if np.any(medium):
        arr[medium, 3] = np.minimum(arr[medium, 3], 164)

    return Image.fromarray(arr, mode="RGBA")


if __name__ == "__main__":
    main()
