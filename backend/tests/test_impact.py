"""Assumption-based business impact derived from existing forecasts, outcomes and energy."""

import pytest
from fastapi.testclient import TestClient

from backend.app.impact import ImpactAssumptions, ImpactService
from backend.app.incidents import IncidentService
from backend.app.prediction import PredictionService
from backend.app.simulation import AssemblyLineSimulator


class Line:
    """The same evaluation path as the API: state → prediction → incidents → impact."""

    def __init__(self) -> None:
        self.simulator = AssemblyLineSimulator()
        self.simulator.pause()
        self.predictions = PredictionService()
        self.incidents = IncidentService()

    def inputs(self) -> dict:
        state = self.simulator.state()
        prediction = self.predictions.prediction(state, "FA-02")
        rows = self.simulator.quality_monitored_vehicles()
        self.incidents.evaluate(state, prediction, rows, self.simulator.quality_genealogy())
        return dict(
            state=state, prediction=prediction, energy=self.simulator.energy(), quality_rows=rows,
            quality_metrics=self.simulator.quality_metrics(), incidents=self.incidents.list_incidents(),
        )

    def bottleneck_demo(self) -> dict:
        # Mirrors the Demo → Bottleneck sequence used by the frontend.
        self.simulator.set_chassis_drift(True)
        self.simulator.advance_demo(380)
        self.inputs()
        self.simulator.advance_demo(20)
        return self.inputs()

    def quality_demo(self) -> dict:
        self.simulator.set_weld_drift(True)
        self.simulator.advance_demo(1800)
        return self.inputs()

    def close(self) -> None:
        self.simulator.shutdown()


def report(inputs: dict, **assumptions):
    service = ImpactService()
    service.set_assumptions(ImpactAssumptions(**assumptions))
    return service.report(**inputs)


def test_healthy_line_has_zero_value_at_risk():
    line = Line()
    try:
        line.simulator.advance_demo(400)
        result = report(line.inputs())
        assert result.production.bottleneck_active is False
        assert result.production.vehicles_at_risk_per_shift == 0
        assert result.production.contribution_at_risk_inr == 0
        assert result.energy.idle_energy_at_risk_kwh == 0
        assert result.quality.incident_active is False
        assert result.quality.potential_rework_avoided_inr == 0
        # Energy is still metered on a calm line.
        assert result.energy.total_kwh > 0
        assert result.energy.kwh_per_vehicle is not None
    finally:
        line.close()


def test_bottleneck_demo_produces_positive_vehicles_at_risk():
    line = Line()
    try:
        result = report(line.bottleneck_demo())
        production = result.production
        assert production.bottleneck_active is True
        assert production.vehicles_at_risk_per_shift > 0
        expected = (production.baseline_throughput_per_hour - production.forecast_throughput_per_hour) * 8
        assert production.vehicles_at_risk_per_shift == pytest.approx(expected, abs=0.1)
        assert production.contribution_at_risk_inr == pytest.approx(production.vehicles_at_risk_per_shift * 50_000, abs=1)
        assert result.energy.idle_energy_at_risk_kwh > 0
        assert result.energy.idle_energy_at_risk_stations
    finally:
        line.close()


def test_quality_demo_produces_positive_potential_rework_avoided():
    line = Line()
    try:
        result = report(line.quality_demo())
        quality = result.quality
        assert quality.incident_active is True
        assert quality.catchable_in_line > 0
        assert quality.exposed_vehicles >= quality.catchable_in_line
        assert quality.rework_cost_delta_inr == 6_000 - 1_500
        assert quality.potential_rework_avoided_inr == quality.catchable_in_line * 4_500
        assert quality.validated_early_detections is not None
        assert quality.validated_rework_avoided_inr == quality.validated_early_detections * 4_500
    finally:
        line.close()


def test_changing_an_assumption_changes_output_proportionally():
    line = Line()
    try:
        inputs = line.bottleneck_demo()
        base = report(inputs)
        assert base.production.contribution_at_risk_inr > 0
        margin = report(inputs, contribution_margin_per_vehicle_inr=100_000)
        assert margin.production.contribution_at_risk_inr == pytest.approx(2 * base.production.contribution_at_risk_inr, abs=1)
        shift = report(inputs, shift_hours=16)
        assert shift.production.vehicles_at_risk_per_shift == pytest.approx(2 * base.production.vehicles_at_risk_per_shift, abs=0.1)
        assert shift.energy.idle_energy_at_risk_kwh_per_shift == pytest.approx(2 * base.energy.idle_energy_at_risk_kwh_per_shift, abs=0.1)
        tariff = report(inputs, electricity_tariff_inr_per_kwh=16)
        assert tariff.energy.energy_cost_inr == pytest.approx(2 * base.energy.energy_cost_inr, abs=1)
        emission = report(inputs, grid_emission_factor_kg_per_kwh=1.42)
        assert emission.energy.co2_kg == pytest.approx(2 * base.energy.co2_kg, rel=1e-3)
        # Assumptions change only the translation, never the underlying evidence.
        assert margin.production.forecast_throughput_per_hour == base.production.forecast_throughput_per_hour
        assert tariff.energy.total_kwh == base.energy.total_kwh
    finally:
        line.close()


def test_assumptions_are_illustrative_and_documented():
    for name, field in ImpactAssumptions.model_fields.items():
        assert field.description, name
        assert "llustrative" in field.description, name
    defaults = ImpactAssumptions()
    assert defaults.shift_hours == 8
    assert defaults.grid_emission_factor_kg_per_kwh == 0.71


@pytest.fixture(scope="module")
def client():
    from backend.app.main import app, simulator

    simulator.pause()
    with TestClient(app) as test_client:
        yield test_client
        test_client.put("/api/impact/assumptions", json={})


def test_impact_endpoint_returns_every_section_with_assumptions(client):
    response = client.get("/api/impact")
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"assumptions", "production", "quality", "energy", "label"}
    assert "Assumption-based" in body["label"]
    assert body["energy"]["label"] == "Synthetic power profile · illustrative"


def test_assumptions_round_trip_and_reject_negative_values_with_422(client):
    original = client.get("/api/impact/assumptions").json()
    updated = client.put("/api/impact/assumptions", json={**original, "electricity_tariff_inr_per_kwh": 9.5})
    assert updated.status_code == 200
    assert client.get("/api/impact/assumptions").json()["electricity_tariff_inr_per_kwh"] == 9.5
    assert client.get("/api/impact").json()["assumptions"]["electricity_tariff_inr_per_kwh"] == 9.5
    for field in ImpactAssumptions.model_fields:
        rejected = client.put("/api/impact/assumptions", json={**original, field: -1})
        assert rejected.status_code == 422, field
    assert client.get("/api/impact/assumptions").json()["electricity_tariff_inr_per_kwh"] == 9.5
    # An empty replacement restores the illustrative defaults.
    assert client.put("/api/impact/assumptions", json={}).json() == ImpactAssumptions().model_dump()
