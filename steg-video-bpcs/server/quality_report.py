#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    original_path = Path(sys.argv[1] if len(sys.argv) > 1 else "cover.mp4")
    stego_path = Path(sys.argv[2] if len(sys.argv) > 2 else "public/stego_bpcs.mp4")
    out_path = Path(sys.argv[3] if len(sys.argv) > 3 else "metrics.json")

    original = cv2.VideoCapture(str(original_path))
    stego = cv2.VideoCapture(str(stego_path))
    if not original.isOpened() or not stego.isOpened():
        raise SystemExit("cannot open input videos")

    total_error = 0.0
    sample_count = 0
    frames = 0
    while True:
        ok_a, frame_a = original.read()
        ok_b, frame_b = stego.read()
        if not ok_a or not ok_b:
            break
        diff = frame_a.astype(np.float32) - frame_b.astype(np.float32)
        total_error += float(np.sum(diff * diff))
        sample_count += int(diff.size)
        frames += 1

    original.release()
    stego.release()
    if sample_count == 0:
        raise SystemExit("no comparable frames")

    mse = total_error / sample_count
    psnr = 99.0 if mse == 0 else 20.0 * math.log10(255.0 / math.sqrt(mse))
    out_path.write_text(json.dumps({"frames_compared": frames, "mse": mse, "psnr": psnr}, indent=2) + "\n", encoding="ascii")
    print(f"quality report: psnr={psnr:.2f} mse={mse:.4f} frames={frames}")


if __name__ == "__main__":
    main()
