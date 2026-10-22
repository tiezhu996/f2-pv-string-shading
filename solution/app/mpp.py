"""Global maximum-power calculation for parallel measured I-V traces."""

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
    current_limit = payload.get("current_limit_a")
    current_limit = None if current_limit is None else float(current_limit)
    voltages = sorted({float(p["voltage_v"]) for string in strings for p in string["curve"]})

    def currents(voltage):
        return {string["id"]: _interp(string["curve"], voltage) for string in strings}

    def total_current(voltage):
        return sum(currents(voltage).values())

    best_voltage = None
    best_power = None

    def consider(voltage, current=None):
        nonlocal best_voltage, best_power
        if current is None:
            current = total_current(voltage)
        if current_limit is not None and current > current_limit + 1e-9:
            return
        power = voltage * current
        if best_power is None or power > best_power:
            best_voltage, best_power = voltage, power

    for voltage in voltages:
        consider(voltage)

    for v0, v1 in zip(voltages, voltages[1:]):
        i0 = total_current(v0)
        i1 = total_current(v1)
        slope = (i1 - i0) / (v1 - v0)
        intercept = i0 - slope * v0
        candidates = [v0, v1]
        if slope < 0.0:
            vertex = -intercept / (2.0 * slope)
            if v0 < vertex < v1:
                candidates.append(vertex)
            if current_limit is not None:
                crossing = (current_limit - intercept) / slope
                if v0 < crossing < v1:
                    candidates.append(crossing)
        for voltage in candidates:
            consider(voltage)

    output_currents = currents(best_voltage)
    return {
        "voltage_v": round(best_voltage, 3),
        "current_a": round(sum(output_currents.values()), 3),
        "power_w": round(best_power, 3),
        "string_currents_a": {
            string["id"]: round(output_currents[string["id"]], 3) for string in strings
        },
    }
