"""Irradiance reporting for the field audit."""

from __future__ import annotations


def estimate(payload):
    reference = int(round(float(payload["reference_irradiance_w_m2"])))
    return [reference for _section in payload["sections"]]
