#!/usr/bin/env bash
set -e
IMG=${IMG:-sensor-fuzz:arm}
docker buildx build --platform linux/arm64 -t "$IMG" -f deploy/Dockerfile . --load
docker run --rm -p 8000:8000 "$IMG"
