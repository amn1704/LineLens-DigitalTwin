"""Synthetic energy metering and derived sustainability metrics."""

import pytest

from backend.app.models import OperationalState
from backend.app.sustainability import DEFAULT_GRID_EMISSION_FACTOR, POWER_PROFILE, EnergyMeter, summarize_energy
from backend.app.simulation import SPECS, AssemblyLineSimulator


DOWNSTREAM = ("FA-03", "FA-04", "FA-05")


def run(seconds: float, *, chassis_drift: bool = False) -> AssemblyLineSimulator:
    simulator = AssemblyLineSimulator()
    simulator.pause()
    if chassis_drift:
        simulator.set_chassis_drift(True)
    for _ in range(int(seconds // 15)):
        simulator._advance(15)
    return simulator


def idle_share(reading, station_ids) -> float:
    total = sum(sum(reading.kwh_by_station_state[station_id].values()) for station_id in station_ids)
    idle = sum(
        kwh for station_id in station_ids
        for state, kwh in reading.kwh_by_station_state[station_id].items()
        if state in {"IDLE", "STARVED", "BLOCKED"}
    )
    return idle / total


def test_power_profile_is_complete_and_keeps_thermal_loads_largest():
    assert set(POWER_PROFILE) == {spec.station_id for spec in SPECS}
    paint_and_oven = {POWER_PROFILE["PAINT-02"].running_kw, POWER_PROFILE["PAINT-03"].running_kw}
    others = [profile.running_kw for station_id, profile in POWER_PROFILE.items() if station_id not in {"PAINT-02", "PAINT-03"}]
    assert min(paint_and_oven) > max(others)
    oven = POWER_PROFILE["PAINT-03"]
    assert oven.idle_kw >= 0.9 * oven.running_kw
    for station_id in ("BIW-01", "BIW-02", "BIW-03"):
        assert POWER_PROFILE[station_id].idle_kw <= 0.2 * POWER_PROFILE[station_id].running_kw
    assert all("Synthetic" in profile.source_note for profile in POWER_PROFILE.values())


def test_meter_uses_running_and_idle_power_by_state():
    meter = EnergyMeter(["PAINT-03"])
    meter.accumulate("PAINT-03", OperationalState.RUNNING, 3600)
    meter.accumulate("PAINT-03", OperationalState.STARVED, 1800)
    meter.accumulate("PAINT-03", OperationalState.BLOCKED, 1800)
    reading = meter.reading()
    assert reading.kwh_by_station_state["PAINT-03"]["RUNNING"] == pytest.approx(POWER_PROFILE["PAINT-03"].running_kw)
    assert reading.kwh_by_station_state["PAINT-03"]["STARVED"] == pytest.approx(POWER_PROFILE["PAINT-03"].idle_kw / 2)
    summary = summarize_energy(reading, {})
    assert summary.idle_kwh == pytest.approx(POWER_PROFILE["PAINT-03"].idle_kw, rel=1e-3)
    assert summary.kwh_per_vehicle is None


def test_energy_increases_monotonically_with_simulated_time():
    simulator = AssemblyLineSimulator()
    simulator.pause()
    try:
        previous = simulator.energy()
        previous_total = sum(sum(by_state.values()) for by_state in previous.kwh_by_station_state.values())
        for _ in range(12):
            simulator._advance(15)
            current = simulator.energy()
            total = sum(sum(by_state.values()) for by_state in current.kwh_by_station_state.values())
            assert total > previous_total
            for station_id, by_state in current.kwh_by_station_state.items():
                assert sum(by_state.values()) >= sum(previous.kwh_by_station_state[station_id].values())
            assert current.simulated_seconds == pytest.approx(previous.simulated_seconds + 15)
            previous, previous_total = current, total
    finally:
        simulator.shutdown()


def test_reset_zeroes_energy_and_per_vehicle_is_null_until_a_vehicle_completes():
    simulator = run(300)
    try:
        before = summarize_energy(simulator.energy(), {})
        assert before.total_kwh > 0
        assert before.vehicles_completed > 0
        assert before.kwh_per_vehicle == pytest.approx(before.total_kwh / before.vehicles_completed, rel=1e-3)
        # reset() resumes the background loop; hold the lock so no tick lands before the read.
        with simulator._lock:
            simulator.reset()
            simulator.pause()
            after = summarize_energy(simulator.energy(), {})
        assert after.total_kwh == 0
        assert after.idle_kwh == 0
        assert after.vehicles_completed == 0
        assert after.kwh_per_vehicle is None
        assert after.simulated_seconds == 0
    finally:
        simulator.shutdown()


def test_co2_equals_kwh_times_emission_factor():
    simulator = run(300)
    try:
        reading = simulator.energy()
        default = summarize_energy(reading, {})
        assert default.grid_emission_factor_kg_per_kwh == DEFAULT_GRID_EMISSION_FACTOR == 0.71
        assert "CEA" in default.emission_factor_note
        assert default.co2_kg == pytest.approx(default.total_kwh * 0.71, rel=1e-3)
        custom = summarize_energy(reading, {}, emission_factor=0.5)
        assert custom.co2_kg == pytest.approx(custom.total_kwh * 0.5, rel=1e-3)
        assert len(default.top_idle_stations) <= 3
        assert [station.idle_kwh for station in default.top_idle_stations] == sorted(
            (station.idle_kwh for station in default.top_idle_stations), reverse=True
        )
    finally:
        simulator.shutdown()


def test_chassis_bottleneck_raises_downstream_idle_energy_share():
    healthy = run(900)
    drifted = run(900, chassis_drift=True)
    try:
        healthy_reading, drifted_reading = healthy.energy(), drifted.energy()
        assert healthy_reading.simulated_seconds == pytest.approx(drifted_reading.simulated_seconds, abs=1)
        assert idle_share(drifted_reading, DOWNSTREAM) > idle_share(healthy_reading, DOWNSTREAM) * 1.25
    finally:
        healthy.shutdown()
        drifted.shutdown()
