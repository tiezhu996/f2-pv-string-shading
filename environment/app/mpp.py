"""Maximum-power reporting for parallel string traces."""

from __future__ import annotations


def _interp(curve, voltage):
    points = sorted((float(p["voltage_v"]), float(p["current_a"])) for p in curve)
    if voltage <= points[0][0]:
        return points[0][1]
    if voltage >= points[-1][0]:
        return points[-1][1]
    for (v0, i0), (v1, i1) in zip(points, points[1:]):
        if v0 <= voltage <= v1:
            return i0 + (i1 - i0) * (voltage - v0) / (v1 - v0)
    raise ValueError("voltage outside curve")


def global_mpp(payload):
    strings = payload["strings"]
    voltages = sorted({float(p["voltage_v"]) for string in strings for p in string["curve"]})
    best_voltage = voltages[0]
    best_currents = {string["id"]: _interp(string["curve"], best_voltage) for string in strings}
    best_power = best_voltage * sum(best_currents.values())
    for voltage in voltages:
        currents = {string["id"]: _interp(string["curve"], voltage) for string in strings}
        power = voltage * sum(currents.values())
        if power > best_power:
            best_voltage = voltage
            best_currents = currents
            best_power = power
    return {
        "voltage_v": round(best_voltage, 3),
        "current_a": round(sum(best_currents.values()), 3),
        "power_w": round(best_power, 3),
        "string_currents_a": {string["id"]: round(best_currents[string["id"]], 3) for string in strings},
    }
