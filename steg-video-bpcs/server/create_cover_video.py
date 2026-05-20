#!/usr/bin/env python3
from pathlib import Path

import cv2
import numpy as np


WIDTH = 320
HEIGHT = 240
FPS = 24
FRAMES = 96
OUT = Path("cover.mp4")


def make_frame(index: int, rng: np.random.Generator) -> np.ndarray:
    x = np.linspace(0, 255, WIDTH, dtype=np.float32)
    y = np.linspace(0, 255, HEIGHT, dtype=np.float32)[:, None]
    wave = 28 * np.sin((x[None, :] + index * 5) / 14.0)
    texture = rng.normal(0, 22, (HEIGHT, WIDTH)).astype(np.float32)
    checker = ((np.indices((HEIGHT, WIDTH)).sum(axis=0) + index) % 2) * 18

    base = (0.48 * x[None, :] + 0.32 * y + wave + texture + checker + 60) % 256
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    frame[:, :, 0] = np.clip(base * 0.75 + 35, 0, 255).astype(np.uint8)
    frame[:, :, 1] = np.clip(235 - base * 0.45 + index, 0, 255).astype(np.uint8)
    frame[:, :, 2] = np.clip(base + 20, 0, 255).astype(np.uint8)

    cx = 42 + (index * 4) % (WIDTH - 84)
    cy = 70 + int(28 * np.sin(index / 7.0))
    cv2.circle(frame, (cx, cy), 22, (34, 190, 235), -1)
    cv2.rectangle(frame, (WIDTH - 105, 30), (WIDTH - 30, 92), (215, 70, 105), -1)
    cv2.putText(frame, "BPCS", (20, HEIGHT - 24), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (245, 245, 245), 2)
    return frame


def main() -> None:
    rng = np.random.default_rng(20260519)
    writer = cv2.VideoWriter(str(OUT), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise SystemExit(f"cannot create {OUT}")

    for index in range(FRAMES):
        writer.write(make_frame(index, rng))
    writer.release()
    print(f"cover video created: {OUT} frames={FRAMES} size={WIDTH}x{HEIGHT} fps={FPS}")


if __name__ == "__main__":
    main()
