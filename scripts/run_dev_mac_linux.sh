#!/usr/bin/env bash
set -euo pipefail

echo "[1/2] Starting API..."
pushd services/local_api >/dev/null
python -m venv .venv || true
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main &
API_PID=$!
popd >/dev/null

echo "[2/2] Starting UI..."
pushd apps/desktop >/dev/null
npm install
npm run dev
popd >/dev/null

kill $API_PID
