#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np


def seed_from_key(key_text: str) -> int:
    digest = hashlib.sha256(key_text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def complexity(block_bits: np.ndarray) -> float:
    horizontal = np.count_nonzero(block_bits[:, 1:] != block_bits[:, :-1])
    vertical = np.count_nonzero(block_bits[1:, :] != block_bits[:-1, :])
    max_edges = block_bits.shape[0] * (block_bits.shape[1] - 1) + (block_bits.shape[0] - 1) * block_bits.shape[1]
    return float(horizontal + vertical) / float(max_edges)


def payload_pattern(bit: int, frame_index: int, block_index: int, block_size: int) -> np.ndarray:
    yy, xx = np.indices((block_size, block_size))
    pattern = ((xx + yy + frame_index + block_index) % 2).astype(np.uint8)
    patch = max(2, block_size // 2)
    if bit:
        pattern[:patch, :patch] = 1
    else:
        pattern[:patch, :patch] = 0
    return pattern


def noisy_positions(video_path: Path, bit_plane: int, alpha: float, block_size: int) -> tuple[list[int], int, int, int]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    block_rows = height // block_size
    block_cols = width // block_size
    blocks_per_frame = block_rows * block_cols
    mask = 1 << bit_plane
    positions: list[int] = []
    frame_index = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        y_channel = frame[:, :, 0]
        frame_base = frame_index * blocks_per_frame
        for block_index in range(blocks_per_frame):
            row = (block_index // block_cols) * block_size
            col = (block_index % block_cols) * block_size
            block = y_channel[row : row + block_size, col : col + block_size]
            block_bits = ((block & mask) > 0).astype(np.uint8)
            if complexity(block_bits) >= alpha:
                positions.append(frame_base + block_index)
        frame_index += 1

    cap.release()
    return positions, frame_index, height, width


def main() -> None:
    in_video = Path(sys.argv[1] if len(sys.argv) > 1 else "cover.mp4")
    bits_path = Path(sys.argv[2] if len(sys.argv) > 2 else "payload_bits.txt")
    key_path = Path(sys.argv[3] if len(sys.argv) > 3 else "stego_key.txt")
    out_video = Path(sys.argv[4] if len(sys.argv) > 4 else "public/stego_bpcs.mp4")
    meta_path = Path(sys.argv[5] if len(sys.argv) > 5 else "payload_meta.json")

    bits = bits_path.read_text(encoding="ascii").strip()
    if not bits or any(bit not in "01" for bit in bits):
        raise SystemExit("payload bit file must contain only 0 and 1")
    key_text = key_path.read_text(encoding="utf-8").strip()
    if not key_text:
        raise SystemExit("stego key is empty")
    metadata = json.loads(meta_path.read_text(encoding="ascii"))
    bit_plane = int(metadata["bit_plane"])
    alpha = float(metadata["alpha"])
    block_size = int(metadata["block_size"])

    candidates, frame_count, height, width = noisy_positions(in_video, bit_plane, alpha, block_size)
    if len(bits) > len(candidates):
        raise SystemExit(f"payload too large for noisy BPCS capacity: bits={len(bits)} capacity={len(candidates)}")

    rng = np.random.default_rng(seed_from_key(key_text))
    selected = np.array(candidates, dtype=np.int64)
    rng.shuffle(selected)
    selected = selected[: len(bits)]
    position_to_bit = {int(pos): int(bit) for pos, bit in zip(selected, bits)}

    cap = cv2.VideoCapture(str(in_video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    out_video.parent.mkdir(parents=True, exist_ok=True)
    temp_video = out_video.with_suffix(".avi")
    writer = cv2.VideoWriter(str(temp_video), cv2.VideoWriter_fourcc(*"FFV1"), fps, (width, height))
    if not writer.isOpened():
        raise SystemExit(f"cannot create {temp_video}")

    block_rows = height // block_size
    block_cols = width // block_size
    blocks_per_frame = block_rows * block_cols
    mask = 1 << bit_plane
    clear_mask = 255 ^ mask
    embedded = 0
    frame_index = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        out_frame = frame.copy()
        y_channel = out_frame[:, :, 0]
        frame_base = frame_index * blocks_per_frame
        for block_index in range(blocks_per_frame):
            bit = position_to_bit.get(frame_base + block_index)
            if bit is None:
                continue
            row = (block_index // block_cols) * block_size
            col = (block_index % block_cols) * block_size
            block = y_channel[row : row + block_size, col : col + block_size]
            pattern = payload_pattern(bit, frame_index, block_index, block_size)
            block[:, :] = (block & clear_mask) | (pattern * mask)
            embedded += 1

        writer.write(out_frame)
        frame_index += 1

    cap.release()
    writer.release()
    temp_video.replace(out_video)
    if embedded != len(bits):
        raise SystemExit(f"embedded {embedded} bits but expected {len(bits)}")

    public_meta = out_video.parent / meta_path.name
    metadata["frame_indices"] = sorted({int(pos) // blocks_per_frame for pos in selected.tolist()})
    metadata["location_map"] = "derived from stego_key.txt; selected positions are not published"
    metadata["noisy_capacity"] = len(candidates)
    metadata["frame_count"] = frame_count
    metadata["width"] = width
    metadata["height"] = height
    public_meta.write_text(json.dumps(metadata, indent=2) + "\n", encoding="ascii")
    (out_video.parent / "key_hint.txt").write_text("Use the shared key file stego_key.txt on the client.\n", encoding="ascii")
    print(f"bpcs embedded: bits={embedded} noisy_capacity={len(candidates)} output={out_video}")


if __name__ == "__main__":
    main()
