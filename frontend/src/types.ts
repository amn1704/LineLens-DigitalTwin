export type Section = "Body Shop" | "Paint Shop" | "Final Assembly";
export type SensorMode =
  "FULL TELEMETRY" | "LIMITED TELEMETRY" | "LEGACY / BASIC SIGNALS";
export type Health = "healthy" | "warning" | "critical";
export type OperationalState =
  | "RUNNING"
  | "IDLE"
  | "BLOCKED"
  | "STARVED"
  | "CHANGEOVER"
  | "WARNING"
  | "OFFLINE";
export type VehicleStatus =
  "PROCESSING" | "BUFFERED" | "TRANSFERRING" | "COMPLETED";

export type DefectFamily =
  | "Body geometry / weld integrity"
  | "Paint surface"
  | "Fastener / torque";

export type InspectionStatus =
  | "PREDICTED"
  | "INSPECTION_PENDING"
  | "CONFIRMED"
  | "CLEARED";

export type QualityLevel = "LOW" | "WATCH" | "INSPECT" | "HIGH";

export interface Vehicle {
  vehicle_id: string;
  variant: string;
  body_color: string;
  batch_id: string;
  current_station: string | null;
  next_station: string | null;
  production_stage: string;
  progress: number;
  entry_time: number;
  time_in_station: number;
  total_line_time: number;
  status: VehicleStatus;
  buffer_id: string | null;
  queue_kind: string | null;
  quality_risk: number;
  quality_level: QualityLevel;
}
export interface StationObservation {
  station_id: string;
  timestamp: number;
  operational_state: OperationalState | null;
  vehicle_id: string | null;
  queue_level: number | null;
  cycle_time: number | null;
  cycle_progress: number | null;
  completed_cycle_time: number | null;
  entry_timestamp: number | null;
  last_departure_timestamp: number | null;
  conveyor_occupied: boolean | null;
  temperature: number | null;
  vibration: number | null;
  power: number | null;
  torque: number | null;
  calibration_status: string | null;
  source: string;
  quality: number;
  signals: string[];
}
export interface StationBaseline {
  expected_cycle: number;
  cycle_stddev: number;
  expected_utilization: number;
  normal_queue: number;
  samples: number;
}
export interface TwinHistoryPoint {
  simulation_time: number;
  observed_cycle: number | null;
  estimated_cycle: number;
  expected_cycle: number;
  residual: number;
  confidence: number;
}
export interface StationTwinEstimate {
  expected_cycle: number;
  estimated_cycle: number;
  estimated_range_low: number;
  estimated_range_high: number;
  observed_cycle: number | null;
  residual: number;
  normalized_deviation: number;
  residual_trend: "STABLE" | "RISING" | "FALLING";
  confidence: number;
  data_age: number;
  source: string;
  evidence: string[];
  estimated_from_indirect_evidence: boolean;
  last_observation: number | null;
  last_assimilation: number;
  baseline: StationBaseline;
  history: TwinHistoryPoint[];
}
export interface Station {
  id: string;
  name: string;
  section: Section;
  process: string;
  operational_state: OperationalState;
  cycle_time: number;
  nominal_cycle_time: number;
  takt_time: number;
  cycle_progress: number;
  buffer_capacity: number;
  buffer_level: number;
  queue_length: number;
  transfer_mode: string;
  buffer_name: string | null;
  current_vehicle: string | null;
  vehicles_completed: number;
  utilization: number;
  health: Health;
  sensor_mode: SensorMode;
  temperature: number | null;
  vibration: number | null;
  power: number | null;
  torque: number | null;
  calibration_status: string | null;
  last_updated: string;
  observation: StationObservation | null;
  twin: StationTwinEstimate | null;
}
export interface ProcessStep {
  station_id: string;
  station_name: string;
  entry_time: number;
  exit_time: number;
  cycle_time: number;
  result: string;
  equipment_id: string;
  metadata: Record<string, string | number | boolean>;
}
export interface VehicleThread {
  vehicle_id: string;
  variant: string;
  body_color: string;
  batch_id: string;
  current_station: string | null;
  line_progress: number;
  total_line_time: number;
  completed_steps: ProcessStep[];
}
export interface TwinSynchronization {
  status: string;
  overall_confidence: number;
  data_coverage: number;
  last_assimilation: number;
  data_age: number;
}
export interface OperationalEvent {
  event_id: string;
  simulation_time: number;
  severity: string;
  source: string;
  message: string;
}
export interface HistoryPoint {
  simulation_time: number;
  throughput_per_hour: number;
  avg_cycle_time: number;
  body_utilization: number;
  paint_utilization: number;
  final_utilization: number;
}
export interface SimulationInfo {
  simulation_time: number;
  shift_elapsed: number;
  takt_time: number;
  speed: number;
  is_running: boolean;
  vehicles_in_process: number;
  stations_running: number;
  completed_vehicles: number;
  avg_utilization: number;
  active_scenario: string | null;
  quality_scenario_active: boolean;
}

