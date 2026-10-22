"""Estimate effective irradiance levels for identical series sections."""

from __future__ import annotations

from pv_physics import cell_parameters, section_voltage


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


def _knee_guesses(payload, count):
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
    isc_t, _a, _i0 = cell_parameters(payload["cell"], payload["temperature_c"])
    guesses = []
    for _value, index in sorted(peaks[:count], key=lambda item: item[1]):
        guesses.append(float(sweep[index + 1]["current_a"]) * 1000.0 / isc_t)
    return guesses


def _refine(payload, start):
    levels = sorted(max(1.0, min(1300.0, float(value))) for value in start)
    best_error = _sse(payload, levels)
    for step in (200.0, 50.0, 10.0, 2.0, 1.0):
        for _pass in range(2):
            for index in range(len(levels)):
                center = levels[index]
                best_value = center
                best_local = best_error
                for offset in range(-5, 6):
                    value = max(1.0, min(1300.0, center + offset * step))
                    trial = levels[:]
                    trial[index] = value
                    error = _sse(payload, trial)
                    if error < best_local:
                        best_local = error
                        best_value = value
                levels[index] = best_value
                best_error = best_local
            levels.sort()
    return levels, best_error


def estimate(payload):
    count = len(payload["sections"])
    reference = float(payload["reference_irradiance_w_m2"])
    starts = [
        [reference] * count,
        [200.0 + 160.0 * index for index in range(count)],
        [100.0 + 200.0 * index for index in range(count)],
    ]
    knees = _knee_guesses(payload, count)
    if knees:
        padded = knees + [reference] * max(0, count - len(knees))
        starts.append(padded[:count])
    best_levels = None
    best_error = None
    for start in starts:
        levels, error = _refine(payload, start)
        if best_error is None or error < best_error:
            best_levels, best_error = levels, error
    return [int(round(value)) for value in sorted(best_levels)]
