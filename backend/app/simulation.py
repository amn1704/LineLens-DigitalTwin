from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import sin
from threading import Event, RLock, Thread
from time import monotonic, sleep

from .models import (
    AccumulationBuffer,
    DefectFamily,
    Health,
    HistoryPoint,
    InspectionResult,
    InspectionStatus,
    OperationalEvent,
    OperationalState,
    ProcessStep,
    QualityLevel,
    Section,
    SensorMode,
    SimulationInfo,
    Station,
    StationObservation,
    TwinState,
    Vehicle,
    VehicleThread,
    VehicleStatus,
)
from .quality import QualityService
from .twin.estimator import StationDefinition, TwinStateEstimator


TAKT_SECONDS = 60.0
DEFAULT_SPEED = 8.0
TRANSFER_SECONDS = 4.0
MAX_EVENTS = 8
MAX_HISTORY = 90
MAX_VEHICLE_THREADS = 240
ASSIMILATION_SECONDS = 2.0
NOISE_PATTERN = (0.15, -0.85, 0.62, -0.35, 1.0, -0.58, 0.42, -1.0, 0.75, -0.2)


@dataclass(frozen=True)
class StationSpec:
    station_id: str
    name: str
    section: Section
    process: str
    nominal_cycle: float
    incoming_queue_capacity: int
    sensor_mode: SensorMode


SPECS = [
    StationSpec("BIW-01", "Body Framing Cell", Section.BODY_SHOP, "Frame and clamp", 57.0, 2, SensorMode.FULL),
    StationSpec("BIW-02", "Robotic Weld Cell", Section.BODY_SHOP, "Spot welding", 58.0, 1, SensorMode.FULL),
    StationSpec("BIW-03", "Underbody Cell", Section.BODY_SHOP, "Underbody joining", 56.0, 1, SensorMode.LIMITED),
    StationSpec("PAINT-01", "Pretreatment Tunnel", Section.PAINT_SHOP, "Surface preparation", 55.0, 1, SensorMode.BASIC),
    StationSpec("PAINT-02", "Paint Booth", Section.PAINT_SHOP, "Base coat application", 58.0, 1, SensorMode.FULL),
    StationSpec("PAINT-03", "Curing Oven", Section.PAINT_SHOP, "Thermal cure", 57.0, 1, SensorMode.LIMITED),
    StationSpec("FA-01", "Trim Station", Section.FINAL_ASSEMBLY, "Interior trim installation", 59.0, 1, SensorMode.BASIC),
    StationSpec("FA-02", "Chassis Marriage", Section.FINAL_ASSEMBLY, "Powertrain integration", 60.0, 1, SensorMode.FULL),
    StationSpec("FA-03", "Wheel & Torque", Section.FINAL_ASSEMBLY, "Wheel fastening", 56.0, 1, SensorMode.FULL),
    StationSpec("FA-04", "ADAS Calibration", Section.FINAL_ASSEMBLY, "Sensor calibration", 58.0, 1, SensorMode.FULL),
    StationSpec("FA-05", "End-of-Line Inspection", Section.FINAL_ASSEMBLY, "Final functional test", 54.0, 1, SensorMode.LIMITED),
]


@dataclass(frozen=True)
class ConnectionSpec:
    upstream_index: int
    downstream_index: int
    mode: str
    capacity: int
    buffer_id: str | None = None
    buffer_name: str | None = None


CONNECTIONS = [
    ConnectionSpec(0, 1, "DIRECT_COUPLED", 1),
    ConnectionSpec(1, 2, "SHORT_QUEUE", 1),
    ConnectionSpec(2, 3, "ACCUMULATION_BUFFER", 4, "BODY-ACC", "Body Shop Exit Accumulator"),
    ConnectionSpec(3, 4, "DIRECT_COUPLED", 1),
    ConnectionSpec(4, 5, "SHORT_QUEUE", 1),
    ConnectionSpec(5, 6, "ACCUMULATION_BUFFER", 5, "PBS", "Painted Body Storage"),
    ConnectionSpec(6, 7, "DIRECT_COUPLED", 1),
    ConnectionSpec(7, 8, "SHORT_QUEUE", 1),
    ConnectionSpec(8, 9, "DIRECT_COUPLED", 1),
    ConnectionSpec(9, 10, "SHORT_QUEUE", 1),
]

VARIANTS = (("Sedan", "#4f85a6", 1.0), ("SUV", "#596b7f", 1.04), ("EV", "#2f9aa3", 1.035))


@dataclass
class VehicleRuntime:
    vehicle_id: str
    variant: str
    body_color: str
    factor: float
    batch_id: str
    entry_time: float
    current_index: int | None = None
    next_index: int | None = None
    status: VehicleStatus = VehicleStatus.BUFFERED
    process_elapsed: float = 0.0
    active_cycle: float = 0.0
    transfer_started: float = 0.0
    transfer_ends: float = 0.0
    active_process_entry: float | None = None
    build_steps: list[ProcessStep] = field(default_factory=list)
    buffer_id: str | None = None
    queue_kind: str | None = None
    # Phase 4: Latent quality state (hidden from predictor)
    latent_quality_score: float = 1.0  # 1.0 = perfect, degrades with process issues
    latent_defect: bool = False  # Ground truth for simulation/validation
    quality_prediction_updated: bool = False


@dataclass
class StationRuntime:
    spec: StationSpec
    queue: deque[str] = field(default_factory=deque)
    current_vehicle: str | None = None
    current_cycle: float = 0.0
    elapsed: float = 0.0
    busy_seconds: float = 0.0
    vehicles_completed: int = 0
    operational_state: OperationalState = OperationalState.IDLE
    blocked_since: float | None = None
    last_completed_cycle: float | None = None
    last_departure_time: float | None = None


