from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from ..models import OperationalState
from ..prediction.models import ForwardResult


@dataclass(frozen=True)
class StationPower:
    running_kw: float
    idle_kw: float
    source_note: str


# Synthetic, illustrative power draw per station.  These are not measured plant
# values; they only keep the relative pattern plausible (paint and curing are the
# heavy thermal loads, a curing oven cannot shut down when starved, robot cells
# draw little when waiting).  Edit them here to explore a different line.
POWER_PROFILE: dict[str, StationPower] = {
    "BIW-01": StationPower(22.0, 3.5, "Synthetic · framing robots and clamps; servo hold when waiting"),
    "BIW-02": StationPower(45.0, 5.0, "Synthetic · spot-weld transformers draw power only while welding"),
    "BIW-03": StationPower(28.0, 4.0, "Synthetic · underbody joining robots; low standby"),
    "PAINT-01": StationPower(60.0, 38.0, "Synthetic · heated pretreatment baths and pumps keep circulating"),
    "PAINT-02": StationPower(140.0, 92.0, "Synthetic · booth air supply and conditioning keep running between bodies"),
    "PAINT-03": StationPower(125.0, 116.0, "Synthetic · thermal oven must stay at temperature when starved or blocked"),
    "FA-01": StationPower(8.0, 2.0, "Synthetic · trim tools and lighting"),
    "FA-02": StationPower(30.0, 6.0, "Synthetic · marriage lift, AGV and nutrunners"),
    "FA-03": StationPower(14.0, 3.0, "Synthetic · wheel nutrunners; low standby"),
    "FA-04": StationPower(10.0, 4.0, "Synthetic · calibration targets and lighting stay on"),
    "FA-05": StationPower(35.0, 10.0, "Synthetic · roller and functional test benches"),
}

DEFAULT_GRID_EMISSION_FACTOR = 0.71
EMISSION_FACTOR_NOTE = "approx. Indian grid average — verify against the latest CEA CO2 Baseline Database"
POWER_PROFILE_LABEL = "Synthetic power profile · illustrative"

RUNNING_STATES = {OperationalState.RUNNING, OperationalState.WARNING}
IDLE_STATES = {OperationalState.IDLE, OperationalState.STARVED, OperationalState.BLOCKED, OperationalState.CHANGEOVER}


def station_power_kw(station_id: str, state: OperationalState) -> float:
    profile = POWER_PROFILE[station_id]
    if state in RUNNING_STATES:
        return profile.running_kw
    if state in IDLE_STATES:
        return profile.idle_kw
    return 0.0


@dataclass(frozen=True)
class EnergyReading:
    """An immutable copy of the meter, safe to use outside the simulator lock."""

    kwh_by_station_state: dict[str, dict[str, float]]
    vehicles_completed: int
    simulated_seconds: float


@dataclass
class EnergyMeter:
    """Synthetic per-station energy meter driven by simulated seconds.

    The simulator owns one meter and calls it while holding its own lock, so the
    meter itself keeps no lock.
    """

    station_ids: list[str]
    _kwh: dict[str, dict[str, float]] = field(init=False)
    _vehicles_completed: int = field(init=False, default=0)
    _seconds: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._kwh = {station_id: {} for station_id in self.station_ids}
        self._vehicles_completed = 0
        self._seconds = 0.0

    def accumulate(self, station_id: str, state: OperationalState, seconds: float) -> None:
        if seconds <= 0:
            return
        by_state = self._kwh[station_id]
        by_state[state.value] = by_state.get(state.value, 0.0) + station_power_kw(station_id, state) * seconds / 3600

    def advance_clock(self, seconds: float) -> None:
        self._seconds += max(0.0, seconds)

    def record_completion(self) -> None:
        self._vehicles_completed += 1

    def reading(self) -> EnergyReading:
        return EnergyReading(
            kwh_by_station_state={station_id: dict(by_state) for station_id, by_state in self._kwh.items()},
            vehicles_completed=self._vehicles_completed,
            simulated_seconds=self._seconds,
        )


class StationEnergy(BaseModel):
    station_id: str
    station_name: str
    total_kwh: float = Field(ge=0)
    idle_kwh: float = Field(ge=0)
    idle_energy_share: float = Field(ge=0, le=1)
    kwh_by_state: dict[str, float]
    running_kw: float
    idle_kw: float
    source_note: str


