"""Photovoltaic string audit tool."""

from __future__ import annotations

import json
import sys

from irradiance import estimate
from mpp import global_mpp
from pv_physics import section_voltage


def run_bypass(payload):
    cell = payload["cell"]
    current = float(payload["current_a"])
    bypassed = []
    for section in payload["sections"]:
        _voltage, state = section_voltage(
            section,
            cell,
            payload["temperature_c"],
            payload["bypass_forward_v"],
            current,
            float(section["front_irradiance_w_m2"]),
        )
        if state:
            bypassed.append(section["id"])
    return {"bypassed_section_ids": bypassed}


def dispatch(payload):
    kind = payload.get("kind")
    if kind == "bypass":
        return run_bypass(payload)
    if kind == "irradiance":
        return {"irradiance_levels_w_m2": estimate(payload)}
    if kind == "mpp":
        return global_mpp(payload)
    raise ValueError(f"unknown kind: {kind}")


def main(argv):
    if len(argv) != 2:
        print("usage: python3 /app/main.py <input.json>", file=sys.stderr)
        return 2
    try:
        with open(argv[1], "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        result = dispatch(payload)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