class AssemblyLineSimulator:
    """Thread-safe, accelerated, deterministic production-flow simulator for LineLens."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._stop = Event()
        self._last_wall = monotonic()
        self._running = True
        self._speed = DEFAULT_SPEED
        self._thread = Thread(target=self._loop, daemon=True, name="linelens-simulation")
        self._quality_service = QualityService()
        self.reset(start_thread=False)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                now = monotonic()
                elapsed = min(0.5, max(0.0, now - self._last_wall))
                self._last_wall = now
                if self._running:
                    self._advance(elapsed * self._speed)
            sleep(0.2)

    def reset(self, start_thread: bool = False) -> None:
        del start_thread  # Keeps reset callable from initialization and API without a special branch.
        with self._lock:
            self._simulation_time = 1_200.0
            self._stations = [StationRuntime(spec=spec) for spec in SPECS]
            self._buffers: dict[str, deque[str]] = {
                connection.buffer_id: deque()
                for connection in CONNECTIONS
                if connection.buffer_id is not None
            }
            self._vehicles: dict[str, VehicleRuntime] = {}
            self._transfers: dict[str, VehicleRuntime] = {}
            self._events: deque[OperationalEvent] = deque(maxlen=MAX_EVENTS)
            self._history: deque[HistoryPoint] = deque(maxlen=MAX_HISTORY)
            self._completion_times: deque[float] = deque(maxlen=200)
            self._vehicle_threads: OrderedDict[str, VehicleThread] = OrderedDict()
            self._telemetry_dropouts: set[str] = set()
            self._telemetry_noise: dict[str, float] = {}
            self._active_scenario: str | None = None
            self._scenario_started: float | None = None
            # Phase 4: Weld process drift state
            self._weld_drift_active: bool = False
            self._weld_drift_started: float | None = None
            self._weld_gun_condition: float = 1.0  # 1.0 = new, degrades over time
            self._electrode_cap_lot: str = "EC-17"  # Default electrode cap lot
            self._latest_observations: dict[str, StationObservation] = {}
            self._current_observations: dict[str, StationObservation] = {}
            self._estimator = TwinStateEstimator([
                StationDefinition(spec.station_id, spec.sensor_mode, spec.nominal_cycle) for spec in SPECS
            ])
            self._vehicle_sequence = 10_430
            self._event_sequence = 0
            self._last_generation = self._simulation_time - TAKT_SECONDS
            self._last_history_time = self._simulation_time
            self._last_assimilation_time = self._simulation_time - ASSIMILATION_SECONDS
            self._running = True
            self._speed = DEFAULT_SPEED
            self._last_wall = monotonic()
            
            # Phase 4: Reset quality service
            self._quality_service.reset()

            # A warm start represents an already-operating shift, so rolling throughput is derived
            # from actual preceding completions rather than a hard-coded UI value.
            for seconds_ago in range(55, 3_600, 60):
                self._completion_times.append(self._simulation_time - seconds_ago)
            for index, station in enumerate(self._stations):
                vehicle = self._new_vehicle()
                self._start_vehicle(index, vehicle, initial_progress=0.18 + (index % 4) * 0.14)
                self._seed_build_record(vehicle, index)
                station.busy_seconds = self._simulation_time * (0.79 + (index % 3) * 0.03)
                station.vehicles_completed = 17 + index * 2
            for index in (0, 3, 6):
                vehicle = self._new_vehicle()
                vehicle.current_index = index
                vehicle.next_index = index
                vehicle.status = VehicleStatus.BUFFERED
                connection = self._incoming_connection(index)
                if connection and connection.buffer_id:
                    self._buffers[connection.buffer_id].append(vehicle.vehicle_id)
                    vehicle.buffer_id = connection.buffer_id
                    vehicle.queue_kind = "ACCUMULATION_BUFFER"
                else:
                    self._stations[index].queue.append(vehicle.vehicle_id)
                    vehicle.queue_kind = "SHORT_QUEUE"
            # A small, real normal-production cohort remains as the reference
            # population for later enrichment calculations.  It is created from
            # the same vehicle digital threads, before any scenario is active.
            self._quality_baseline_threads = {
                vehicle.vehicle_id: VehicleThread(
                    vehicle_id=vehicle.vehicle_id, variant=vehicle.variant, body_color=vehicle.body_color,
                    batch_id=vehicle.batch_id,
                    current_station=SPECS[vehicle.current_index].station_id if vehicle.current_index is not None else None,
                    line_progress=min(1.0, len(vehicle.build_steps) / len(SPECS)),
                    total_line_time=round(self._simulation_time - vehicle.entry_time, 1),
                    completed_steps=list(vehicle.build_steps),
                )
                for vehicle in self._vehicles.values() if vehicle.build_steps
            }
            initial_observations = self._observation_snapshot()
            self._latest_observations = {observation.station_id: observation for observation in initial_observations}
            self._current_observations = dict(self._latest_observations)
            # Warm shift samples originate in the observation layer, giving every
            # station its own healthy starting fingerprint without estimator access
            # to private runtime state.
            warm_observations: list[StationObservation] = []
            for sample in range(8):
                for index, observation in enumerate(initial_observations):
                    variation = ((sample * 3 + index * 2) % 5 - 2) * 0.006
                    warm_observations.append(observation.model_copy(update={
                        "timestamp": round(self._simulation_time - (8 - sample) * 62, 1),
                        "completed_cycle_time": round(SPECS[index].nominal_cycle * (1 + variation), 2),
                        "last_departure_timestamp": round(self._simulation_time - (8 - sample) * 62, 1),
                    }))
            self._estimator.bootstrap(warm_observations, self._simulation_time)
            self._estimator.assimilate(initial_observations, self._simulation_time)
            self._last_assimilation_time = self._simulation_time
            # Give the warm production line its genuine, low-risk Quality Twin
            # immediately.  These use only seeded past process records and the
            # same feature/model pipeline as live production.
            for vehicle in self._vehicles.values():
                if vehicle.build_steps and vehicle.current_index is not None:
                    self._update_vehicle_quality_prediction(vehicle, vehicle.current_index)
            self._add_event("INFO", "System", "LineLens simulation initialized in normal operating state")
            self._record_history(force=True)

    def pause(self) -> None:
        with self._lock:
            self._running = False
            self._add_event("NOTICE", "System", "Simulation paused")

    def resume(self) -> None:
        with self._lock:
            self._running = True
            self._last_wall = monotonic()
            self._add_event("NOTICE", "System", "Simulation resumed")

    def set_speed(self, speed: float) -> None:
        if speed not in {1.0, 5.0, 8.0, 10.0}:
            raise ValueError("Speed must be one of 1, 5, 8, or 10")
        with self._lock:
            self._speed = speed
            self._add_event("INFO", "System", f"Simulation speed set to {speed:g}×")

    def advance_demo(self, seconds: float) -> None:
        """Advance synthetic plant time quickly through the real simulation pipeline."""
        if not 0 < seconds <= 2400:
            raise ValueError("Demo advance must be between 0 and 2400 simulated seconds")
        with self._lock:
            remaining = float(seconds)
            while remaining > 0:
                step = min(10.0, remaining)
                self._advance(step)
                remaining -= step
            self._last_wall = monotonic()
            self._add_event("INFO", "Demo", f"Synthetic demonstration advanced {seconds:g} simulated seconds")

    def _new_vehicle(self) -> VehicleRuntime:
        self._vehicle_sequence += 1
        variant, color, factor = VARIANTS[(self._vehicle_sequence - 10_431) % len(VARIANTS)]
        vehicle = VehicleRuntime(
            vehicle_id=f"VH-{self._vehicle_sequence}",
            variant=variant,
            body_color=color,
            factor=factor,
            batch_id=f"B{73 + ((self._vehicle_sequence - 10_431) % 5)}",
            entry_time=self._simulation_time,
        )
        self._vehicles[vehicle.vehicle_id] = vehicle
        return vehicle

    def _cycle_for(self, station_index: int, vehicle: VehicleRuntime) -> float:
        factor = vehicle.factor
        if vehicle.variant == "SUV" and station_index in {6, 7, 8}:
            factor += 0.025
        if vehicle.variant == "EV" and station_index in {7, 9}:
            factor += 0.03
        micro_variation = 1 + (((int(vehicle.vehicle_id[-2:]) + station_index * 3) % 5) - 2) * 0.006
        physical_drift = 0.0
        
        # Chassis fixture drift scenario (existing)
        if self._active_scenario == "CHASSIS_FIXTURE_ALIGNMENT_DRIFT" and station_index == 7 and self._scenario_started is not None:
            elapsed = max(0.0, self._simulation_time - self._scenario_started)
            drift_progress = min(1.0, elapsed / 360.0)
            physical_drift = 16.0 * drift_progress
            physical_drift += (((int(vehicle.vehicle_id[-2:]) % 3) - 1) * 0.7 * drift_progress)
        
        # Phase 4: Weld process drift scenario
        if self._weld_drift_active and station_index == 1 and self._weld_drift_started is not None:  # BIW-02 Robotic Weld
            elapsed = max(0.0, self._simulation_time - self._weld_drift_started)
            drift_progress = min(1.0, elapsed / 420.0)  # 7-minute drift progression
            
            # Weld gun condition degrades over time
            self._weld_gun_condition = max(0.7, 1.0 - drift_progress * 0.25)
            
            # Process variance increases with drift
            weld_variance = drift_progress * 3.5  # Up to 3.5s additional variance
            physical_drift += weld_variance * (((int(vehicle.vehicle_id[-2:]) % 4) - 1.5) * 0.5)
            
            # Some cycles get extended
            if ((int(vehicle.vehicle_id[-2:]) + int(elapsed / 60)) % 5) == 0:
                physical_drift += 2.0 * drift_progress  # Occasional cycle extensions
        
        return round(self._stations[station_index].spec.nominal_cycle * factor * micro_variation + physical_drift, 1)

    def set_chassis_drift(self, active: bool) -> None:
        with self._lock:
            if active and self._active_scenario is None:
                self._active_scenario = "CHASSIS_FIXTURE_ALIGNMENT_DRIFT"
                self._scenario_started = self._simulation_time
                self._add_event("NOTICE", "Chassis Marriage", "Physical scenario started: fixture alignment delay")
            elif not active and self._active_scenario is not None:
                self._active_scenario = None
                self._scenario_started = None
                self._add_event("INFO", "Chassis Marriage", "Physical fixture alignment drift cleared")
    
    def set_weld_drift(self, active: bool) -> None:
        """Phase 4: Control weld process drift scenario."""
        with self._lock:
            if active and not self._weld_drift_active:
                self._weld_drift_active = True
                self._weld_drift_started = self._simulation_time
                self._weld_gun_condition = 1.0
                self._add_event("NOTICE", "Robotic Weld Cell", "Physical scenario started: weld gun electrode cap wear (WG-04, EC-17)")
            elif not active and self._weld_drift_active:
                self._weld_drift_active = False
                self._weld_drift_started = None
                self._weld_gun_condition = 1.0
                self._add_event("INFO", "Robotic Weld Cell", "Weld process drift cleared")

    def _incoming_connection(self, station_index: int) -> ConnectionSpec | None:
        return next((connection for connection in CONNECTIONS if connection.downstream_index == station_index), None)

    def _outgoing_connection(self, station_index: int) -> ConnectionSpec | None:
        return next((connection for connection in CONNECTIONS if connection.upstream_index == station_index), None)

    def _incoming_queue(self, station_index: int) -> deque[str]:
        connection = self._incoming_connection(station_index)
        if connection and connection.buffer_id:
            return self._buffers[connection.buffer_id]
        return self._stations[station_index].queue

    def _incoming_capacity(self, station_index: int) -> int:
        connection = self._incoming_connection(station_index)
        return connection.capacity if connection else self._stations[station_index].spec.incoming_queue_capacity

    def _start_vehicle(self, station_index: int, vehicle: VehicleRuntime, initial_progress: float = 0.0) -> None:
        station = self._stations[station_index]
        cycle = self._cycle_for(station_index, vehicle)
        station.current_vehicle = vehicle.vehicle_id
        station.current_cycle = cycle
        station.elapsed = min(cycle * initial_progress, cycle)
        station.operational_state = OperationalState.RUNNING
        station.blocked_since = None
        vehicle.current_index = station_index
        vehicle.next_index = station_index + 1 if station_index + 1 < len(self._stations) else None
        vehicle.status = VehicleStatus.PROCESSING
        vehicle.process_elapsed = station.elapsed
        vehicle.active_cycle = cycle
        vehicle.active_process_entry = self._simulation_time - station.elapsed
        vehicle.buffer_id = None
        vehicle.queue_kind = None

    def _advance(self, delta: float) -> None:
        if delta <= 0:
            return
        self._simulation_time += delta
        self._complete_transfers()
        self._ensure_entry_buffer()
        for index, station in enumerate(self._stations):
            if station.current_vehicle is not None:
                station.elapsed += delta
                station.busy_seconds += delta
                vehicle = self._vehicles[station.current_vehicle]
                vehicle.process_elapsed = station.elapsed
                if station.elapsed >= station.current_cycle:
                    self._finish_or_block(index)
            self._start_available(index)
        self._update_station_states()
        self._assimilate_observations()
        self._record_history()

    def _finish_or_block(self, station_index: int) -> None:
        station = self._stations[station_index]
        vehicle_id = station.current_vehicle
        if vehicle_id is None:
            return
        vehicle = self._vehicles[vehicle_id]
        next_index = station_index + 1
        if next_index >= len(self._stations):
            self._complete_process_record(vehicle, station, station_index)
            
            # Phase 4: Record EOL inspection result
            self._record_eol_inspection(vehicle, station_index)
            
            station.current_vehicle = None
            station.elapsed = 0.0
            station.current_cycle = 0.0
            station.vehicles_completed += 1
            self._completion_times.append(self._simulation_time)
            vehicle.status = VehicleStatus.COMPLETED
            vehicle.current_index = station_index
            vehicle.next_index = None
            self._add_event("INFO", station.spec.name, f"{vehicle.vehicle_id} completed End-of-Line Inspection")
            self._archive_vehicle_thread(vehicle)
            del self._vehicles[vehicle_id]
            return
        downstream = self._stations[next_index]
        if len(self._incoming_queue(next_index)) >= self._incoming_capacity(next_index):
            station.operational_state = OperationalState.BLOCKED
            station.blocked_since = station.blocked_since or self._simulation_time
            return
        station.current_vehicle = None
        self._complete_process_record(vehicle, station, station_index)
        station.elapsed = 0.0
        station.current_cycle = 0.0
        station.vehicles_completed += 1
        station.blocked_since = None
        station.last_completed_cycle = vehicle.active_cycle
        station.last_departure_time = self._simulation_time
        vehicle.status = VehicleStatus.TRANSFERRING
        vehicle.current_index = station_index
        vehicle.next_index = next_index
        vehicle.transfer_started = self._simulation_time
        vehicle.transfer_ends = self._simulation_time + TRANSFER_SECONDS
        self._transfers[vehicle_id] = vehicle
        self._add_event("INFO", station.spec.name, f"{vehicle.vehicle_id} transferred toward {downstream.spec.name}")

    def _process_context(self, station_index: int, vehicle: VehicleRuntime) -> tuple[str, dict[str, str | float | bool]]:
        station_id = SPECS[station_index].station_id
        vehicle_number = int(vehicle.vehicle_id.rsplit("-", 1)[-1])
        # Normal production deliberately rotates genuine genealogy fields.  The
        # drift scenario has a specific, observable WG-04 / EC-17 signature.
        weld_gun = "WG-04" if self._weld_drift_active else ("WG-04", "WG-05", "WG-06")[vehicle_number % 3]
        cap_lot = "EC-17" if self._weld_drift_active else ("EC-17", "EC-18", "EC-19")[vehicle_number % 3]
        robot_cell = "RW-CELL-02" if weld_gun == "WG-04" else "RW-CELL-03"
        equipment, metadata = {
            "BIW-01": ("BF-FIX-04", {"fixture": "BF-FIX-04"}),
            "BIW-02": (weld_gun, {
                "robot_cell": robot_cell,
                "weld_gun": weld_gun,
                "electrode_cap_lot": cap_lot,
                "weld_program": "SPOT-A17"
            }),
            "BIW-03": ("UB-JIG-03", {"joining_fixture": "UB-JIG-03"}),
            "PAINT-01": ("PT-TUNNEL-01", {"chemical_program": "PRETREAT-A"}),
            "PAINT-02": ("PB-ROBOT-02", {"paint_batch": vehicle.batch_id, "spray_program": "BASE-COAT"}),
            "PAINT-03": ("OVEN-03", {"oven_recipe": "CURE-58"}),
            "FA-01": ("TRIM-RIG-01", {"trim_kit": f"TK-{vehicle.variant.upper()}"}),
            "FA-02": ("CM-FIX-07", {"fixture": "CM-FIX-07", "marriage_program": "PT-INTEGRATE"}),
            "FA-03": ("TORQUE-04", {"torque_tool": "TORQUE-04", "target_torque_nm": 112.0}),
            "FA-04": ("ADAS-RIG-02", {"calibration_rig": "ADAS-RIG-02"}),
            "FA-05": ("EOL-TEST-01", {"test_bench": "EOL-TEST-01"}),
        }[station_id]
        return equipment, metadata

    def _seed_build_record(self, vehicle: VehicleRuntime, current_index: int) -> None:
        """Create retained MES-style history for vehicles already on the warm line."""
        seeded: list[ProcessStep] = []
        cursor = vehicle.active_process_entry if vehicle.active_process_entry is not None else self._simulation_time
        for index in reversed(range(current_index)):
            equipment_id, metadata = self._process_context(index, vehicle)
            cycle = self._cycle_for(index, vehicle)
            exit_time = cursor - TRANSFER_SECONDS
            entry_time = exit_time - cycle
            seeded.append(ProcessStep(
                station_id=SPECS[index].station_id, station_name=SPECS[index].name,
                entry_time=round(entry_time, 1), exit_time=round(exit_time, 1), cycle_time=cycle,
                result="PASS", equipment_id=equipment_id, metadata=metadata,
            ))
            cursor = entry_time
        vehicle.build_steps.extend(reversed(seeded))
        if vehicle.build_steps:
            vehicle.entry_time = vehicle.build_steps[0].entry_time

    def _complete_process_record(self, vehicle: VehicleRuntime, station: StationRuntime, station_index: int) -> None:
        equipment_id, metadata = self._process_context(station_index, vehicle)
        entry_time = vehicle.active_process_entry if vehicle.active_process_entry is not None else self._simulation_time - vehicle.active_cycle
        
        # Phase 4: Update latent quality based on process conditions
        self._update_latent_quality(vehicle, station_index, station)
        twin = self._estimator.station_estimate(station.spec.station_id, self._simulation_time)
        metadata.update({
            "twin_expected_cycle": round(twin.expected_cycle, 2),
            "twin_confidence": round(twin.confidence, 3),
            "twin_residual": round(vehicle.active_cycle - twin.expected_cycle, 2),
        })
        if station_index == 1:
            drift_progress = 0.0
            if self._weld_drift_active and self._weld_drift_started is not None:
                drift_progress = min(1.0, max(0.0, self._simulation_time - self._weld_drift_started) / 420.0)
            vehicle_number = int(vehicle.vehicle_id.rsplit("-", 1)[-1])
            noise = ((vehicle_number % 5) - 2) * 0.008
            metadata.update({
                "weld_telemetry_available": station.spec.station_id not in self._telemetry_dropouts,
                "weld_energy_deviation": round(noise + drift_progress * 0.16, 3),
                "weld_variance_multiplier": round(0.65 + drift_progress * 1.45 + abs(noise) * 3, 3),
            })
        
        vehicle.build_steps.append(ProcessStep(
            station_id=station.spec.station_id, station_name=station.spec.name, entry_time=round(entry_time, 1),
            exit_time=round(self._simulation_time, 1), cycle_time=round(vehicle.active_cycle, 1), result="PASS",
            equipment_id=equipment_id, metadata=metadata,
        ))
        vehicle.active_process_entry = None
        
        # A forecast must exist before EOL; never create its first forecast from
        # End-of-Line inspection completion.
        if station_index < len(SPECS) - 1:
            self._update_vehicle_quality_prediction(vehicle, station_index)

    def _update_latent_quality(self, vehicle: VehicleRuntime, station_index: int, station: StationRuntime) -> None:
        """Phase 4: Update latent quality state based on process conditions (hidden from predictor)."""
        
        # Base quality starts at 1.0 (perfect)
        quality_impact = 0.0
        
        # Weld process quality impact
        if station_index == 1 and self._weld_drift_active:  # BIW-02 Robotic Weld
            if self._weld_drift_started is not None:
                elapsed = max(0.0, self._simulation_time - self._weld_drift_started)
                drift_progress = min(1.0, elapsed / 420.0)
                
                # Quality degrades based on weld gun condition and process variance
                quality_impact += drift_progress * 0.15 * (1.0 - self._weld_gun_condition)
                
                # Random quality failures based on drift severity
                vehicle_hash = int(vehicle.vehicle_id[-2:]) + station_index * 7
                # Ground truth is generated only in the physical simulator.  A
                # growing probability makes the 8× demo produce validated EOL
                # outcomes without ever exposing this label to the predictor.
                failure_probability = min(0.76, 0.05 + drift_progress * 0.70)
                if (vehicle_hash % 100) / 100.0 < failure_probability:
                    vehicle.latent_defect = True
        
        # Cycle time anomalies also affect quality
        expected_cycle = self._stations[station_index].spec.nominal_cycle * vehicle.factor
        cycle_deviation = abs(vehicle.active_cycle - expected_cycle) / max(expected_cycle, 1.0)
        if cycle_deviation > 0.08:  # >8% cycle deviation
            quality_impact += cycle_deviation * 0.1
        
        # Update latent quality score
        vehicle.latent_quality_score = max(0.0, vehicle.latent_quality_score - quality_impact)
        
        # Determine defect status if quality degrades enough
        if vehicle.latent_quality_score < 0.75 and not vehicle.latent_defect:
            # Small probability of defect based on quality degradation
            import random
            # Use deterministic seeding for reproducibility
            random.seed(int(vehicle.vehicle_id[-2:]) + int(self._simulation_time))
            if random.random() < (0.75 - vehicle.latent_quality_score) * 0.3:
                vehicle.latent_defect = True
    
    def _update_vehicle_quality_prediction(self, vehicle: VehicleRuntime, station_index: int) -> None:
        """Phase 4: Update quality prediction using digital thread (no latent truth)."""
        
        # Only update if vehicle has completed some steps
        if not vehicle.build_steps:
            return
        
        # Get current station ID
        current_station_id = SPECS[station_index].station_id if station_index < len(SPECS) else None
        if current_station_id is None:
            return
        
        # Build vehicle thread for prediction
        current_station = SPECS[station_index].station_id if station_index < len(SPECS) else None
        progress = min(1.0, (len(vehicle.build_steps) + (0.5 if vehicle.status is VehicleStatus.PROCESSING else 0.0)) / len(SPECS))
        
        from .models import VehicleThread
        vehicle_thread = VehicleThread(
            vehicle_id=vehicle.vehicle_id,
            variant=vehicle.variant,
            body_color=vehicle.body_color,
            batch_id=vehicle.batch_id,
            current_station=current_station,
            line_progress=round(progress, 3),
            total_line_time=round(self._simulation_time - vehicle.entry_time, 1),
            completed_steps=list(vehicle.build_steps),
        )
        
        # Get station observations and twins
        station_observations = self._current_observations
        station_twins = {spec.station_id: self._estimator.station_estimate(spec.station_id, self._simulation_time) for spec in SPECS}
        
        # Predictor boundary: only past, observable vehicle-thread evidence enters.
        previous = self._quality_service.get_vehicle_quality(vehicle.vehicle_id)
        previous_risk = float(previous["current_prediction"]["risk"]) if previous and previous["current_prediction"] else 0.0
        prediction = self._quality_service.update_vehicle_quality(
            vehicle_thread,
            current_station_id,
            self._simulation_time,
            station_observations,
            station_twins,
        )
        if prediction and prediction.risk >= 0.35 and previous_risk < 0.35:
            self._add_event(
                "NOTICE", "Vehicle Quality Twin",
                f"QUALITY WATCH · {vehicle.vehicle_id} reached {prediction.risk:.0%} after {current_station_id}",
            )
        if prediction and prediction.risk >= 0.60 and previous_risk < 0.60:
            self._add_event(
                "WARNING", "Vehicle Quality Twin",
                f"{vehicle.vehicle_id} crossed inspection threshold ({prediction.risk:.0%}); "
                f"review at {prediction.recommended_inspection_point or 'End-of-Line Inspection'}",
            )
        vehicle.quality_prediction_updated = True
    
    def _record_eol_inspection(self, vehicle: VehicleRuntime, station_index: int) -> None:
        """Phase 4: Record EOL inspection result with ground truth revelation."""
        
        # Determine inspection outcome based on latent defect truth
        passed = not vehicle.latent_defect
        
        # Determine defect family if failed
        defect_family = None
        if not passed:
            # Based on process evidence, attribute to weld/integrity issues
            if vehicle.latent_quality_score < 0.8:
                defect_family = DefectFamily.BODY_WELD
            else:
                defect_family = DefectFamily.BODY_WELD  # Default for Phase 4
        
        # Record inspection result
        self._quality_service.record_inspection_result(
            vehicle_id=vehicle.vehicle_id,
            inspection_time=self._simulation_time,
            inspection_station=SPECS[station_index].station_id,
            passed=passed,
            defect_family=defect_family.value if defect_family else None,
        )
        
        # Log inspection event
        if passed:
            self._add_event("INFO", "End-of-Line Inspection", f"{vehicle.vehicle_id} passed final quality inspection")
            self._add_event("INFO", "Vehicle Quality Twin", f"EOL RESULT · {vehicle.vehicle_id} PASS")
        else:
            self._add_event("WARNING", "End-of-Line Inspection", f"{vehicle.vehicle_id} failed inspection - {defect_family.value if defect_family else 'Unknown defect'}")
            self._add_event("WARNING", "Vehicle Quality Twin", f"EOL RESULT · {vehicle.vehicle_id} CONFIRMED QUALITY ISSUE")

    def _archive_vehicle_thread(self, vehicle: VehicleRuntime) -> None:
        self._vehicle_threads[vehicle.vehicle_id] = VehicleThread(
            vehicle_id=vehicle.vehicle_id, variant=vehicle.variant, body_color=vehicle.body_color, batch_id=vehicle.batch_id,
            current_station=None, line_progress=1.0, total_line_time=round(self._simulation_time - vehicle.entry_time, 1),
            completed_steps=list(vehicle.build_steps),
        )
        while len(self._vehicle_threads) > MAX_VEHICLE_THREADS:
            self._vehicle_threads.popitem(last=False)

    def _complete_transfers(self) -> None:
        for vehicle_id, vehicle in list(self._transfers.items()):
            if self._simulation_time < vehicle.transfer_ends:
                continue
            if vehicle.next_index is None:
                del self._transfers[vehicle_id]
                continue
            target = self._stations[vehicle.next_index]
            incoming = self._incoming_queue(vehicle.next_index)
            connection = self._incoming_connection(vehicle.next_index)
            if len(incoming) >= self._incoming_capacity(vehicle.next_index):
                continue
            incoming.append(vehicle_id)
            vehicle.current_index = vehicle.next_index
            vehicle.status = VehicleStatus.BUFFERED
            vehicle.process_elapsed = 0.0
            if connection and connection.buffer_id:
                vehicle.buffer_id = connection.buffer_id
                vehicle.queue_kind = "ACCUMULATION_BUFFER"
                self._add_event("INFO", connection.buffer_name or target.spec.name, f"{vehicle.vehicle_id} entered {connection.buffer_name}")
            else:
                vehicle.buffer_id = None
                vehicle.queue_kind = "SHORT_QUEUE"
                self._add_event("INFO", target.spec.name, f"{vehicle.vehicle_id} queued for {target.spec.name}")
            del self._transfers[vehicle_id]

    def _ensure_entry_buffer(self) -> None:
        first = self._stations[0]
        # Keep the rendered work-in-process set compact and legible while allowing
        # every station to remain populated in the accelerated normal-flow demo.
        if (
            len(self._vehicles) >= 15
            or len(first.queue) >= first.spec.incoming_queue_capacity
            or self._simulation_time - self._last_generation < TAKT_SECONDS * 0.78
        ):
            return
        vehicle = self._new_vehicle()
        vehicle.current_index = 0
        vehicle.next_index = 0
        vehicle.status = VehicleStatus.BUFFERED
        vehicle.queue_kind = "SHORT_QUEUE"
        first.queue.append(vehicle.vehicle_id)
        self._last_generation = self._simulation_time
        self._add_event("INFO", "Line entry", f"{vehicle.vehicle_id} entered the Body Shop")

    def _start_available(self, station_index: int) -> None:
        station = self._stations[station_index]
        incoming = self._incoming_queue(station_index)
        if station.current_vehicle is not None or not incoming:
            return
        vehicle_id = incoming.popleft()
        self._start_vehicle(station_index, self._vehicles[vehicle_id])
        self._add_event("INFO", station.spec.name, f"{vehicle_id} started {station.spec.process.lower()}")

    def _update_station_states(self) -> None:
        for index, station in enumerate(self._stations):
            if station.current_vehicle is not None:
                if station.operational_state is not OperationalState.BLOCKED:
                    station.operational_state = OperationalState.RUNNING
            elif self._incoming_queue(index):
                station.operational_state = OperationalState.IDLE
            elif index == 0:
                station.operational_state = OperationalState.IDLE
            else:
                station.operational_state = OperationalState.STARVED

    def _add_event(self, severity: str, source: str, message: str) -> None:
        self._event_sequence += 1
        self._events.appendleft(OperationalEvent(
            event_id=f"EV-{self._event_sequence:05d}", simulation_time=round(self._simulation_time, 1), severity=severity, source=source, message=message,
        ))

    def _throughput(self) -> float:
        window_start = self._simulation_time - 3_600
        return round(sum(time >= window_start for time in self._completion_times), 1)

    def _section_utilization(self, section: Section) -> float:
        relevant = [station for station in self._stations if station.spec.section is section]
        denominator = max(self._simulation_time, 1.0)
        return round(sum(station.busy_seconds / denominator for station in relevant) / len(relevant) * 100, 1)

    def _plant_telemetry(self, index: int) -> tuple[float | None, float | None, float | None, float | None, str | None]:
        """Synthetic plant signals.  They become observations only when a station has them."""
        phase = self._simulation_time / 42 + index * 0.61
        
        # Phase 4: Weld-specific telemetry during drift scenario
        if index == 1 and self._weld_drift_active:  # BIW-02 Robotic Weld
            if self._weld_drift_started is not None:
                elapsed = max(0.0, self._simulation_time - self._weld_drift_started)
                drift_progress = min(1.0, elapsed / 420.0)
                
                # Power becomes less consistent during drift
                base_power = 48 + sin(phase * 0.8) * 2.7
                power_variation = (drift_progress * 4.0) * sin(phase * 2.3)
                power = round(base_power + power_variation, 1)
                
                # Vibration increases with weld gun degradation
                base_vibration = 1.35 + abs(sin(phase * 1.7)) * 0.42
                vibration_increase = drift_progress * 0.8
                vibration = round(base_vibration + vibration_increase, 2)
                
                temperature = round(39 + sin(phase) * 1.2, 1)
                torque = None
                calibration = None
                return temperature, vibration, power, torque, calibration
        
        # Standard telemetry for other stations
        temperature = round(39 + sin(phase) * 1.2, 1) if index in {1, 4, 5} else None
        vibration = round(1.35 + abs(sin(phase * 1.7)) * 0.42, 2) if index in {0, 1, 2, 7, 8} else None
        power = round(48 + sin(phase * 0.8) * 2.7, 1) if index in {1, 7} else None
        torque = round(112 + sin(phase) * 3.6, 1) if index == 8 else None
        calibration = "Calibrating" if index == 9 and self._stations[index].current_vehicle else "Ready" if index == 9 else None
        return temperature, vibration, power, torque, calibration

    def _observation_snapshot(self) -> list[StationObservation]:
        observations: list[StationObservation] = []
        for index, station in enumerate(self._stations):
            spec = station.spec
            if spec.station_id in self._telemetry_dropouts:
                continue
            temperature, vibration, power, torque, calibration = self._plant_telemetry(index)
            noise = self._telemetry_noise.get(spec.station_id, 0.28 if spec.sensor_mode is SensorMode.FULL else 0.0)
            # A fixed repeatable sequence makes the filter demonstration reproducible
            # while the amplitude remains controlled by the explicit test slider.
            noise_slot = int(self._simulation_time / ASSIMILATION_SECONDS) + index * 3
            jitter = NOISE_PATTERN[noise_slot % len(NOISE_PATTERN)] * noise
            source = "Synthetic PLC + tool telemetry" if spec.sensor_mode is SensorMode.FULL else "Synthetic PLC + MES events" if spec.sensor_mode is SensorMode.LIMITED else "Synthetic PLC / conveyor events"
            common = dict(
                station_id=spec.station_id, timestamp=round(self._simulation_time, 1), operational_state=station.operational_state,
                completed_cycle_time=station.last_completed_cycle,
                last_departure_timestamp=station.last_departure_time, source=source,
            )
            incoming = self._incoming_queue(index)
            if spec.sensor_mode is SensorMode.FULL:
                observations.append(StationObservation(
                    **common, vehicle_id=station.current_vehicle, queue_level=len(incoming),
                    entry_timestamp=round(self._vehicles[station.current_vehicle].active_process_entry, 1) if station.current_vehicle and self._vehicles[station.current_vehicle].active_process_entry is not None else None,
                    cycle_time=round((station.current_cycle or spec.nominal_cycle) + jitter, 2) if station.current_vehicle else None,
                    cycle_progress=round(min(1.0, station.elapsed / station.current_cycle), 3) if station.current_cycle else 0.0,
                    conveyor_occupied=bool(incoming), temperature=temperature, vibration=vibration, power=power, torque=torque,
                    calibration_status=calibration, quality=max(0.56, round(0.96 - noise * 0.055, 3)), signals=["PLC state", "cycle timestamp", "vehicle identity", "tool telemetry"],
                ))
            elif spec.sensor_mode is SensorMode.LIMITED:
                observations.append(StationObservation(
                    **common, queue_level=len(incoming), cycle_time=None, cycle_progress=None,
                    entry_timestamp=round(station.current_vehicle and self._vehicles[station.current_vehicle].active_process_entry or 0, 1) or None,
                    conveyor_occupied=bool(incoming), temperature=temperature if index == 5 else None,
                    vibration=vibration if index == 2 else None, power=None, torque=None, calibration_status=None,
                    quality=0.86, signals=["PLC state", "entry / exit timestamps", "conveyor occupancy"],
                ))
            else:
                observations.append(StationObservation(
                    **common, queue_level=1 if incoming else 0, cycle_time=None, cycle_progress=None,
                    entry_timestamp=round(station.current_vehicle and self._vehicles[station.current_vehicle].active_process_entry or 0, 1) or None,
                    conveyor_occupied=bool(incoming or station.current_vehicle), temperature=None, vibration=None, power=None, torque=None,
                    calibration_status=None, quality=0.73, signals=["basic PLC state", "arrival / departure events", "conveyor occupancy"],
                ))
        return observations

    def _assimilate_observations(self, force: bool = False) -> None:
        if not force and self._simulation_time - self._last_assimilation_time < ASSIMILATION_SECONDS:
            return
        observations = self._observation_snapshot()
        self._latest_observations.update({observation.station_id: observation for observation in observations})
        self._current_observations = {observation.station_id: observation for observation in observations}
        self._estimator.assimilate(observations, self._simulation_time)
        self._last_assimilation_time = self._simulation_time

    def set_observation_condition(self, station_id: str, *, drop: bool | None = None, noise: float | None = None) -> None:
        if station_id not in {spec.station_id for spec in SPECS}:
            raise ValueError("Station not found")
        if drop is not None:
            if drop:
                self._telemetry_dropouts.add(station_id)
            else:
                self._telemetry_dropouts.discard(station_id)
        if noise is not None:
            if not 0 <= noise <= 8:
                raise ValueError("Noise must be between 0 and 8 seconds")
            self._telemetry_noise[station_id] = noise
        self._assimilate_observations(force=True)

    def _record_history(self, force: bool = False) -> None:
        if not force and self._simulation_time - self._last_history_time < 12:
            return
        self._last_history_time = self._simulation_time
        active_cycles = [station.current_cycle for station in self._stations if station.current_cycle]
        self._history.append(HistoryPoint(
            simulation_time=round(self._simulation_time, 1), throughput_per_hour=self._throughput(),
            avg_cycle_time=round(sum(active_cycles) / len(active_cycles), 1) if active_cycles else 0,
            body_utilization=self._section_utilization(Section.BODY_SHOP), paint_utilization=self._section_utilization(Section.PAINT_SHOP), final_utilization=self._section_utilization(Section.FINAL_ASSEMBLY),
        ))

    def _vehicle_model(self, vehicle: VehicleRuntime) -> Vehicle:
        current_station = SPECS[vehicle.current_index].station_id if vehicle.current_index is not None else None
        next_station = SPECS[vehicle.next_index].station_id if vehicle.next_index is not None else None
        progress = 0.0
        if vehicle.status is VehicleStatus.PROCESSING and vehicle.active_cycle:
            progress = min(1.0, vehicle.process_elapsed / vehicle.active_cycle)
        elif vehicle.status is VehicleStatus.TRANSFERRING:
            progress = min(1.0, max(0.0, (self._simulation_time - vehicle.transfer_started) / TRANSFER_SECONDS))
        stage = "Body" if (vehicle.current_index or 0) <= 2 else "Paint" if (vehicle.current_index or 0) <= 5 else "Final Assembly"
        
        # Phase 4: Get quality information
        quality_record = self._quality_service.get_vehicle_quality(vehicle.vehicle_id)
        current_quality_prediction = quality_record["current_prediction"] if quality_record else None
        quality_risk = float(current_quality_prediction["risk"]) if current_quality_prediction else 0.0
        quality_level_str = current_quality_prediction["quality_level"] if current_quality_prediction else "LOW"
        try:
            quality_level = QualityLevel(quality_level_str)
        except ValueError:
            quality_level = QualityLevel.LOW
        
        return Vehicle(
            vehicle_id=vehicle.vehicle_id, variant=vehicle.variant, body_color=vehicle.body_color, batch_id=vehicle.batch_id,
            current_station=current_station, next_station=next_station, production_stage=stage, progress=round(progress, 3), entry_time=round(vehicle.entry_time, 1),
            time_in_station=round(vehicle.process_elapsed, 1), total_line_time=round(self._simulation_time - vehicle.entry_time, 1), status=vehicle.status,
            buffer_id=vehicle.buffer_id, queue_kind=vehicle.queue_kind,
            quality_risk=quality_risk, quality_level=quality_level,
        )

    def _station_model(self, index: int, station: StationRuntime) -> Station:
        observation = self._current_observations.get(station.spec.station_id)
        last_observation = observation or self._latest_observations.get(station.spec.station_id)
        twin = self._estimator.station_estimate(station.spec.station_id, self._simulation_time)
        # During a feed gap the Twin retains the last observed PLC state; it does not
        # substitute the simulator's current hidden operational state.
        observed_state = last_observation.operational_state if last_observation and last_observation.operational_state else OperationalState.IDLE
        health = Health.HEALTHY
        if observed_state in {OperationalState.BLOCKED, OperationalState.STARVED, OperationalState.WARNING}:
            health = Health.WARNING
        if observed_state in {OperationalState.OFFLINE}:
            health = Health.CRITICAL
        progress = observation.cycle_progress if observation and observation.cycle_progress is not None else 0.0
        timing_evidence = observation or last_observation
        if timing_evidence and timing_evidence.entry_timestamp is not None and observed_state is OperationalState.RUNNING:
            progress = min(0.99, max(0.0, (self._simulation_time - timing_evidence.entry_timestamp) / max(twin.estimated_cycle, 1)))
        connection = self._incoming_connection(index)
        buffer_queue = self._buffers[connection.buffer_id] if connection and connection.buffer_id else None
        short_queue_level = len(station.queue)
        buffer_level = len(buffer_queue) if buffer_queue is not None else 0
        utilization = min(0.99, max(0.0, twin.baseline.expected_utilization + (0.04 if observed_state is OperationalState.RUNNING else -0.08)))
        return Station(
            id=station.spec.station_id, name=station.spec.name, section=station.spec.section, process=station.spec.process, operational_state=observed_state,
            cycle_time=twin.estimated_cycle, nominal_cycle_time=station.spec.nominal_cycle, takt_time=TAKT_SECONDS, cycle_progress=round(progress, 3),
            buffer_capacity=connection.capacity if connection and connection.buffer_id else 0,
            buffer_level=buffer_level, queue_length=short_queue_level,
            transfer_mode=connection.mode if connection else "LINE_ENTRY",
            buffer_name=connection.buffer_name if connection else None,
            current_vehicle=observation.vehicle_id if observation else None,
            vehicles_completed=station.vehicles_completed, utilization=round(utilization, 3), health=health, sensor_mode=station.spec.sensor_mode,
            temperature=observation.temperature if observation else None, vibration=observation.vibration if observation else None,
            power=observation.power if observation else None, torque=observation.torque if observation else None,
            calibration_status=observation.calibration_status if observation else None, last_updated=datetime.now(UTC).isoformat(), observation=observation, twin=twin,
        )

    def state(self) -> TwinState:
        with self._lock:
            stations = [self._station_model(index, station) for index, station in enumerate(self._stations)]
            visible = sorted(self._vehicles.values(), key=lambda vehicle: vehicle.vehicle_id)
            running = sum(station.operational_state is OperationalState.RUNNING for station in stations)
            avg_utilization = round(sum(station.utilization for station in stations) / len(stations) * 100, 1)
            return TwinState(
                timestamp=datetime.now(UTC).isoformat(), throughput_per_hour=self._throughput(), stations=stations,
                vehicles=[self._vehicle_model(vehicle) for vehicle in visible],
                buffers=[
                    AccumulationBuffer(
                        id=connection.buffer_id, name=connection.buffer_name or connection.buffer_id,
                        upstream_station=SPECS[connection.upstream_index].station_id,
                        downstream_station=SPECS[connection.downstream_index].station_id,
                        capacity=connection.capacity, level=len(self._buffers[connection.buffer_id]),
                        vehicle_ids=list(self._buffers[connection.buffer_id]),
                    )
                    for connection in CONNECTIONS if connection.buffer_id is not None
                ],
                events=list(self._events), history=list(self._history),
                synchronization=self._estimator.synchronization(self._simulation_time),
                simulation=SimulationInfo(simulation_time=round(self._simulation_time, 1), shift_elapsed=round(self._simulation_time, 1), takt_time=TAKT_SECONDS, speed=self._speed, is_running=self._running,
                    vehicles_in_process=len(visible), stations_running=running, completed_vehicles=sum(station.vehicles_completed for station in self._stations), avg_utilization=avg_utilization,
                    active_scenario=self._active_scenario, quality_scenario_active=self._weld_drift_active),
            )

    def stations(self) -> list[Station]:
        return self.state().stations

    def station(self, station_id: str) -> Station | None:
        return next((station for station in self.stations() if station.id == station_id), None)

    def vehicles(self) -> list[Vehicle]:
        return self.state().vehicles

    def events(self) -> list[OperationalEvent]:
        return self.state().events

    def history(self) -> list[HistoryPoint]:
        return self.state().history

    def observations(self) -> list[StationObservation]:
        with self._lock:
            return [self._current_observations[spec.station_id] for spec in SPECS if spec.station_id in self._current_observations]

    def synchronization(self):
        with self._lock:
            return self._estimator.synchronization(self._simulation_time)

    def quality_vehicles(self, threshold: float = 0.60) -> list[dict]:
        with self._lock:
            return self._quality_service.get_high_risk_vehicles(threshold)

    def quality_monitored_vehicles(self) -> list[dict]:
        with self._lock:
            rows = self._quality_service.get_monitored_vehicles()
            live = {vehicle.vehicle_id: vehicle for vehicle in self._vehicles.values()}
            for row in rows:
                vehicle = live.get(row["vehicle_id"])
                if vehicle is not None:
                    row["variant"] = vehicle.variant
                    row["current_station"] = SPECS[vehicle.current_index].name if vehicle.current_index is not None else "In transfer"
                    row["line_progress"] = round(min(1.0, len(vehicle.build_steps) / len(SPECS)), 3)
                    row["active"] = True
                else:
                    archived = self._vehicle_threads.get(row["vehicle_id"])
                    row["variant"] = archived.variant if archived else "Vehicle"
                    row["current_station"] = "Completed"
                    row["line_progress"] = 1.0
                    row["active"] = False
            return sorted(rows, key=lambda row: (not row["active"], -float(row["risk"]), -float(row["prediction_timestamp"])))

    def quality_scenario(self) -> dict:
        with self._lock:
            elapsed = max(0.0, self._simulation_time - self._weld_drift_started) if self._weld_drift_active and self._weld_drift_started else 0.0
            progress = min(1.0, elapsed / 420.0)
            exposed = sum(
                1 for record in self._quality_service._quality_records.values()
                if record.current_prediction and record.current_prediction.likely_origin_station == "BIW-02"
            ) if self._weld_drift_active else 0
            return {
                "active": self._weld_drift_active,
                "elapsed_seconds": round(elapsed, 1),
                "tool_condition": "Degrading" if self._weld_drift_active else "Nominal",
                "affected_tool": "WG-04",
                "electrode_lot": "EC-17",
                "energy_deviation": round(progress * 0.16, 3),
                "process_variability": round(0.65 + progress * 1.45, 2),
                "vehicles_exposed": exposed,
            }

    def quality_vehicle(self, vehicle_id: str) -> dict | None:
        with self._lock:
            quality = self._quality_service.get_vehicle_quality(vehicle_id)
            if quality is not None:
                thread = self.vehicle_thread(vehicle_id)
                quality["build_record"] = [step.model_dump(mode="json") for step in thread.completed_steps] if thread else []
            return quality

    def quality_genealogy(self) -> dict:
        with self._lock:
            threads = dict(self._vehicle_threads)
            for vehicle in self._vehicles.values():
                current_station = SPECS[vehicle.current_index].station_id if vehicle.current_index is not None else None
                threads[vehicle.vehicle_id] = VehicleThread(
                    vehicle_id=vehicle.vehicle_id, variant=vehicle.variant, body_color=vehicle.body_color,
                    batch_id=vehicle.batch_id, current_station=current_station,
                    line_progress=min(1.0, len(vehicle.build_steps) / len(SPECS)),
                    total_line_time=round(self._simulation_time - vehicle.entry_time, 1),
                    completed_steps=list(vehicle.build_steps),
                )
            return self._quality_service.analyze_genealogy(
                self._simulation_time, threads, self._quality_baseline_threads,
            )

    def quality_metrics(self) -> dict:
        with self._lock:
            return self._quality_service.get_quality_metrics()

    def vehicle_thread(self, vehicle_id: str) -> VehicleThread | None:
        with self._lock:
            archived = self._vehicle_threads.get(vehicle_id)
            if archived is not None:
                return archived
            vehicle = self._vehicles.get(vehicle_id)
            if vehicle is None:
                return None
            current_station = SPECS[vehicle.current_index].station_id if vehicle.current_index is not None else None
            progress = min(1.0, (len(vehicle.build_steps) + (0.5 if vehicle.status is VehicleStatus.PROCESSING else 0.0)) / len(SPECS))
            return VehicleThread(
                vehicle_id=vehicle.vehicle_id, variant=vehicle.variant, body_color=vehicle.body_color, batch_id=vehicle.batch_id,
                current_station=current_station, line_progress=round(progress, 3), total_line_time=round(self._simulation_time - vehicle.entry_time, 1),
                completed_steps=list(vehicle.build_steps),
            )

    def shutdown(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
