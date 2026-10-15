#!/bin/bash
# Rebuild assets/footage.mp4 from the raw phone take: light denoise, upscale 478x850 -> 1080x1920
# with sharpening, short GOP for fast seeking, and loudness normalized to -14 LUFS (two-pass
# values measured from source/raw-take.mp4).
set -euo pipefail
cd "$(dirname "$0")/.."
ffmpeg -hide_banner -v error -y -i source/raw-take.mp4 \
  -vf "hqdn3d=1.2:1.2:3:3,scale=1080:1920:flags=lanczos,unsharp=5:5:0.7:5:5:0.0,format=yuv420p" \
  -c:v libx264 -preset slow -crf 16 -g 15 -r 30 \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=-9.04:measured_TP=0.11:measured_LRA=10.10:measured_thresh=-21.03:offset=0.01:linear=true,aresample=48000" \
  -c:a aac -b:a 192k -movflags +faststart assets/footage.mp4
echo "assets/footage.mp4 ready"
