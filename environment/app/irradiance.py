"""Irradiance reporting for the field audit."""

from __future__ import annotations

from pv_physics import cell_parameters


def estimate(payload):
    current_max = max(float(point["current_a"]) for point in payload["sweep"])
    isc_t, _a, _i0 = cell_parameters(payload["cell"], payload["temperature_c"])
    level = int(round(current_max * 1000.0 / isc_t))
    return [level for _section in payload["sections"]]
