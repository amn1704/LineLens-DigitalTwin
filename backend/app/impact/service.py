from __future__ import annotations

from ..incidents.models import Incident, IncidentStatus, IncidentType
from ..incidents.service import IncidentService
from ..models import TwinState
from ..prediction.models import PredictionState
from ..sustainability.energy import EnergyReading, IdleEnergyRisk, idle_energy_at_risk, summarize_energy
from .assumptions import ImpactAssumptions
from .models import EnergyImpact, ImpactReport, ProductionImpact, QualityImpact


# The same 10-minute no-intervention forecast that drives production incidents.
IMPACT_HORIZON = "600"
MATERIAL_IMPACTS = {"UPSTREAM_BLOCKING", "DOWNSTREAM_STARVATION", "THROUGHPUT_LOSS"}


class ImpactService:
    """Translates existing forecasts, quality outcomes and metered energy into
    assumption-based vehicles, ₹ and kWh.  It reads results; it never re-runs the
    forward simulation or changes the line."""

    def __init__(self) -> None:
        self._assumptions = ImpactAssumptions()

    @property
    def assumptions(self) -> ImpactAssumptions:
        return self._assumptions

    def set_assumptions(self, assumptions: ImpactAssumptions) -> ImpactAssumptions:
        self._assumptions = assumptions
        return assumptions

    def report(
        self,
        *,
        state: TwinState,
        prediction: PredictionState,
        energy: EnergyReading,
        quality_rows: list[dict],
        quality_metrics: dict,
        incidents: list[Incident],
    ) -> ImpactReport:
        assumptions = self._assumptions  # one consistent set for the whole report
        production = production_impact(prediction, assumptions)
        return ImpactReport(
            generated_at=state.simulation.simulation_time,
            assumptions=assumptions,
            production=production,
            quality=quality_impact(incidents, quality_rows, quality_metrics, assumptions),
            energy=energy_impact(state, prediction, energy, assumptions, production.bottleneck_active),
        )


def production_impact(prediction: PredictionState, assumptions: ImpactAssumptions) -> ProductionImpact:
    source_id = prediction.primary_station_id
    assessment = next((item for item in prediction.assessments if item.station_id == source_id), None)
    risk = assessment.risk if assessment else 0.0
    forecast = prediction.forecasts.get(IMPACT_HORIZON)
    method = (
        "(rolling throughput when the forecast was made − 10-minute no-intervention forecast throughput) "
        "× shift hours × contribution margin. Counted only while bottleneck risk is elevated."
    )
    if forecast is None:
        return ProductionImpact(
            bottleneck_active=False, source_station_id=source_id, source_risk=round(risk, 3),
            horizon_seconds=int(IMPACT_HORIZON), vehicles_at_risk_per_shift=0.0, contribution_at_risk_inr=0.0, method=method,
        )
    # The forward model compares its outcome with the throughput in its input
    # snapshot (trajectory offset 0); the estimate uses that same baseline.
    baseline = forecast.trajectory[0].throughput_per_hour if forecast.trajectory else None
    projected = forecast.metrics.throughput_per_hour
    active = risk >= IncidentService.PRODUCTION_RISK_THRESHOLD and any(
        impact.impact_type in MATERIAL_IMPACTS for impact in forecast.impacts
    )
    vehicles = max(0.0, baseline - projected) * assumptions.shift_hours if active and baseline is not None else 0.0
    return ProductionImpact(
        bottleneck_active=active, source_station_id=source_id, source_risk=round(risk, 3),
        horizon_seconds=forecast.scenario.horizon_seconds,
        baseline_throughput_per_hour=baseline, forecast_throughput_per_hour=projected,
        vehicles_at_risk_per_shift=round(vehicles, 1),
        contribution_at_risk_inr=round(vehicles * assumptions.contribution_margin_per_vehicle_inr),
        method=method,
    )