class EnergySummary(BaseModel):
    label: str = POWER_PROFILE_LABEL
    simulated_seconds: float
    total_kwh: float = Field(ge=0)
    idle_kwh: float = Field(ge=0)
    idle_energy_share: float = Field(ge=0, le=1)
    vehicles_completed: int
    kwh_per_vehicle: float | None = None
    co2_kg: float = Field(ge=0)
    grid_emission_factor_kg_per_kwh: float
    emission_factor_note: str = EMISSION_FACTOR_NOTE
    top_idle_stations: list[StationEnergy]
    stations: list[StationEnergy]


def _idle_kwh(by_state: dict[str, float]) -> float:
    return sum(kwh for state, kwh in by_state.items() if OperationalState(state) in IDLE_STATES)


def summarize_energy(
    reading: EnergyReading,
    station_names: dict[str, str],
    emission_factor: float = DEFAULT_GRID_EMISSION_FACTOR,
) -> EnergySummary:
    stations: list[StationEnergy] = []
    for station_id, by_state in reading.kwh_by_station_state.items():
        total = sum(by_state.values())
        idle = _idle_kwh(by_state)
        profile = POWER_PROFILE[station_id]
        stations.append(StationEnergy(
            station_id=station_id, station_name=station_names.get(station_id, station_id),
            total_kwh=round(total, 4), idle_kwh=round(idle, 4),
            idle_energy_share=round(idle / total, 4) if total > 0 else 0.0,
            kwh_by_state={state: round(kwh, 4) for state, kwh in by_state.items()},
            running_kw=profile.running_kw, idle_kw=profile.idle_kw, source_note=profile.source_note,
        ))
    total_kwh = sum(sum(by_state.values()) for by_state in reading.kwh_by_station_state.values())
    idle_kwh = sum(_idle_kwh(by_state) for by_state in reading.kwh_by_station_state.values())
    top_idle = sorted((station for station in stations if station.idle_kwh > 0), key=lambda station: station.idle_kwh, reverse=True)[:3]
    return EnergySummary(
        simulated_seconds=round(reading.simulated_seconds, 1),
        total_kwh=round(total_kwh, 4), idle_kwh=round(idle_kwh, 4),
        idle_energy_share=round(idle_kwh / total_kwh, 4) if total_kwh > 0 else 0.0,
        vehicles_completed=reading.vehicles_completed,
        # Null until a vehicle completes: a partial line has no honest per-vehicle figure.
        kwh_per_vehicle=round(total_kwh / reading.vehicles_completed, 3) if reading.vehicles_completed else None,
        co2_kg=round(total_kwh * emission_factor, 4),
        grid_emission_factor_kg_per_kwh=emission_factor,
        top_idle_stations=top_idle, stations=stations,
    )


class StationIdleRisk(BaseModel):
    station_id: str
    excess_idle_seconds: float = Field(ge=0)
    idle_kw: float
    kwh: float = Field(ge=0)


class IdleEnergyRisk(BaseModel):
    horizon_seconds: int
    kwh: float = Field(ge=0)
    stations: list[StationIdleRisk]


def idle_energy_at_risk(
    forecast: ForwardResult,
    expected_cycles: dict[str, float],
    takt_seconds: float,
) -> IdleEnergyRisk:
    """Extra idle energy the no-intervention forecast implies at affected stations.

    Only stations the forecast flags as starved or blocked count.  Their forecast
    starved and blocked time is compared with the idle time a healthy station
    already has between vehicles (takt minus its normal cycle), and only the
    excess is multiplied by the station's synthetic idle power.
    """
    horizon = forecast.scenario.horizon_seconds
    affected = {
        impact.entity_id
        for impact in forecast.impacts
        if impact.entity_type == "STATION" and impact.impact_type in {"DOWNSTREAM_STARVATION", "UPSTREAM_BLOCKING"}
    }
    rows: list[StationIdleRisk] = []
    for station_id in sorted(affected):
        if station_id not in POWER_PROFILE:
            continue
        forecast_idle = (
            forecast.metrics.station_starved_seconds.get(station_id, 0.0)
            + forecast.metrics.station_blocked_seconds.get(station_id, 0.0)
        )
        expected_cycle = expected_cycles.get(station_id, takt_seconds)
        normal_idle = horizon * max(0.0, takt_seconds - expected_cycle) / max(takt_seconds, 1.0)
        excess = max(0.0, forecast_idle - normal_idle)
        idle_kw = POWER_PROFILE[station_id].idle_kw
        rows.append(StationIdleRisk(
            station_id=station_id, excess_idle_seconds=round(excess, 1), idle_kw=idle_kw,
            kwh=round(excess * idle_kw / 3600, 4),
        ))
    return IdleEnergyRisk(horizon_seconds=horizon, kwh=round(sum(row.kwh for row in rows), 4), stations=rows)
