"""Estimate effective irradiance levels for identical series sections."""

from __future__ import annotations

from pv_physics import cell_parameters, section_voltage


def _initial_levels(payload):
    sections = payload["sections"]
    sweep = payload["sweep"]
    derivatives = []
    for left, right in zip(sweep, sweep[1:]):
        delta_i = float(right["current_a"]) - float(left["current_a"])
        delta_v = float(right["voltage_v"]) - float(left["voltage_v"])
        derivatives.append(abs(delta_v / delta_i))
    peaks = []
    for index in range(1, len(derivatives) - 1):
        if derivatives[index] > derivatives[index - 1] and derivatives[index] >= derivatives[index + 1]:
            peaks.append((derivatives[index], index))
    peaks.sort(reverse=True)
    selected = sorted(peaks[: len(sections)], key=lambda item: item[1])
    isc_t, _a, _i0 = cell_parameters(payload["cell"], payload["temperature_c"])
    if len(selected) == len(sections):
        return sorted(float(sweep[index + 1]["current_a"]) * 1000.0 / isc_t for _value, index in selected)
    reference = float(payload["reference_irradiance_w_m2"])
    return [max(20.0, min(1200.0, reference * (index + 1) / (len(sections) + 1))) for index in range(len(sections))]


def _predicted(payload, levels):
    total = [0.0] * len(payload["sweep"])
    for level in levels:
        for index, point in enumerate(payload["sweep"]):
            voltage, _ = section_voltage(
                payload["sections"][0],
                payload["cell"],
                payload["temperature_c"],
                payload["bypass_forward_v"],
                float(point["current_a"]),
                level,
            )
            total[index] += voltage
    return total


def _sse(payload, levels):
    predicted = _predicted(payload, levels)
    return sum(
        (float(point["voltage_v"]) - value) ** 2
        for point, value in zip(payload["sweep"], predicted)
    )


def estimate(payload):
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
    return [int(round(value)) for value in sorted(levels)]
