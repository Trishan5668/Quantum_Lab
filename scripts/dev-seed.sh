#!/usr/bin/env bash
# Seed a local QuantHub instance with a few real projects, files and one run.
# Uses only the public API; nothing is written directly to the database.
# Usage: scripts/dev-seed.sh [api-base] (default http://127.0.0.1:8765)
set -euo pipefail

API="${1:-http://127.0.0.1:8765}/api/v1"
HANDLE="${QUANTHUB_SEED_HANDLE:-quanthub-demo}"
AUTH=(-H "X-QuantHub-User: ${HANDLE}" -H "X-QuantHub-Name: QuantHub Demo")

json() { python3 -c "import json,sys;d=json.load(sys.stdin);print(d['data'] if d.get('data') is not None else d)"; }
field() { python3 -c "import json,sys;print(json.load(sys.stdin)['data']['$1'])"; }

create_project() {
  curl -s -X POST "$API/projects" "${AUTH[@]}" -H "Content-Type: application/json" -d "$1"
}

# Preflight: the API only accepts these identity headers when it is explicitly
# running the development profile. Fail with the reason instead of seeding
# nothing and printing a wall of 401s.
mode="$(curl -sf "$API/me" "${AUTH[@]}" 2>/dev/null | python3 -c \
  "import json,sys;print(json.load(sys.stdin)['data'].get('mode','guest'))" 2>/dev/null || echo "unreachable")"
if [[ "$mode" != "local" && "$mode" != "authenticated" ]]; then
  if [[ "$mode" == "unreachable" ]]; then
    echo "cannot reach the QuantHub API at $API" >&2
  else
    echo "the QuantHub API at $API did not accept the seed identity (session mode: $mode)." >&2
    echo "start it with: QUANTHUB_ENV=development QUANTHUB_TRUST_CLIENT_IDENTITY=1" >&2
    echo "or use scripts/dev-api.sh, which sets both." >&2
  fi
  exit 1
fi

echo "== projects"
for payload in \
  '{"name":"Surface Code Notes","description":"Circuit-level surface-code memory sweeps with Stim and PyMatching, plus notes on decoding.","visibility":"public","topics":["qec","surface-code","stim"],"initialize_readme":true,"gitignore_template":"python","license":"MIT"}' \
  '{"name":"BB84 Toolkit","description":"Reference implementation and tests for the BB84 prepare-and-measure key distribution protocol.","visibility":"public","topics":["algorithms","cryptography","education"],"initialize_readme":true,"gitignore_template":"node","license":"Apache-2.0"}' \
  '{"name":"Reading List","description":"Papers I am reading on fault-tolerant quantum computing.","visibility":"public","topics":["research","papers"],"initialize_readme":true,"gitignore_template":"none","license":"none"}'
do
  create_project "$payload" | field full_name || true
done

tmp="$(mktemp -d)"
cat > "$tmp/distance_sweep.py" <<'PY'
"""Distance sweep helper for rotated surface-code memories."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SweepPoint:
    distance: int
    rounds: int
    shots: int


DEFAULT_SWEEP = (
    SweepPoint(distance=3, rounds=3, shots=5000),
    SweepPoint(distance=5, rounds=5, shots=5000),
)
PY
cat > "$tmp/NOTES.md" <<'MD'
# Decoder notes

- MWPM on the detector error model is the baseline for Stim-backed runs.
- Zero observed failures are reported with an upper bound, never as p = 0.
MD
cat > "$tmp/bb84.md" <<'MD'
# BB84 toolkit

Reference implementation of BB84 for the education track. No security claim
beyond the idealised single-photon model.
MD

echo "== files"
rev=$(curl -s "$API/projects/$HANDLE/surface-code-notes" "${AUTH[@]}" | field revision)
curl -s -X POST "$API/projects/$HANDLE/surface-code-notes/upload" "${AUTH[@]}" \
  -F "files=@$tmp/distance_sweep.py;filename=distance_sweep.py" \
  -F "files=@$tmp/NOTES.md;filename=NOTES.md" \
  -F 'paths=["src/distance_sweep.py","NOTES.md"]' \
  -F "message=Add distance sweep helper and decoder notes" \
  -F "expected_revision=$rev" | json | head -c 200; echo

rev=$(curl -s "$API/projects/$HANDLE/bb84-toolkit" "${AUTH[@]}" | field revision)
curl -s -X POST "$API/projects/$HANDLE/bb84-toolkit/upload" "${AUTH[@]}" \
  -F "files=@$tmp/bb84.md;filename=bb84.md" \
  -F 'paths=["docs/bb84.md"]' \
  -F "message=Document the BB84 reference implementation" \
  -F "expected_revision=$rev" | json | head -c 200; echo

echo "== experiment"
protocol=$(curl -s "$API/experiments/templates" "${AUTH[@]}" \
  | python3 -c "import json,sys;d=json.load(sys.stdin)['data'];print(json.dumps([t for t in d['templates'] if not t['requires_stim']][0]['protocol']))")
spec=$(curl -s -X POST "$API/projects/$HANDLE/surface-code-notes/experiments" "${AUTH[@]}" \
  -H "Content-Type: application/json" \
  -d "{\"protocol\": $protocol, \"name\": \"Repetition d=3 code-capacity baseline\", \"description\": \"Ideal-syndrome bit-flip baseline comparing exact and majority-vote decoding.\"}" \
  | field id)
echo "spec=$spec"
run=$(curl -s -X POST "$API/projects/$HANDLE/surface-code-notes/experiments/$spec/runs" "${AUTH[@]}" \
  -H "Content-Type: application/json" -d '{}' | field id)
echo "run=$run"

for _ in $(seq 1 60); do
  status=$(curl -s "$API/projects/$HANDLE/surface-code-notes/runs/$run" "${AUTH[@]}" | field status)
  printf '%s ' "$status"
  case "$status" in completed|failed|cancelled) break ;; esac
  sleep 1
done
echo
rm -rf "$tmp"
echo "done"
