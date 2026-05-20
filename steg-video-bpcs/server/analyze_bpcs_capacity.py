#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import cv2
import numpy as np


BIT_PLANES = [2, 3, 4, 5]
ALPHAS = [0.30, 0.35, 0.40, 0.45]
BLOCK_SIZE = 8


def complexity(block_bits: np.ndarray) -> float:
    horizontal = np.count_nonzero(block_bits[:, 1:] != block_bits[:, :-1])
    vertical = np.count_nonzero(block_bits[1:, :] != block_bits[:-1, :])
    max_edges = block_bits.shape[0] * (block_bits.shape[1] - 1) + (block_bits.shape[0] - 1) * block_bits.shape[1]
    return float(horizontal + vertical) / float(max_edges)


def count_capacity(video_path: Path, bit_plane: int, alpha: float) -> tuple[int, int]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video_path}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    block_rows = height // BLOCK_SIZE
    block_cols = width // BLOCK_SIZE
    mask = 1 << bit_plane
    count = 0
    frames = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        channel = frame[:, :, 0]
        for block_index in range(block_rows * block_cols):
            row = (block_index // block_cols) * BLOCK_SIZE
            col = (block_index % block_cols) * BLOCK_SIZE
            block = channel[row : row + BLOCK_SIZE, col : col + BLOCK_SIZE]
            block_bits = ((block & mask) > 0).astype(np.uint8)
            if complexity(block_bits) >= alpha:
                count += 1
        frames += 1

    cap.release()
    return count, frames


def main() -> None:
    video_path = Path(sys.argv[1] if len(sys.argv) > 1 else "cover.mp4")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "capacity_report.json")
    rows = []
    best = None
    for bit_plane in BIT_PLANES:
        for alpha in ALPHAS:
            capacity, frames = count_capacity(video_path, bit_plane, alpha)
            row = {"bit_plane": bit_plane, "alpha": alpha, "capacity_bits": capacity, "frames": frames}
            rows.append(row)
            if best is None or capacity > best["capacity_bits"]:
                best = row

    report = {"block_size": BLOCK_SIZE, "rows": rows, "recommended": best}
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    print(f"capacity analyzed: combinations={len(rows)} recommended_plane={best['bit_plane']} recommended_alpha={best['alpha']:.2f} capacity={best['capacity_bits']}")


if __name__ == "__main__":
    main()
