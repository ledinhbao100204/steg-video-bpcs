#!/usr/bin/env python3
import json
import hashlib
import struct
import sys
import zlib
from pathlib import Path

import cv2
import numpy as np


MAGIC = b"BPCSVID1"


def seed_from_key(key_text: str) -> int:
    digest = hashlib.sha256(key_text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def complexity(block_bits: np.ndarray) -> float:
    horizontal = np.count_nonzero(block_bits[:, 1:] != block_bits[:, :-1])
    vertical = np.count_nonzero(block_bits[1:, :] != block_bits[:-1, :])
    max_edges = block_bits.shape[0] * (block_bits.shape[1] - 1) + (block_bits.shape[0] - 1) * block_bits.shape[1]
    return float(horizontal + vertical) / float(max_edges)


def majority_vote(bits: str, repeat: int) -> str:
    voted = []
    for index in range(0, len(bits), repeat):
        group = bits[index : index + repeat]
        if len(group) != repeat:
            break
        voted.append("1" if group.count("1") >= ((repeat // 2) + 1) else "0")
    return "".join(voted)


def bytes_from_bits(bits: str) -> bytes:
    out = bytearray()
    for index in range(0, len(bits), 8):
        byte = bits[index : index + 8]
        if len(byte) == 8:
            out.append(int(byte, 2))
    return bytes(out)


def parse_packet(packet: bytes) -> bytes:
    if not packet.startswith(MAGIC):
        raise SystemExit("magic mismatch: wrong key, damaged video, or wrong metadata")
    offset = len(MAGIC)
    if len(packet) < offset + 2:
        raise SystemExit("packet too short")
    message_length = struct.unpack(">H", packet[offset : offset + 2])[0]
    offset += 2
    end = offset + message_length
    if len(packet) < end + 4:
        raise SystemExit("packet length mismatch")
    message = packet[offset:end]
    stored_crc = struct.unpack(">I", packet[end : end + 4])[0]
    actual_crc = zlib.crc32(message) & 0xFFFFFFFF
    if stored_crc != actual_crc:
        raise SystemExit(f"crc mismatch: expected={stored_crc:08x} actual={actual_crc:08x}")
    return message


def main() -> None:
    in_video = Path(sys.argv[1] if len(sys.argv) > 1 else "stego_bpcs.mp4")
    meta_path = Path(sys.argv[2] if len(sys.argv) > 2 else "payload_meta.json")
    key_path = Path(sys.argv[3] if len(sys.argv) > 3 else "stego_key.txt")
    out_path = Path(sys.argv[4] if len(sys.argv) > 4 else "extracted_message.txt")

    metadata = json.loads(meta_path.read_text(encoding="ascii"))
    key_text = key_path.read_text(encoding="utf-8").strip()
    bit_plane = int(metadata["bit_plane"])
    block_size = int(metadata["block_size"])
    alpha = float(metadata["alpha"])
    repeat = int(metadata["repeat"])
    payload_bit_count = int(metadata["payload_bit_count"])

    cap = cv2.VideoCapture(str(in_video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {in_video}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    block_rows = height // block_size
    block_cols = width // block_size
    blocks_per_frame = block_rows * block_cols
    mask = 1 << bit_plane
    candidates: list[int] = []
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
                candidates.append(frame_base + block_index)
        frame_index += 1

    cap.release()
    if payload_bit_count > len(candidates):
        raise SystemExit(f"metadata asks for {payload_bit_count} bits but capacity is {len(candidates)}")

    rng = np.random.default_rng(seed_from_key(key_text))
    selected_positions = np.array(candidates, dtype=np.int64)
    rng.shuffle(selected_positions)
    selected_positions = [int(pos) for pos in selected_positions[:payload_bit_count].tolist()]
    wanted = set(selected_positions)

    cap = cv2.VideoCapture(str(in_video))
    if not cap.isOpened():
        raise SystemExit(f"cannot reopen {in_video}")
    detected_by_position: dict[int, str] = {}
    frame_index = 0

    while len(detected_by_position) < payload_bit_count:
        ok, frame = cap.read()
        if not ok:
            break
        y_channel = frame[:, :, 0]
        frame_base = frame_index * blocks_per_frame
        for block_index in range(blocks_per_frame):
            pos = frame_base + block_index
            if pos not in wanted:
                continue
            row = (block_index // block_cols) * block_size
            col = (block_index % block_cols) * block_size
            block = y_channel[row : row + block_size, col : col + block_size]
            ones = np.count_nonzero(block & mask)
            detected_by_position[pos] = "1" if ones >= ((block_size * block_size) // 2) else "0"
        frame_index += 1

    cap.release()
    if len(detected_by_position) != payload_bit_count:
        raise SystemExit(f"extracted {len(detected_by_position)} bits but expected {payload_bit_count}")

    repeated_bits = "".join(detected_by_position[pos] for pos in selected_positions)
    packet_bits = majority_vote(repeated_bits, repeat)
    message = parse_packet(bytes_from_bits(packet_bits))
    out_path.write_bytes(message)
    print(f"crc ok: extracted message: {message.decode('utf-8', errors='replace')}")


if __name__ == "__main__":
    main()
