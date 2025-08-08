#!/usr/bin/env bash
set -euo pipefail

rm -rf mcap_ros2idl_support/dist
npm --prefix nodejs run deploy
python -m build
