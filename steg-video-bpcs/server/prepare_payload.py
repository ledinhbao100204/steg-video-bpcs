#!/usr/bin/env python3
import json
import struct
import sys
import zlib
from pathlib import Path


MAGIC = b"BPCSVID1"
DEFAULT_REPEAT = 7


def bits_from_bytes(data: bytes) -> str:
    return "".join(f"{byte:08b}" for byte in data)


def main() -> None:
    message_path = Path(sys.argv[1] if len(sys.argv) > 1 else "secret_message.txt")
    bits_path = Path(sys.argv[2] if len(sys.argv) > 2 else "payload_bits.txt")
    meta_path = Path(sys.argv[3] if len(sys.argv) > 3 else "payload_meta.json")

    message = message_path.read_bytes()
    crc = zlib.crc32(message) & 0xFFFFFFFF
    packet = MAGIC + struct.pack(">H", len(message)) + message + struct.pack(">I", crc)
    packet_bits = bits_from_bytes(packet)
    repeated_bits = "".join(bit * DEFAULT_REPEAT for bit in packet_bits)

    metadata = {
        "method": "BPCS bit-plane blocks on selected noisy 8x8 regions",
        "magic": MAGIC.decode("ascii"),
        "bit_plane": 5,
        "alpha": 0.3,
        "block_size": 8,
        "repeat": DEFAULT_REPEAT,
        "packet_bit_count": len(packet_bits),
        "payload_bit_count": len(repeated_bits),
        "crc32": f"{crc:08x}",
    }
    bits_path.write_text(repeated_bits + "\n", encoding="ascii")
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="ascii")
    print(f"payload prepared: bits={len(repeated_bits)} repeat={DEFAULT_REPEAT} crc32={crc:08x}")


if __name__ == "__main__":
    main()
