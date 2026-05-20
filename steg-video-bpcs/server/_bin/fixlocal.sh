#!/bin/bash
set -e

cd /home/ubuntu
chmod +x create_cover_video.py analyze_bpcs_capacity.py prepare_payload.py embed_bpcs.py quality_report.py 2>/dev/null || true
mkdir -p public
chown -R ubuntu:ubuntu /home/ubuntu/public
