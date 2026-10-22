#!/usr/bin/env bash
# Start the QuantHub API for local development.
#
# QuantHub's local session (the X-QuantHub-* identity headers) is only honoured
# when the server is *explicitly* told it is a development instance, because
# those headers are not a security boundary. Booting the API with a bare
# `uvicorn app.main:app` therefore leaves the app read-only: every write returns
# 401. This script sets the two variables that opt in, and nothing else, so the
# web app works out of the box.
#
# Usage:
#   scripts/dev-api.sh [--port 8765] [--host 127.0.0.1]
#
# Never use this profile for a deployment reachable by untrusted clients.
set -euo pipefail

HOST="${QUANTHUB_HOST:-127.0.0.1}"
PORT="${QUANTHUB_PORT:-8765}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="${2:?--host needs a value}"; shift 2 ;;
    --port) PORT="${2:?--port needs a value}"; shift 2 ;;
    -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root/fastapi-server"

export QUANTHUB_ENV="${QUANTHUB_ENV:-development}"
export QUANTHUB_TRUST_CLIENT_IDENTITY="${QUANTHUB_TRUST_CLIENT_IDENTITY:-1}"
export QUANTHUB_DATA_DIR="${QUANTHUB_DATA_DIR:-$root/.quanthub-data}"

if [[ "$QUANTHUB_ENV" != "development" && "$QUANTHUB_ENV" != "test" ]]; then
  echo "refusing to enable local identity headers with QUANTHUB_ENV=$QUANTHUB_ENV" >&2
  exit 1
fi

# Prefer the active virtualenv; a bare `python` is often the system interpreter.
if [[ -z "${PYTHON:-}" ]]; then
  if [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
    PYTHON="$VIRTUAL_ENV/bin/python"
  else
    PYTHON="python3"
  fi
fi

echo "QuantHub API (local development)"
echo "  QUANTHUB_ENV=$QUANTHUB_ENV"
echo "  QUANTHUB_TRUST_CLIENT_IDENTITY=$QUANTHUB_TRUST_CLIENT_IDENTITY"
echo "  QUANTHUB_DATA_DIR=$QUANTHUB_DATA_DIR"
echo "  interpreter: $PYTHON"
echo "  http://$HOST:$PORT/docs"

exec "$PYTHON" -m uvicorn app.main:app --host "$HOST" --port "$PORT"
