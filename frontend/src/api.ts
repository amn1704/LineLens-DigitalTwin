import type {
  GenealogyAnalysis,
  PredictionState,
  QualityMetrics,
  QualityScenario,
  QualityVehicleListItem,
  Incident,
  TwinState,
  VehicleQualityRecord,
  VehicleThread,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok)
    throw new Error(`LineLens API request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export const getState = () => request<TwinState>("/api/state");
export const simulationControl = (action: "reset" | "pause" | "resume") =>
  request<TwinState>(`/api/simulation/${action}`, { method: "POST" });
export const setSimulationSpeed = (speed: number) =>
  request<TwinState>("/api/simulation/speed", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speed }),
  });
export const getVehicleThread = (vehicleId: string) =>
  request<VehicleThread>(`/api/vehicles/${vehicleId}/thread`);
export const setObservationCondition = (
  stationId: string,
  condition: { drop?: boolean; noise?: number },
) =>
  request<TwinState>(
    `/api/twin/testing/stations/${stationId}/observation-condition`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(condition),
    },
  );
export const getPredictions = (stationId: string) =>
  request<PredictionState>(
    `/api/predictions?station_id=${encodeURIComponent(stationId)}`,
  );
export const setChassisDrift = (active: boolean) =>
  request<TwinState>("/api/simulation/scenarios/chassis-fixture-drift", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active }),
  });

export const setWeldDrift = (active: boolean) =>
  request<TwinState>("/api/simulation/scenarios/weld-drift", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active }),
  });

export const advanceDemo = (seconds: number) =>
  request<TwinState>("/api/simulation/demo/advance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seconds }),
  });

export const getQualityVehicles = (threshold = 0.6) =>
  request<Record<string, unknown>[]>(
    `/api/quality/vehicles?threshold=${threshold}`,
  );
export const getQualityMonitoredVehicles = () =>
  request<QualityVehicleListItem[]>("/api/quality/vehicles/all");
export const getQualityScenario = () => request<QualityScenario>("/api/quality/scenario");

export const getQualityVehicle = (vehicleId: string) =>
  request<VehicleQualityRecord>(`/api/quality/vehicles/${vehicleId}`);

export const getQualityGenealogy = () =>
  request<GenealogyAnalysis>("/api/quality/genealogy");

export const getQualityMetrics = () =>
  request<QualityMetrics>("/api/quality/metrics");

export const getIncidents = (status = "active") =>
  request<Incident[]>(`/api/incidents?status=${encodeURIComponent(status)}`);
export const getIncidentHistory = () => request<Incident[]>("/api/incidents/history");
export const incidentAction = (
  incidentId: string,
  action: "acknowledge" | "investigate" | "resolve",
) => request<Incident>(`/api/incidents/${encodeURIComponent(incidentId)}/${action}`, { method: "POST" });
export const addIncidentNote = (incidentId: string, note: string) =>
  request<Incident>(`/api/incidents/${encodeURIComponent(incidentId)}/note`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  });