export interface BottleneckFeatures {
  cycle_to_takt_ratio: number;
  health_residual: number;
  normalized_residual: number;
  residual_trend: string;
  rolling_cycle_mean: number;
  rolling_cycle_variance: number;
  station_completion_rate: number;
  completion_rate_change: number;
  upstream_queue_growth: number;
  downstream_arrival_rate: number;
  utilization: number;
  blocked_time_ratio: number;
  starved_time_ratio: number;
  accumulator_fill_rate: number;
  evidence_persistence: number;
}
export interface RiskHistoryPoint {
  simulation_time: number;
  risk: number;
  confidence: number;
}
export interface BottleneckAssessment {
  station_id: string;
  station_name: string;
  risk: number;
  confidence: number;
  level: string;
  features: BottleneckFeatures;
  evidence: string[];
  history: RiskHistoryPoint[];
}
export interface TrajectoryPoint {
  offset_seconds: number;
  throughput_per_hour: number;
  completed_vehicles: number;
  wip: number;
  station_queues: Record<string, number>;
  station_states: Record<string, string>;
  accumulator_levels: Record<string, number>;
}
export interface ForecastImpact {
  entity_id: string;
  entity_type: "STATION" | "ACCUMULATION_BUFFER" | "LINE";
  impact_type: string;
  eta_seconds: number;
  eta_range_low: number;
  eta_range_high: number;
  confidence: number;
  current_value: number | string;
  projected_value: number | string;
  severity: string;
}
export interface OutcomeMetrics {
  throughput_per_hour: number;
  throughput_change_percent: number;
  completed_vehicles: number;
  wip: number;
  peak_queue: number;
  blocked_time_seconds: number;
  starved_time_seconds: number;
  accumulator_peak: Record<string, number>;
}
export interface ForwardResult {
  snapshot_time: number;
  source_station_id: string;
  scenario: {
    horizon_seconds: number;
    action: null;
    seed: number;
    assumption: string;
  };
  forecast_confidence: number;
  trajectory: TrajectoryPoint[];
  impacts: ForecastImpact[];
  metrics: OutcomeMetrics;
}
export interface ForecastAlert {
  alert_id: string;
  simulation_time: number;
  severity: string;
  alert_type: "FORECAST";
  source: string;
  message: string;
}
export interface ValidationMetric {
  horizon_seconds: number;
  evaluated: boolean;
  queue_mae: number | null;
  accumulator_mae: number | null;
  throughput_mae: number | null;
  state_accuracy: number | null;
}
export interface ForecastValidation {
  triggered_at: number | null;
  first_actual_impact_at: number | null;
  prediction_lead_time_seconds: number | null;
  impact_eta_error_seconds: number | null;
  metrics: ValidationMetric[];
}
export interface PredictionState {
  generated_at: number;
  label: string;
  primary_station_id: string;
  assessments: BottleneckAssessment[];
  forecasts: Record<string, ForwardResult>;
  alerts: ForecastAlert[];
  validation: ForecastValidation;
}
export interface AccumulationBuffer {
  id: string;
  name: string;
  upstream_station: string;
  downstream_station: string;
  capacity: number;
  level: number;
  vehicle_ids: string[];
}
export interface TwinState {
  timestamp: string;
  throughput_per_hour: number;
  simulation: SimulationInfo;
  stations: Station[];
  vehicles: Vehicle[];
  buffers: AccumulationBuffer[];
  events: OperationalEvent[];
  history: HistoryPoint[];
  synchronization: TwinSynchronization | null;
}

export interface QualityEvidence {
  factor: string;
  value: string;
  contribution: number | null;
}

