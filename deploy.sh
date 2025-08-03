#!/usr/bin/env bash
set -euo pipefail

rm -rf dist
npm run deploy
python -m build
