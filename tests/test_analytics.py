"""Tests for the pure analytics logic (no Home Assistant needed)."""

import importlib.util
import pathlib
import sys
import types

BASE = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "grillfuerst_p530e"
pkg = types.ModuleType("gp")
pkg.__path__ = [str(BASE)]
sys.modules["gp"] = pkg
for name in ("const", "analytics"):
    spec = importlib.util.spec_from_file_location(f"gp.{name}", BASE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"gp.{name}"] = mod
    spec.loader.exec_module(mod)
from gp.analytics import GrillAnalytics, SESSION_END_AFTER  # noqa: E402


def poll(a, t, chamber=None, gas=None, probe1=None, target1=None, mode=0, target=230):
    data = {"114": mode, "110": target, "106": target1 or 0}
    if chamber is not None:
        data["101"] = chamber
    if gas is not None:
        data["119"] = round(gas * 10)
    if probe1 is not None:
        data["102"] = probe1
    a.update(t, data)


def test_gas_counts_steps_ignores_noise_and_refill():
    a = GrillAnalytics()
    poll(a, 0, gas=3.0)
    poll(a, 15, gas=2.9)            # 0.1 used
    poll(a, 30, gas=3.0)            # noise up: ignored
    poll(a, 45, gas=2.9)            # back to ref: not counted again
    poll(a, 60, gas=2.7)            # 0.2 used
    assert round(a.gas_consumed, 2) == 0.3
    poll(a, 75, gas=11.0)           # new cylinder
    poll(a, 90, gas=10.9)
    assert round(a.gas_consumed, 2) == 0.4
    poll(a, 105, gas=0.0)           # cylinder taken off: no consumption
    assert round(a.gas_consumed, 2) == 0.4
    assert round(a.gas_energy, 2) == round(0.4 * 12.8, 2)


def test_session_and_rate():
    a = GrillAnalytics()
    t = 0
    gas = 5.0
    while t <= 3600:                # one hour hot, 0.6 kg used
        poll(a, t, chamber=220, gas=gas)
        t += 60
        if t % 600 == 0:
            gas -= 0.1
    assert a.grilling
    poll(a, t, chamber=30, gas=gas)
    poll(a, t + SESSION_END_AFTER + 60, chamber=25, gas=gas)
    assert not a.grilling
    s = a.last_session
    assert s and 3500 <= s["duration"] <= 3700 and s["max_temp"] == 220
    assert 0.5 <= s["gas_used"] <= 0.7
    assert a.gas_rate is not None and 0.4 < a.gas_rate < 0.8
    assert 5 < a.runtime_left(4.0) < 10


def test_offline_ends_session_and_eta():
    a = GrillAnalytics()
    for i, temp in enumerate([20, 25, 30, 35, 40]):
        poll(a, i * 60, chamber=200, probe1=temp, target1=60)
    eta = a.probe_eta(0, {"106": 60})
    assert eta is not None and 230 < eta < 250   # 5 °C/min → 20 °C to go ≈ 240 s
    assert a.preheat_eta({"114": 0, "110": 230}) is None   # chamber flat
    a.update(300, None)
    a.update(300 + SESSION_END_AFTER + 1, None)
    assert not a.grilling and a.last_session is not None


def test_roundtrip():
    a = GrillAnalytics(gas_consumed=1.234, active_seconds=4000, active_gas=0.8)
    b = GrillAnalytics.from_dict(a.as_dict())
    assert b.gas_consumed == 1.234 and b.active_seconds == 4000 and b.gas_rate is not None
