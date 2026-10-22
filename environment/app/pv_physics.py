"""Electrical helpers shared by the PV audit commands."""

from __future__ import annotations

import math

Q = 1.602176634e-19
K = 1.380649e-23
T_REF = 25.0
G_REF = 1000.0


def cell_parameters(cell, temperature_c):
    tk = temperature_c + 273.15
    isc_t = cell["isc_stc_a"] * (
        1.0 + cell["alpha_isc_pct_per_c"] / 100.0 * (temperature_c - T_REF)
    )
    voc_t = cell["voc_stc_v"] * (
        1.0 + cell["beta_voc_pct_per_c"] / 100.0 * (temperature_c - T_REF)
    )
    a_cell = cell["ideality_factor"] * K * tk / Q
    i0 = isc_t / math.exp(voc_t / a_cell)
    return isc_t, a_cell, i0


def effective_irradiance(section, bifaciality):
    return section["front_irradiance_w_m2"] + bifaciality * section["rear_irradiance_w_m2"]


def section_voltage(section, cell, temperature_c, bypass_forward_v, current_a, irradiance):
    isc_t, a_cell, i0 = cell_parameters(cell, temperature_c)
    cells = int(section["cells"])
    iph = isc_t * irradiance / G_REF
    if current_a >= iph:
        return -bypass_forward_v, True
    active = cells * a_cell * math.log((iph - current_a) / i0) - current_a * cells * cell["series_ohm"]
    if active <= -bypass_forward_v:
        return -bypass_forward_v, True
    return active, False


def string_voltage(sections, irradiances, cell, temperature_c, bypass_forward_v, current_a):
    voltage = 0.0
    bypassed = []
    for section, irradiance in zip(sections, irradiances):
        section_v, state = section_voltage(
            section, cell, temperature_c, bypass_forward_v, current_a, irradiance
        )
        voltage += section_v
        if state:
            bypassed.append(section["id"])
    return voltage, bypassed
