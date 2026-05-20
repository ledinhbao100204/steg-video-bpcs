#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> None:
    expected = Path(sys.argv[1] if len(sys.argv) > 1 else "expected_message.txt")
    actual = Path(sys.argv[2] if len(sys.argv) > 2 else "extracted_message.txt")
    if expected.read_bytes() == actual.read_bytes():
        print("messages match")
    else:
        print("messages differ")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
