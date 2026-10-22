"""Hidden acceptance checks for the photovoltaic string audit."""

import json
import os
import signal
import shutil
import subprocess
import tempfile
from pathlib import Path

ENTRY = "/app/main.py"
PYTHON = "/usr/local/bin/python3"
CANDIDATE_USER = "runner"
CANDIDATE_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/home/runner",
    "LANG": "C.UTF-8",
    "TZ": "UTC",
}
CALL_TIMEOUT_SEC = 30
TEST_DIR = Path(__file__).resolve().parent
FIXTURES = TEST_DIR / "fixtures"
EXPECTED = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))


def run_candidate(*args, timeout=CALL_TIMEOUT_SEC):
    as_root = os.getuid() == 0
    proc = subprocess.Popen(
        [PYTHON, ENTRY, *[str(arg) for arg in args]],
        cwd="/app",
        env=CANDIDATE_ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        user=CANDIDATE_USER if as_root else None,
        group=CANDIDATE_USER if as_root else None,
        extra_groups=[] if as_root else None,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise TimeoutError(f"{ENTRY} exceeded {timeout}s")
    return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)


def run_fixture(name):
    folder = Path(tempfile.mkdtemp(prefix="pv-audit-"))
    folder.chmod(0o755)
    target = folder / "input.json"
    shutil.copyfile(FIXTURES / f"{name}.json", target)
    target.chmod(0o644)
    proc = run_candidate(target)
    shutil.rmtree(folder, ignore_errors=True)
    assert proc.returncode == 0, f"exit={proc.returncode} stderr={proc.stderr[-500:]}"
    return json.loads(proc.stdout)


def run_payload(payload):
    folder = Path(tempfile.mkdtemp(prefix="pv-audit-"))
    folder.chmod(0o755)
    target = folder / "input.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    target.chmod(0o644)
    proc = run_candidate(target)
    shutil.rmtree(folder, ignore_errors=True)
    return proc


def assert_levels_close(got, expected, tolerance=4):
    assert len(got) == len(expected)
    assert all(abs(left - right) <= tolerance for left, right in zip(got, expected))


def assert_mpp_close(got, expected):
    assert abs(got["voltage_v"] - expected["voltage_v"]) <= 0.002
    assert abs(got["current_a"] - expected["current_a"]) <= 0.002
    assert abs(got["power_w"] - expected["power_w"]) <= 0.015
    assert set(got["string_currents_a"]) == set(expected["string_currents_a"])
    for string_id, value in expected["string_currents_a"].items():
        assert abs(got["string_currents_a"][string_id] - value) <= 0.002


# ---------- gate: entry contract, not scored ----------

def test_prints_one_json_object():
    """「处理规则见 `/app/SPEC.md`」"""
    got = run_fixture("bypass-basic")
    assert isinstance(got, dict)


def test_unknown_kind_or_missing_argument_exits_2():
    """「参数缺失或 kind 不识别时返回 2」"""
    missing = run_candidate()
    unknown = run_payload({"kind": "unknown"})
    assert missing.returncode == 2
    assert missing.stdout.strip() == ""
    assert unknown.returncode == 2
    assert unknown.stdout.strip() == ""


# ---------- difficulty 1: bypass state ----------

def test_bifacial_gain_changes_bypass_state():
    """「把 `/app/main.py` 改到能按那份交接单出结果」"""
    got = run_fixture("bypass-basic")
    assert got["bypassed_section_ids"] == EXPECTED["bypass-basic"]["bypassed_section_ids"]


def test_temperature_corrected_current_at_knee():
    """「把 `/app/main.py` 改到能按那份交接单出结果」"""
    got = run_fixture("bypass-knee")
    assert got["bypassed_section_ids"] == EXPECTED["bypass-knee"]["bypassed_section_ids"]


def test_hot_module_boundary_uses_isc_coefficient():
    """「把 `/app/main.py` 改到能按那份交接单出结果」"""
    got = run_fixture("bypass-hot")
    assert got["bypassed_section_ids"] == EXPECTED["bypass-hot"]["bypassed_section_ids"]


# ---------- difficulty 2: irradiance inversion ----------

def test_three_irradiance_levels_are_recovered():
    """「处理规则见 `/app/SPEC.md`」"""
    got = run_fixture("irr-three-levels")["irradiance_levels_w_m2"]
    assert_levels_close(got, EXPECTED["irr-three-levels"]["irradiance_levels_w_m2"])


def test_close_levels_near_bypass_knees_are_resolved():
    """「处理规则见 `/app/SPEC.md`」"""
    got = run_fixture("irr-near-knees")["irradiance_levels_w_m2"]
    assert_levels_close(got, EXPECTED["irr-near-knees"]["irradiance_levels_w_m2"])


def test_alternating_dark_and_bright_levels_are_recovered():
    """「处理规则见 `/app/SPEC.md`」"""
    got = run_fixture("irr-mixed")["irradiance_levels_w_m2"]
    assert_levels_close(got, EXPECTED["irr-mixed"]["irradiance_levels_w_m2"])


# ---------- difficulty 3: global MPP ----------

def test_single_curve_interior_maximum():
    """「把 `/app/main.py` 改到能按那份交接单出结果」"""
    got = run_fixture("mpp-single-shaded")
    assert_mpp_close(got, EXPECTED["mpp-single-shaded"]["exact"])


def test_parallel_misaligned_curves_share_one_voltage():
    """「处理规则见 `/app/SPEC.md`」"""
    got = run_fixture("mpp-parallel-misaligned")
    assert_mpp_close(got, EXPECTED["mpp-parallel-misaligned"]["exact"])


def test_interior_vertex_beats_all_scan_points():
    """「把 `/app/main.py` 改到能按那份交接单出结果」"""
    got = run_fixture("mpp-interior-vertex")
    assert_mpp_close(got, EXPECTED["mpp-interior-vertex"]["exact"])
