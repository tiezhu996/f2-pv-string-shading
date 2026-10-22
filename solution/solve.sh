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
        '''def estimate(payload):
    levels = _initial_levels(payload)
    best_error = _sse(payload, levels)
    for _ in range(5):
        changed = False
        for index in range(len(levels)):
            center = levels[index]
            best_value = center
            best_local = best_error
            lower = max(1, int(center) - 9)
            upper = min(1300, int(center) + 9)
            for value in range(lower, upper + 1):
                trial = levels[:]
                trial[index] = float(value)
                error = _sse(payload, trial)
                if error < best_local:
                    best_local = error
                    best_value = float(value)
            levels[index] = best_value
            best_error = best_local
            changed = changed or best_value != center
        levels.sort()
        if not changed:
            break
    return [int(round(value)) for value in sorted(levels)]''',
        '''def estimate(payload):
    reference = int(round(float(payload["reference_irradiance_w_m2"])))
    return [reference for _section in payload["sections"]]''',
    ),
    "difficulty_3": (
        "mpp.py",
        '''        if slope < 0.0:
            intercept = i0 - slope * v0
            vertex = -intercept / (2.0 * slope)
            if v0 < vertex < v1:
                candidates.append(vertex)
''',
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