def quality_impact(
    incidents: list[Incident],
    quality_rows: list[dict],
    quality_metrics: dict,
    assumptions: ImpactAssumptions,
) -> QualityImpact:
    delta = assumptions.eol_rework_cost_inr - assumptions.inline_rework_cost_inr
    incident = next(
        (item for item in incidents if item.type == IncidentType.QUALITY and item.status != IncidentStatus.RESOLVED),
        None,
    )
    cohort = [
        row for row in quality_rows
        if float(row.get("risk", 0)) >= IncidentService.QUALITY_RISK_THRESHOLD
    ] if incident else []
    # Only bodies still on the line, without an End-of-Line outcome, can still be caught in-line.
    catchable = [row for row in cohort if row.get("active") and row.get("inspection_status", "PREDICTED") == "PREDICTED"]
    awaiting_outcomes = quality_metrics.get("validation_state") == "AWAITING_EOL_OUTCOMES"
    detections = None if awaiting_outcomes else int(quality_metrics.get("true_positives", 0))
    return QualityImpact(
        incident_active=incident is not None,
        incident_id=incident.incident_id if incident else None,
        exposed_vehicles=len(cohort), catchable_in_line=len(catchable),
        rework_cost_delta_inr=round(delta),
        potential_rework_avoided_inr=round(len(catchable) * max(0.0, delta)),
        validated_early_detections=detections,
        validated_rework_avoided_inr=round(detections * max(0.0, delta)) if detections is not None else None,
        method=(
            "Potential: flagged bodies still on the line × (End-of-Line rework − in-line rework). "
            "Validated: warnings later confirmed by synthetic End-of-Line outcomes × the same difference."
        ),
    )


def energy_impact(
    state: TwinState,
    prediction: PredictionState,
    energy: EnergyReading,
    assumptions: ImpactAssumptions,
    bottleneck_active: bool,
) -> EnergyImpact:
    names = {station.id: station.name for station in state.stations}
    summary = summarize_energy(energy, names, assumptions.grid_emission_factor_kg_per_kwh)
    forecast = prediction.forecasts.get(IMPACT_HORIZON)
    if forecast is not None and bottleneck_active:
        expected_cycles = {
            station.id: station.twin.expected_cycle if station.twin else station.nominal_cycle_time
            for station in state.stations
        }
        at_risk = idle_energy_at_risk(forecast, expected_cycles, state.simulation.takt_time)
    else:
        at_risk = IdleEnergyRisk(horizon_seconds=int(IMPACT_HORIZON), kwh=0.0, stations=[])
    per_shift = at_risk.kwh / max(at_risk.horizon_seconds, 1) * assumptions.shift_hours * 3600
    tariff = assumptions.electricity_tariff_inr_per_kwh
    return EnergyImpact(
        simulated_seconds=summary.simulated_seconds, vehicles_completed=summary.vehicles_completed,
        total_kwh=round(summary.total_kwh, 2), kwh_per_vehicle=summary.kwh_per_vehicle,
        idle_kwh=round(summary.idle_kwh, 2), idle_energy_share=summary.idle_energy_share,
        energy_cost_inr=round(summary.total_kwh * tariff), idle_energy_cost_inr=round(summary.idle_kwh * tariff),
        co2_kg=round(summary.co2_kg, 2), grid_emission_factor_kg_per_kwh=summary.grid_emission_factor_kg_per_kwh,
        top_idle_stations=summary.top_idle_stations,
        idle_energy_at_risk_kwh=round(at_risk.kwh, 3), idle_energy_at_risk_horizon_seconds=at_risk.horizon_seconds,
        idle_energy_at_risk_kwh_per_shift=round(per_shift, 1),
        idle_energy_at_risk_inr_per_shift=round(per_shift * tariff),
        idle_energy_at_risk_stations=at_risk.stations,
        method=(
            "Metered from the synthetic power profile in simulated seconds since reset. "
            "At risk: forecast starved/blocked time beyond normal takt idle at affected stations × idle power, "
            "extrapolated to one shift."
        ),
    )
