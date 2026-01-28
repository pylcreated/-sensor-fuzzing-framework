#!/usr/bin/env bash
set -e
# Build and run container locally
IMG=${IMG:-sensor-fuzz:latest}
docker build -t "$IMG" -f deploy/Dockerfile .
docker run --rm -p 8000:8000 "$IMG"
