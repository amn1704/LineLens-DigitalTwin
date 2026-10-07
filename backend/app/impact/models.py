from __future__ import annotations

from pydantic import BaseModel, Field

from ..sustainability.energy import EMISSION_FACTOR_NOTE, POWER_PROFILE_LABEL, StationEnergy, StationIdleRisk
from .assumptions import ImpactAssumptions


class ProductionImpact(BaseModel):
    bottleneck_active: bool
    source_station_id: str
    source_risk: float = Field(ge=0, le=1)
    horizon_seconds: int
    baseline_throughput_per_hour: float | None = None
    forecast_throughput_per_hour: float | None = None
    vehicles_at_risk_per_shift: float = Field(ge=0)
    contribution_at_risk_inr: float = Field(ge=0)
    method: str


class QualityImpact(BaseModel):
    incident_active: bool
    incident_id: str | None = None
    exposed_vehicles: int = Field(ge=0)
    catchable_in_line: int = Field(ge=0)
    rework_cost_delta_inr: float
    potential_rework_avoided_inr: float = Field(ge=0)
    validated_early_detections: int | None = None
    validated_rework_avoided_inr: float | None = None
    method: str


class EnergyImpact(BaseModel):
    label: str = POWER_PROFILE_LABEL
    simulated_seconds: float
    vehicles_completed: int
    total_kwh: float = Field(ge=0)
    kwh_per_vehicle: float | None = None
    idle_kwh: float = Field(ge=0)
    idle_energy_share: float = Field(ge=0, le=1)
    energy_cost_inr: float = Field(ge=0)
    idle_energy_cost_inr: float = Field(ge=0)
    co2_kg: float = Field(ge=0)
    grid_emission_factor_kg_per_kwh: float
    emission_factor_note: str = EMISSION_FACTOR_NOTE
    top_idle_stations: list[StationEnergy]
    idle_energy_at_risk_kwh: float = Field(ge=0)
    idle_energy_at_risk_horizon_seconds: int
    idle_energy_at_risk_kwh_per_shift: float = Field(ge=0)
    idle_energy_at_risk_inr_per_shift: float = Field(ge=0)
    idle_energy_at_risk_stations: list[StationIdleRisk]
    method: str


class ImpactReport(BaseModel):
    generated_at: float
    label: str = "Assumption-based estimate · synthetic data · illustrative assumptions"
    assumptions: ImpactAssumptions
    production: ProductionImpact
    quality: QualityImpact
    energy: EnergyImpact
