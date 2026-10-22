#!/usr/bin/env bash
# Install the complete reference implementation, then optionally revert one
# difficulty to its original form for leave-one-out verification.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
install -m 0644 "$HERE/app/"*.py /app/

SKIP="${HTB_SKIP:-}" /usr/local/bin/python3 - /app <<'PY'
import os
import sys
from pathlib import Path

REVERT = {
    "difficulty_1": (
        "main.py",
        '        irradiance = effective_irradiance(section, cell["bifaciality_factor"])',
        '        irradiance = float(section["front_irradiance_w_m2"])',
    ),
    "difficulty_2": (
        "irradiance.py",
        '    return [int(round(value)) for value in sorted(best_levels)]',
        '    return [int(round(reference)) for _section in payload["sections"]]',
    ),
    "difficulty_3": (
        "mpp.py",
        '        if slope < 0.0:\n'
        '            vertex = -intercept / (2.0 * slope)\n'
        '            if v0 < vertex < v1:\n'
        '                candidates.append(vertex)\n'
        '            if current_limit is not None:\n'
        '                crossing = (current_limit - intercept) / slope\n'
        '                if v0 < crossing < v1:\n'
        '                    candidates.append(crossing)\n',
        "",
    ),
}
skip = [item for item in os.environ.get("SKIP", "").split(",") if item]
unknown = sorted(set(skip) - set(REVERT))
if unknown:
    sys.exit(f"unknown difficulty ids: {unknown}")
root = Path(sys.argv[1])
for key in skip:
    filename, fixed, original = REVERT[key]
    path = root / filename
    text = path.read_text(encoding="utf-8")
    if text.count(fixed) != 1:
        sys.exit(f"{key} fixed fragment appears {text.count(fixed)} times, expected 1")
    path.write_text(text.replace(fixed, original), encoding="utf-8")
    print(f"reverted {key} in {filename}", file=sys.stderr)
PY
chown runner:runner /app/*.py 2>/dev/null || true