export interface VehicleQualityPrediction {
  vehicle_id: string;
  prediction_timestamp: number;
  station_at_prediction: string;
  risk: number;
  confidence: number;
  likely_defect_family: DefectFamily | null;
  likely_origin_station: string | null;
  recommended_inspection_point: string | null;
  evidence: QualityEvidence[];
  quality_level: QualityLevel;
  model_version: string;
}

export interface InspectionResult {
  vehicle_id: string;
  inspection_timestamp: number;
  inspection_station: string;
  result: string;
  defect_family: DefectFamily | null;
  inspection_status: InspectionStatus;
}

export interface VehicleQualityRecord {
  vehicle_id: string;
  current_prediction: VehicleQualityPrediction | null;
  prediction_history: VehicleQualityPrediction[];
  inspection_result: InspectionResult | null;
  build_record?: ProcessStep[];
}

export interface CommonFactor {
  factor_type: string;
  factor_id: string;
  factor_name: string;
  support: number;
  cohort_prevalence: number;
  baseline_prevalence: number;
  risk_lift: number;
  confidence: number;
}

export interface GenealogyAnalysis {
  analysis_timestamp: number;
  cohort_definition: string;
  cohort_size: number;
  baseline_size: number;
  common_factors: CommonFactor[];
  likely_origin_process: string | null;
  analysis_confidence: number;
  analysis_note?: string;
}

export interface QualityMetrics {
  total_vehicles: number;
  total_predictions: number;
  defective_vehicles: number;
  defect_rate: number;
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
  precision: number | null;
  recall: number | null;
  false_positive_rate: number | null;
  prediction_lead_time_mean: number | null;
  prediction_lead_time_max: number | null;
  early_interception_opportunity: number | null;
  unnecessary_inspections: number;
  model_version: string;
  validation_state: "AWAITING_EOL_OUTCOMES" | "CONFIRMED_ZERO_FAILURES" | "VALID";
  model_status: { mode: string; source: string; model_version: string };
}
export interface QualityVehicleListItem {
  vehicle_id: string;
  risk: number;
  confidence: number;
  quality_level: QualityLevel;
  station_at_prediction: string;
  current_station: string;
  line_progress: number;
  variant?: string;
  active: boolean;
  likely_defect_family: DefectFamily | null;
  inspection_status: InspectionStatus | "PREDICTED";
  prediction_timestamp: number;
}
export interface QualityScenario {
  active: boolean;
  elapsed_seconds: number;
  tool_condition: string;
  affected_tool: string;
  electrode_lot: string;
  energy_deviation: number;
  process_variability: number;
  vehicles_exposed: number;
}

export type IncidentType = "PRODUCTION" | "QUALITY";
export type IncidentStatus = "NEW" | "ACKNOWLEDGED" | "INVESTIGATING" | "MONITORING" | "RESOLVED";
export interface IncidentTimelineEvent {
  timestamp: number;
  kind: string;
  message: string;
  actor: string;
}
export interface IncidentEvidence {
  label: string;
  value: string;
  baseline: string | null;
  detail: string | null;
}
export interface IncidentAsset {
  asset_id: string;
  name: string;
  area: string;
  role: string;
}
export interface IncidentVehicle {
  vehicle_id: string;
  current_location: string;
  quality_risk: number;
  inspection_status: string;
}
export interface IncidentResponseMetrics {
  detection_lead_time_seconds: number | null;
  acknowledgement_seconds: number | null;
  investigation_seconds: number | null;
  resolution_seconds: number | null;
  vehicles_exposed: number;
}
export interface IncidentOutcome {
  predicted_impact_happened: boolean | null;
  suspected_factor_confirmed: boolean | null;
  process_returned_toward_baseline: boolean | null;
  affected_vehicles_inspected: number;
}
export interface Incident {
  incident_id: string;
  type: IncidentType;
  title: string;
  status: IncidentStatus;
  severity: string;
  detected_at: number;
  updated_at: number;
  source: string;
  confidence: number;
  summary: string;
  expected_impact: string;
  response_window_seconds: number | null;
  affected_assets: IncidentAsset[];
  affected_vehicles: IncidentVehicle[];
  evidence: IncidentEvidence[];
  recommended_checks: string[];
  owner_role: string;
  timeline: IncidentTimelineEvent[];
  outcome: IncidentOutcome;
  response_metrics: IncidentResponseMetrics;
  acknowledged_at: number | null;
  investigating_at: number | null;
  resolved_at: number | null;
  recurrence_of: string | null;
}
