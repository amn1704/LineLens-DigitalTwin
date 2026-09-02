import {
  Activity,
  Bell,
  Box,
  CheckCircle2,
  ChartLine,
  ChevronDown,
  CircleAlert,
  ClipboardCheck,
  Crosshair,
  Expand,
  Footprints,
  FlaskConical,
  Gauge,
  GitBranch,
  LayoutDashboard,
  List,
  Menu,
  LocateFixed,
  Minus,
  Pause,
  Play,
  Plus,
  Route,
  RotateCcw,
  Settings2,
  Shield,
  HelpCircle,
  Timer,
  Users,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  advanceDemo,
  getQualityGenealogy,
  getQualityMetrics,
  getQualityMonitoredVehicles,
  getQualityScenario,
  getQualityVehicle,
  getQualityVehicles,
  addIncidentNote,
  getIncidentHistory,
  getIncidents,
  getState,
  getPredictions,
  getVehicleThread,
  setChassisDrift,
  setObservationCondition,
  setSimulationSpeed,
  setWeldDrift,
  simulationControl,
  incidentAction,
} from "./api";
import { FactoryScene } from "./twin/FactoryScene";
import { GuidedTour } from "./GuidedTour";
import { TOUR_STEPS, hasSeenTour, rememberTour } from "./tour";
import type {
  GenealogyAnalysis,
  HistoryPoint,
  Incident,
  BottleneckAssessment,
  ForecastAlert,
  ForecastValidation,
  ForwardResult,
  OperationalEvent,
  PredictionState,
  QualityMetrics,
  QualityScenario,
  QualityVehicleListItem,
  Station,
  TwinState,
  Vehicle,
  VehicleQualityRecord,
  VehicleThread,
} from "./types";

type Tab = "Dashboard" | "Machines" | "Quality" | "Incidents" | "Analytics" | "Alerts";
type ViewAction = "reset" | "zoom-in" | "zoom-out";
const sections = ["Body Shop", "Paint Shop", "Final Assembly"] as const;
const stateTone = (state: Station["operational_state"]) =>
  state === "RUNNING"
    ? "healthy"
    : state === "BLOCKED" || state === "STARVED" || state === "WARNING"
      ? "warning"
      : state === "OFFLINE"
        ? "critical"
        : "idle";
const clock = (seconds: number) =>
  `${String(Math.floor(seconds / 3600)).padStart(2, "0")}:${String(Math.floor(seconds / 60) % 60).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;

export default function App() {
  const [state, setState] = useState<TwinState | null>(null);
  const [selectedId, setSelectedId] = useState("FA-02");
  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle | null>(null);
  const [vehicleThread, setVehicleThread] = useState<VehicleThread | null>(
    null,
  );
  const [activeTab, setActiveTab] = useState<Tab>("Dashboard");
  const [dataView, setDataView] = useState<"twin" | "observed" | "forecast">(
    "twin",
  );
  const [prediction, setPrediction] = useState<PredictionState | null>(null);
  const [forecastHorizon, setForecastHorizon] = useState(300);
  const [error, setError] = useState<string | null>(null);
  
  // Phase 4: Quality state
  const [qualityVehicles, setQualityVehicles] = useState<QualityVehicleListItem[]>([]);
  const [selectedQualityVehicle, setSelectedQualityVehicle] = useState<QualityVehicleListItem | null>(null);
  const [selectedQualityRecord, setSelectedQualityRecord] = useState<VehicleQualityRecord | null>(null);
  const [genealogy, setGenealogy] = useState<GenealogyAnalysis | null>(null);
  const [qualityMetrics, setQualityMetrics] = useState<QualityMetrics | null>(null);
  const [weldDriftActive, setWeldDriftActive] = useState(false);
  const [qualityScenario, setQualityScenario] = useState<QualityScenario | null>(null);
  const [qualityFilter, setQualityFilter] = useState<"REVIEW" | "WATCH" | "INSPECT" | "ALL">("REVIEW");
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [incidentHistory, setIncidentHistory] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [incidentFilter, setIncidentFilter] = useState<"ACTIVE" | "RESOLVED">("ACTIVE");
  const [moreOpen, setMoreOpen] = useState(false);
  const [demoOpen, setDemoOpen] = useState(false);
  const [validationOpen, setValidationOpen] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const [tourMode, setTourMode] = useState<"welcome" | "active" | "complete" | null>(null);
  const [tourStep, setTourStep] = useState(0);
  const tourWelcomeChecked = useRef(false);
  const tourScenarioRun = useRef(new Set<string>());
  const [view, setView] = useState<{ action: ViewAction; tick: number }>({
    action: "reset",
    tick: 0,
  });
  const [cameraMode, setCameraMode] = useState<"orbit" | "walk" | "tour">(
    "orbit",
  );
  const [observationConditions, setObservationConditions] = useState<
    Record<string, { drop: boolean; noise: number }>
  >({});
  const stageRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!state || tourWelcomeChecked.current) return;
    tourWelcomeChecked.current = true;
    const forceWelcome = new URLSearchParams(window.location.search).get("tour") === "welcome";
    if (forceWelcome || !hasSeenTour(window.localStorage)) setTourMode("welcome");
  }, [state]);

  useEffect(() => {
    if (!validationOpen) return;
    void getQualityMetrics().then(setQualityMetrics).catch(() => undefined);
  }, [validationOpen]);

  useEffect(() => {
    let mounted = true;
    const refresh = async () => {
      try {
        const next = await getState();
        if (mounted) {
          setState(next);
          setError(null);
        }
      } catch {
        if (mounted)
          setError("LineLens is waiting for its local simulation service.");
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 750);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    let mounted = true;
    const refreshPrediction = async () => {
      try {
        const next = await getPredictions(selectedId);
        if (mounted) setPrediction(next);
      } catch {
        if (mounted) setPrediction(null);
      }
    };
    void refreshPrediction();
    const timer = window.setInterval(() => void refreshPrediction(), 1600);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [selectedId]);
  useEffect(() => {
    let mounted = true;
    const refreshIncidents = async () => {
      try {
        const [active, history] = await Promise.all([getIncidents(), getIncidentHistory()]);
        if (!mounted) return;
        setIncidents(active);
        setIncidentHistory(history);
        setSelectedIncident((current) =>
          (current && [...active, ...history].find((item) => item.incident_id === current.incident_id))
          ?? active[0]
          ?? history[0]
          ?? null,
        );
      } catch {
        if (mounted) setIncidents([]);
      }
    };
    void refreshIncidents();
    const timer = window.setInterval(() => void refreshIncidents(), 1800);
    return () => { mounted = false; window.clearInterval(timer); };
  }, []);
  useEffect(() => {
    if (activeTab !== "Dashboard") setCameraMode("orbit");
  }, [activeTab]);
  
  // Phase 4: Fetch quality data when Quality tab is active
  useEffect(() => {
    let mounted = true;
    const refreshQuality = async () => {
      if (activeTab !== "Quality") return;
      try {
        const [vehicles, genealogyData, metrics, scenario] = await Promise.all([
          getQualityMonitoredVehicles(),
          getQualityGenealogy(),
          getQualityMetrics(),
          getQualityScenario(),
        ]);
        if (mounted) {
          setQualityVehicles(vehicles);
          setGenealogy(genealogyData);
          setQualityMetrics(metrics);
          setQualityScenario(scenario);
          setWeldDriftActive(scenario.active);
          setSelectedQualityVehicle((current) =>
            (current && vehicles.find((vehicle) => vehicle.vehicle_id === current.vehicle_id))
            ?? vehicles.find((vehicle) => vehicle.risk >= .35)
            ?? null,
          );
        }
      } catch {
        if (mounted) {
          setQualityVehicles([]);
          setGenealogy(null);
          setQualityMetrics(null);
          setQualityScenario(null);
        }
      }
    };
    void refreshQuality();
    const timer = window.setInterval(() => void refreshQuality(), 2000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [activeTab]);
  
  // Fetch detailed quality record when vehicle selected
  useEffect(() => {
    let mounted = true;
    if (!selectedQualityVehicle) {
      setSelectedQualityRecord(null);
      return () => { mounted = false; };
    }
    const vehicleId = String(selectedQualityVehicle.vehicle_id);
    void getQualityVehicle(vehicleId)
      .then((record) => {
        if (mounted) setSelectedQualityRecord(record);
      })
      .catch(() => {
        if (mounted) setSelectedQualityRecord(null);
      });
    return () => {
      mounted = false;
    };
  }, [selectedQualityVehicle]);
  useEffect(() => {
    let mounted = true;
    if (!selectedVehicle) {
      setVehicleThread(null);
      return () => {
        mounted = false;
      };
    }
    void getVehicleThread(selectedVehicle.vehicle_id)
      .then((thread) => {
        if (mounted) setVehicleThread(thread);
      })
      .catch(() => {
        if (mounted) setVehicleThread(null);
      });
    return () => {
      mounted = false;
    };
  }, [selectedVehicle]);

  const executeDemo = useCallback(async (kind: "bottleneck" | "quality") => {
    setDemoBusy(true);
    try {
      let next = await simulationControl("reset");
      next = await simulationControl("pause");
      setIncidents([]);
      setSelectedIncident(null);
      if (kind === "bottleneck") {
        await setChassisDrift(true);
        next = await advanceDemo(380);
        await getIncidents();
        next = await advanceDemo(20);
        const [forecast, activeIncidents] = await Promise.all([getPredictions("FA-02"), getIncidents()]);
        setPrediction(forecast);
        setIncidents(activeIncidents);
        setSelectedIncident(activeIncidents[0] ?? null);
        setSelectedId("FA-02");
        setActiveTab("Dashboard");
        setDataView("forecast");
        setForecastHorizon(300);
      } else {
        await setWeldDrift(true);
        next = await advanceDemo(1800);
        const [vehicles, genealogyData, metrics, scenario, activeIncidents] = await Promise.all([
          getQualityMonitoredVehicles(), getQualityGenealogy(), getQualityMetrics(), getQualityScenario(), getIncidents(),
        ]);
        setQualityVehicles(vehicles);
        setGenealogy(genealogyData);
        setQualityMetrics(metrics);
        setQualityScenario(scenario);
        setWeldDriftActive(true);
        const meaningful = vehicles.find((vehicle) => vehicle.risk >= .6) ?? vehicles.find((vehicle) => vehicle.line_progress >= .5) ?? vehicles[0] ?? null;
        setSelectedQualityVehicle(meaningful);
        setIncidents(activeIncidents);
        setSelectedIncident(activeIncidents.find((incident) => incident.type === "QUALITY") ?? activeIncidents[0] ?? null);
        setActiveTab("Quality");
      }
      setState(next);
      setDemoOpen(false);
      setError(null);
    } catch {
      setError("The short synthetic demonstration could not be prepared.");
    } finally {
      setDemoBusy(false);
    }
  }, []);

  useEffect(() => {
    if (tourMode !== "active") return;
    const step = TOUR_STEPS[tourStep];
    setActiveTab(step.page);
    if (step.stationId) {
      setSelectedId(step.stationId);
      setSelectedVehicle(null);
    }
    if (tourStep <= 2) setDataView("twin");
    if (tourStep === 3) {
      setDataView("forecast");
      setForecastHorizon(300);
    }
    if (tourStep === 4) setQualityFilter("ALL");
    if (tourStep === 5) setQualityFilter("REVIEW");
    if (step.scenario && !tourScenarioRun.current.has(step.scenario)) {
      tourScenarioRun.current.add(step.scenario);
      void executeDemo(step.scenario);
    }
  }, [executeDemo, tourMode, tourStep]);

  useEffect(() => {
    if (tourMode !== "active" || (tourStep !== 4 && tourStep !== 5) || qualityVehicles.length === 0) return;
    const candidate = tourStep === 5
      ? qualityVehicles.find((vehicle) => vehicle.risk >= .6)
      : qualityVehicles.find((vehicle) => vehicle.line_progress >= .5);
    setSelectedQualityVehicle(candidate ?? qualityVehicles[0]);
  }, [qualityVehicles, tourMode, tourStep]);

  useEffect(() => {
    if (tourMode === "active" && tourStep === 6 && incidents.length) {
      setSelectedIncident(incidents.find((incident) => incident.type === "QUALITY") ?? incidents[0]);
    }
  }, [incidents, tourMode, tourStep]);

  const selected = useMemo(
    () =>
      state?.stations.find((station) => station.id === selectedId) ??
      state?.stations[0],
    [state, selectedId],
  );
  if (!state || !selected)
    return (
      <LoadingState message={error ?? "Loading live automotive production…"} />
    );
  const selectStation = (id: string) => {
    setSelectedId(id);
    setSelectedVehicle(null);
    setActiveTab("Dashboard");
  };
  const control = async (action: "reset" | "pause" | "resume") => {
    try {
      setState(await simulationControl(action));
      setError(null);
      if (action === "reset") {
        setSelectedVehicle(null);
        setSelectedQualityVehicle(null);
        setSelectedQualityRecord(null);
        setObservationConditions({});
        setWeldDriftActive(false);
        setPrediction(null);
        setIncidents([]);
        setIncidentHistory([]);
        setSelectedIncident(null);
        setDataView("twin");
      }
    } catch {
      setError("Simulation control request failed.");
    }
  };
  const speed = async (value: number) => {
    try {
      setState(await setSimulationSpeed(value));
      setError(null);
    } catch {
      setError("Unable to change simulation speed.");
    }
  };
  const commandView = (action: ViewAction) =>
    setView((current) => ({ action, tick: current.tick + 1 }));
  const toggleFullscreen = async () => {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await stageRef.current?.requestFullscreen();
  };
  const testCondition = async (
    stationId: string,
    condition: { drop?: boolean; noise?: number },
  ) => {
    try {
      setObservationConditions((current) => ({
        ...current,
        [stationId]: {
          drop: condition.drop ?? current[stationId]?.drop ?? false,
          noise: condition.noise ?? current[stationId]?.noise ?? 0,
        },
      }));
      setState(await setObservationCondition(stationId, condition));
      setError(null);
    } catch {
      setError("Observation condition update failed.");
    }
  };
  const toggleChassisDrift = async () => {
    try {
      setState(
        await setChassisDrift(state.simulation.active_scenario === null),
      );
      setError(null);
    } catch {
      setError("Unable to update the physical drift scenario.");
    }
  };
  
  const toggleWeldDrift = async () => {
    try {
      setState(await setWeldDrift(!weldDriftActive));
      setWeldDriftActive(!weldDriftActive);
      setError(null);
    } catch {
      setError("Unable to update weld process drift scenario.");
    }
  };
  const openIncident = (incident: Incident | null) => {
    if (!incident) return;
    setSelectedIncident(incident);
    setActiveTab("Incidents");
  };
  const updateIncident = async (
    action: "acknowledge" | "investigate" | "resolve",
    incident: Incident,
  ) => {
    try {
      const updated = await incidentAction(incident.incident_id, action);
      setSelectedIncident(updated);
      setIncidents((current) => action === "resolve" ? current.filter((item) => item.incident_id !== updated.incident_id) : current.map((item) => item.incident_id === updated.incident_id ? updated : item));
      if (action === "resolve") setIncidentHistory((current) => [updated, ...current.filter((item) => item.incident_id !== updated.incident_id)]);
    } catch { setError("Incident workflow update failed."); }
  };
  const noteIncident = async (incident: Incident, note: string) => {
    try {
      const updated = await addIncidentNote(incident.incident_id, note);
      setSelectedIncident(updated);
      setIncidents((current) => current.map((item) => item.incident_id === updated.incident_id ? updated : item));
    } catch { setError("Unable to add the incident note."); }
  };
  const beginTour = async () => {
    tourScenarioRun.current.clear();
    setTourStep(0);
    setTourMode("active");
    setActiveTab("Dashboard");
    setSelectedId("FA-02");
    setDataView("twin");
    try {
      const healthy = await simulationControl("reset");
      setState(healthy);
      setIncidents([]);
      setSelectedIncident(null);
    } catch { setError("Unable to reset the quick tour demonstration."); }
  };
  const skipTour = () => {
    rememberTour(window.localStorage);
    setTourMode(null);
  };
  const nextTour = () => {
    if (tourStep >= TOUR_STEPS.length - 1) {
      rememberTour(window.localStorage);
      setTourMode("complete");
    } else setTourStep((current) => current + 1);
  };
  const exploreAfterTour = async () => {
    rememberTour(window.localStorage);
    setTourMode(null);
    setActiveTab("Dashboard");
    setDataView("twin");
    try { setState(await simulationControl("reset")); } catch { setError("Unable to reset the demonstration."); }
  };
  const runDemoFromTour = (kind: "bottleneck" | "quality") => {
    rememberTour(window.localStorage);
    setTourMode(null);
    void executeDemo(kind);
  };
  const selectedAssessment =
    prediction?.assessments.find((item) => item.station_id === selected.id) ??
    null;
  const selectedForecast =
    prediction?.forecasts[String(forecastHorizon)] ?? null;
  const forecastPoint = selectedForecast?.trajectory.at(-1) ?? null;

  const fullCount = state.stations.filter(
    (s) => s.sensor_mode === "FULL TELEMETRY",
  ).length;
  const limitedCount = state.stations.filter(
    (s) => s.sensor_mode === "LIMITED TELEMETRY",
  ).length;
  const basicCount = state.stations.filter(
    (s) => s.sensor_mode === "LEGACY / BASIC SIGNALS",
  ).length;
  const freshCount = state.stations.filter(
    (s) => s.twin && s.twin.data_age < 8,
  ).length;
  const inferredCount = state.stations.filter(
    (s) => s.twin?.estimated_from_indirect_evidence,
  ).length;
  const syncTooltip = state.synchronization
    ? `TWIN SYNCHRONIZATION\nOverall state confidence: ${Math.round(state.synchronization.overall_confidence * 100)}%\nFresh observations: ${freshCount} / ${state.stations.length}\nFull telemetry stations: ${fullCount}\nLimited telemetry: ${limitedCount}\nLegacy/basic: ${basicCount}\nEstimated/inferred now: ${inferredCount}\nLast assimilation: ${state.synchronization.data_age.toFixed(1)}s ago`
    : "";

  return (
    <main className="line-lens">
      <header className="app-bar">
        <div className="brand">
          <span className="brand-mark">
            <Crosshair size={18} strokeWidth={2.3} />
          </span>
          <strong>LineLens</strong>
          <span>Automotive Digital Twin</span>
        </div>
        <div className="live-controls">
          <span
            className={
              state.simulation.is_running ? "live-badge" : "paused-badge"
            }
          >
            <i />{" "}
            {state.simulation.is_running
              ? "Simulation live"
              : "Simulation paused"}
          </span>
          {state.synchronization && (
            <span
              className={`twin-sync ${state.synchronization.status === "TWIN SYNCHRONIZED" ? "ready" : ""}`}
              title={syncTooltip}
            >
              <i />{" "}
              {state.synchronization.status === "TWIN SYNCHRONIZED"
                ? "Twin synchronized"
                : "Twin estimating"}{" "}
              <b>
                {Math.round(state.synchronization.overall_confidence * 100)}%
                {" confidence"}
              </b>
            </span>
          )}
          <span
            className="sim-clock"
            title="Simulated factory time. Reset returns to a healthy 20-minute warm start so Twin baselines, throughput, and production history are immediately meaningful."
          >
            <Timer size={13} /> Simulation time{" "}
            {clock(state.simulation.shift_elapsed)}
          </span>
          <button
            title={
              state.simulation.is_running
                ? "Pause simulation"
                : "Resume simulation"
            }
            onClick={() =>
              void control(state.simulation.is_running ? "pause" : "resume")
            }
          >
            {state.simulation.is_running ? (
              <Pause size={14} />
            ) : (
              <Play size={14} />
            )}
          </button>
          {(state.simulation.active_scenario || state.simulation.quality_scenario_active) && <span className="demo-active-badge">Demo active · {state.simulation.quality_scenario_active ? "Weld quality issue" : "Bottleneck"}</span>}
          <button className="header-action" onClick={() => setTourMode("welcome")}><HelpCircle size={14}/> Tour</button>
          <button className="header-action" onClick={() => setDemoOpen(true)}><FlaskConical size={14}/> Demo</button>
        </div>
      </header>
      <nav className="primary-nav">
        <NavTab
          active={activeTab === "Dashboard"}
          label="Dashboard"
          icon={<LayoutDashboard size={15} />}
          onClick={() => setActiveTab("Dashboard")}
        />
        <NavTab
          active={activeTab === "Quality"}
          label="Quality"
          icon={<Shield size={15} />}
          onClick={() => setActiveTab("Quality")}
        />
        <NavTab
          active={activeTab === "Incidents"}
          label="Incidents"
          icon={<CircleAlert size={15} />}
          onClick={() => setActiveTab("Incidents")}
        />
        <div className="more-nav">
          <button className={["Machines","Analytics","Alerts"].includes(activeTab) ? "active" : ""} onClick={() => setMoreOpen((open) => !open)}><Menu size={15}/> More <ChevronDown size={13}/></button>
          {moreOpen && <div className="more-menu">
            <button onClick={() => { setActiveTab("Machines"); setMoreOpen(false); }}><List size={14}/> Machines</button>
            <button onClick={() => { setActiveTab("Analytics"); setMoreOpen(false); }}><ChartLine size={14}/> Analytics</button>
            <button onClick={() => { setActiveTab("Alerts"); setMoreOpen(false); }}><Bell size={14}/> Alerts</button>
            <button onClick={() => { setValidationOpen(true); setMoreOpen(false); }}><CheckCircle2 size={14}/> About / Validation</button>
          </div>}
        </div>
      </nav>
      {error && <div className="service-notice">{error}</div>}
      {activeTab === "Dashboard" && (
        <section className="dashboard-layout">
          <StationList
            stations={state.stations}
            events={state.events}
            selectedId={selected.id}
            onSelect={selectStation}
            dataView={dataView}
            prediction={prediction}
          />
          <section ref={stageRef} data-tour="factory-canvas" className={`twin-stage camera-${cameraMode}`}>
            <div className="scene-meta">
              <span className={dataView === "forecast" ? "forecast-label" : ""}>
                {dataView === "forecast"
                  ? "Forecast view"
                  : cameraMode === "orbit"
                    ? "Orbit view"
                    : cameraMode === "walk"
                      ? "Walk mode"
                      : "Factory tour"}
              </span>
              <small>
                {dataView === "forecast"
                  ? `+${forecastHorizon / 60} min · No intervention · simulation-derived`
                  : cameraMode === "walk"
                    ? "Click scene · WASD move · Shift faster · Esc exit"
                    : cameraMode === "tour"
                      ? "Automatic 25 second process tour · Esc cancels"
                      : `Drag to orbit · Scroll to zoom · ${state.simulation.speed}× twin data`}
              </small>
              <div data-tour="forecast-control" className="data-view-switch">
                <button
                  className={dataView === "observed" ? "active" : ""}
                  title="Direct production data received from the factory."
                  onClick={() => setDataView("observed")}
                >
                  Observed
                </button>
                <button
                  className={dataView === "twin" ? "active" : ""}
                  title="LineLens's best estimate of what is happening now."
                  onClick={() => setDataView("twin")}
                >
                  Twin
                </button>
                <button
                  className={dataView === "forecast" ? "active forecast" : ""}
                  title="What LineLens expects may happen next."
                  onClick={() => setDataView("forecast")}
                >
                  Forecast
                </button>
              </div>
              {dataView === "forecast" && (
                <div className="forecast-timeline">
                  {[0, 120, 300, 600].map((seconds) => (
                    <button
                      key={seconds}
                      className={
                        seconds > 0 && forecastHorizon === seconds
                          ? "active"
                          : ""
                      }
                      onClick={() => {
                        if (seconds === 0) setDataView("twin");
                        else setForecastHorizon(seconds);
                      }}
                    >
                      {seconds === 0 ? "NOW" : `+${seconds / 60}m`}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="scene-tools">
              <button
                aria-label="Reset view"
                title="Reset view"
                onClick={() => {
                  setCameraMode("orbit");
                  commandView("reset");
                }}
              >
                <RotateCcw size={15} />
              </button>
              <button
                aria-label="Zoom in"
                title="Zoom in"
                onClick={() => commandView("zoom-in")}
              >
                <Plus size={16} />
              </button>
              <button
                aria-label="Zoom out"
                title="Zoom out"
                onClick={() => commandView("zoom-out")}
              >
                <Minus size={16} />
              </button>
              <span className="tool-divider" />
              <button
                className={cameraMode === "walk" ? "active" : ""}
                aria-label={
                  cameraMode === "walk" ? "Exit walk mode" : "Enter walk mode"
                }
                title={cameraMode === "walk" ? "Exit walk mode" : "Walk mode"}
                onClick={() =>
                  setCameraMode(cameraMode === "walk" ? "orbit" : "walk")
                }
              >
                {cameraMode === "walk" ? (
                  <X size={15} />
                ) : (
                  <Footprints size={15} />
                )}
              </button>
              <button
                className={cameraMode === "tour" ? "active" : ""}
                aria-label="Factory tour"
                title="Factory tour"
                onClick={() =>
                  setCameraMode(cameraMode === "tour" ? "orbit" : "tour")
                }
              >
                <Route size={15} />
              </button>
              <button
                aria-label="Toggle fullscreen"
                title="Fullscreen"
                onClick={() => void toggleFullscreen()}
              >
                <Expand size={15} />
              </button>
            </div>
            {incidents.slice(0, 1).map((incident) => (
              <button key={incident.incident_id} data-tour="incident-summary" className="dashboard-quality-summary" onClick={() => openIncident(incident)}>
                <ClipboardCheck size={15} />
                <span><b>{incident.type === "QUALITY" ? "Quality watch" : "Early warning"}</b>{incident.summary} · View incident</span>
              </button>
            ))}
            <FactoryScene
              stations={state.stations}
              vehicles={state.vehicles}
              selectedId={selected.id}
              onSelect={selectStation}
              onSelectVehicle={setSelectedVehicle}
              viewAction={view.action}
              viewTick={view.tick}
              cameraMode={cameraMode}
              onCameraModeChange={setCameraMode}
              forecastPoint={dataView === "forecast" ? forecastPoint : null}
              forecastImpacts={
                dataView === "forecast" ? (selectedForecast?.impacts ?? []) : []
              }
              currentQueues={Object.fromEntries(
                state.stations.map((station) => [
                  station.id,
                  station.buffer_capacity
                    ? station.buffer_level
                    : station.queue_length,
                ]),
              )}
              qualityScenarioActive={state.simulation.quality_scenario_active}
            />
            <div className="asset-overlay">
              {selectedVehicle ? (
                <VehicleOverlay
                  vehicle={selectedVehicle}
                  thread={vehicleThread}
                />
              ) : (
                <StationOverlay
                  station={selected}
                  dataView={dataView}
                  assessment={selectedAssessment}
                  forecast={selectedForecast}
                />
              )}
            </div>
          </section>
          <RightPanel
            state={state}
            selected={selected}
            dataView={dataView}
            vehicle={selectedVehicle}
            vehicleThread={vehicleThread}
            onTestCondition={testCondition}
            testCondition={
              observationConditions[selected.id] ?? { drop: false, noise: 0 }
            }
            assessment={selectedAssessment}
            forecast={selectedForecast}
            onToggleDrift={toggleChassisDrift}
            incident={incidents.find((item) => item.affected_assets.some((asset) => asset.asset_id === selected.id)) ?? null}
            vehicleIncident={selectedVehicle ? incidents.find((item) => item.affected_vehicles.some((vehicle) => vehicle.vehicle_id === selectedVehicle.vehicle_id)) ?? null : null}
            onOpenIncident={openIncident}
          />
        </section>
      )}
      {activeTab === "Machines" && (
        <MachinesView
          stations={state.stations}
          dataView={dataView}
          onSelect={selectStation}
        />
      )}
      {activeTab === "Analytics" && (
        <AnalyticsView
          history={state.history}
          station={selected}
          stations={state.stations}
          onSelect={setSelectedId}
          assessment={selectedAssessment}
          forecast={selectedForecast}
        />
      )}
      {activeTab === "Incidents" && (
        <IncidentsView
          incidents={incidentFilter === "ACTIVE" ? incidents : incidentHistory}
          selectedIncident={selectedIncident}
          filter={incidentFilter}
          onFilter={setIncidentFilter}
          onSelect={setSelectedIncident}
          onAction={updateIncident}
          onNote={noteIncident}
        />
      )}
      {activeTab === "Alerts" && (
        <EventsView
          events={state.events}
          forecastAlerts={prediction?.alerts ?? []}
          validation={prediction?.validation ?? null}
        />
      )}
      {activeTab === "Quality" && (
        <SimplifiedQualityView
          qualityVehicles={qualityVehicles}
          selectedVehicle={selectedQualityVehicle}
          onSelectVehicle={setSelectedQualityVehicle}
          qualityRecord={selectedQualityRecord}
          genealogy={genealogy}
          metrics={qualityMetrics}
          scenario={qualityScenario}
          filter={qualityFilter}
          onFilter={setQualityFilter}
          incident={selectedQualityVehicle ? incidents.find((item) => item.affected_vehicles.some((vehicle) => vehicle.vehicle_id === selectedQualityVehicle.vehicle_id)) ?? null : null}
          onOpenIncident={openIncident}
        />
      )}
      {demoOpen && <DemoDrawer busy={demoBusy} activeScenario={state.simulation.active_scenario !== null} qualityActive={state.simulation.quality_scenario_active} speed={state.simulation.speed} onClose={() => setDemoOpen(false)} onRun={(kind) => void executeDemo(kind)} onSensorLoss={() => { setDemoOpen(false); setActiveTab("Dashboard"); setSelectedId("FA-01"); void testCondition("FA-01", { drop: true }); }} onReset={() => { setDemoOpen(false); void control("reset"); }} onSpeed={speed} />}
      {validationOpen && <ValidationDrawer state={state} quality={qualityMetrics} prediction={prediction} onClose={() => setValidationOpen(false)} />}
      <GuidedTour mode={tourMode} step={tourStep} busy={demoBusy} onStart={() => void beginTour()} onBack={() => setTourStep((current) => Math.max(0, current - 1))} onNext={nextTour} onSkip={skipTour} onExplore={() => void exploreAfterTour()} onDemo={runDemoFromTour} />
    </main>
  );
}

function DemoDrawer({ busy, activeScenario, qualityActive, speed, onClose, onRun, onSensorLoss, onReset, onSpeed }: {
  busy: boolean;
  activeScenario: boolean;
  qualityActive: boolean;
  speed: number;
  onClose: () => void;
  onRun: (kind: "bottleneck" | "quality") => void;
  onSensorLoss: () => void;
  onReset: () => void;
  onSpeed: (speed: number) => void;
}) {
  return <div className="drawer-backdrop" onClick={onClose}><aside className="app-drawer" onClick={(event) => event.stopPropagation()}><header><div><span>Synthetic demonstration</span><h2>Demo scenarios</h2></div><button aria-label="Close demo" onClick={onClose}><X size={17}/></button></header><p>These controls change only the local factory simulation. They never represent production commands.</p><div className="demo-options"><button disabled={busy} onClick={() => onRun("bottleneck")}><CircleAlert size={18}/><span><b>Bottleneck</b><small>Run a short Chassis Marriage slowdown through the real prediction pipeline.</small></span></button><button disabled={busy} onClick={() => onRun("quality")}><Shield size={18}/><span><b>Weld quality issue</b><small>Create a real risky-vehicle cohort and common weld pattern.</small></span></button><button disabled={busy} onClick={onSensorLoss}><Activity size={18}/><span><b>Sensor loss</b><small>Show how LineLens estimates Trim Station with limited direct data.</small></span></button></div><section><span>Simulation speed</span><div className="drawer-speed">{[1,5,8,10].map((value) => <button key={value} className={speed === value ? "active" : ""} onClick={() => onSpeed(value)}>{value}×</button>)}</div></section>{(activeScenario || qualityActive) && <div className="demo-running"><i/> Demo currently active</div>}<button className="reset-demo" disabled={busy} onClick={onReset}><RotateCcw size={14}/> Reset demo</button>{busy && <div className="drawer-busy"><span className="spinner"/>Running the real factory simulation…</div>}</aside></div>;
}

function ValidationDrawer({ state, quality, prediction, onClose }: { state: TwinState; quality: QualityMetrics | null; prediction: PredictionState | null; onClose: () => void }) {
  const full = state.stations.filter((station) => station.sensor_mode === "FULL TELEMETRY").length;
  const partial = state.stations.filter((station) => station.sensor_mode === "LIMITED TELEMETRY").length;
  const basic = state.stations.filter((station) => station.sensor_mode === "LEGACY / BASIC SIGNALS").length;
  const checked = quality ? quality.true_positives + quality.false_positives : 0;
  const correct = quality?.precision === null || quality?.precision === undefined ? "Awaiting outcomes" : `${Math.round(quality.precision * 100)}%`;
  return <div className="drawer-backdrop" onClick={onClose}><aside className="app-drawer validation-drawer" onClick={(event) => event.stopPropagation()}><header><div><span>About LineLens</span><h2>Validation</h2></div><button aria-label="Close validation" onClick={onClose}><X size={17}/></button></header><p>Predictions are checked against what happens later in the synthetic factory.</p><div className="validation-simple"><Operation label="Warnings checked" value={checked.toString()}/><Operation label="Correct warnings" value={correct}/><Operation label="Average time gained" value={quality?.prediction_lead_time_mean == null ? "Awaiting outcomes" : `${(quality.prediction_lead_time_mean / 60).toFixed(1)} min`}/><Operation label="Vehicles flagged before EOL" value={quality?.true_positives?.toString() ?? "0"}/></div><section className="coverage-simple"><span>Factory data coverage</span><div><b>{full}</b><small>Direct data</small></div><div><b>{partial}</b><small>Partial data</small></div><div><b>{basic}</b><small>Basic data</small></div><p>LineLens can estimate all {state.stations.length} station states.</p></section><details className="app-details"><summary>Technical validation details <ChevronDown size={14}/></summary><div className="validation-technical"><small>Quality model: {quality?.model_version ?? "Loading"}</small><small>Predictions: {quality?.total_predictions ?? 0}</small><small>Precision: {quality?.precision == null ? "—" : `${(quality.precision * 100).toFixed(1)}%`}</small><small>Recall: {quality?.recall == null ? "—" : `${(quality.recall * 100).toFixed(1)}%`}</small><small>Forecast checks: {prediction?.validation.metrics.filter((metric) => metric.evaluated).length ?? 0} horizons evaluated</small></div></details></aside></div>;
}

function LoadingState({ message }: { message: string }) {
  return (
    <main className="loading-shell">
      <Crosshair size={28} />
      <p>{message}</p>
    </main>
  );
}
function NavTab({
  active,
  label,
  icon,
  onClick,
}: {
  active: boolean;
  label: string;
  icon: ReactNode;
  onClick: () => void;
}) {
  return (
    <button className={active ? "active" : ""} onClick={onClick}>
      {icon}
      {label}
    </button>
  );
}
function StationOverlay({
  station,
  dataView,
  assessment,
  forecast,
}: {
  station: Station;
  dataView: "twin" | "observed" | "forecast";
  assessment: BottleneckAssessment | null;
  forecast: ForwardResult | null;
}) {
  const twin = station.twin;
  const observation = station.observation;
  if (dataView === "observed")
    return (
      <>
        <div>
          <span>{observation ? "OBSERVED FEED" : "FEED UNAVAILABLE"}</span>
          <strong>{station.name}</strong>
        </div>
        <Metric
          label="Observed cycle"
          value={
            observation?.cycle_time !== null &&
            observation?.cycle_time !== undefined
              ? `${observation.cycle_time.toFixed(1)}s`
              : "— · no direct signal"
          }
        />
        <Metric
          label="Evidence"
          value={
            observation?.cycle_time !== null &&
            observation?.cycle_time !== undefined
              ? "Direct telemetry"
              : observation
                ? "Indirect timing"
                : "No packets"
          }
        />
        <Metric
          label="Current feed"
          value={observation ? "Available" : "Unavailable"}
        />
        <Metric
          label={
            station.buffer_capacity
              ? (station.buffer_name ?? "Buffer")
              : "Queue"
          }
          value={
            station.buffer_capacity
              ? `${observation?.queue_level ?? "—"}/${station.buffer_capacity}`
              : `${observation?.queue_level ?? "—"}`
          }
        />
      </>
    );
  if (dataView === "forecast") {
    const first = forecast?.impacts[0];
    return (
      <>
        <div>
          <span>NO-ACTION FORECAST</span>
          <strong>{station.name}</strong>
        </div>
        <Metric
          label="Bottleneck risk"
          value={assessment ? `${Math.round(assessment.risk * 100)}%` : "—"}
        />
        <Metric
          label="Forecast confidence"
          value={
            forecast
              ? `${Math.round(forecast.forecast_confidence * 100)}%`
              : "—"
          }
        />
        <Metric
          label="First impact"
          value={
            first
              ? `${first.impact_type.replaceAll("_", " ").toLowerCase()} · ${(first.eta_seconds / 60).toFixed(1)}m`
              : "No material impact"
          }
        />
        <Metric
          label="Projected output"
          value={
            forecast
              ? `${forecast.metrics.throughput_per_hour.toFixed(0)} veh/h`
              : "—"
          }
        />
      </>
    );
  }
  return (
    <>
      <div>
        <span>{station.operational_state}</span>
        <strong>{station.name}</strong>
      </div>
      <Metric
        label="Twin cycle"
        value={`${Math.round(station.cycle_progress * station.cycle_time)} / ${station.cycle_time}s`}
      />
      <Metric
        label="Expected"
        value={`${twin?.expected_cycle.toFixed(1) ?? "—"}s`}
      />
      <Metric
        label="Confidence"
        value={twin ? `${Math.round(twin.confidence * 100)}%` : "—"}
      />
      <Metric
        label={
          station.buffer_capacity ? (station.buffer_name ?? "Buffer") : "Queue"
        }
        value={
          station.buffer_capacity
            ? `${station.buffer_level}/${station.buffer_capacity}`
            : `${station.queue_length}`
        }
      />
    </>
  );
}
function VehicleOverlay({
  vehicle,
  thread,
}: {
  vehicle: Vehicle;
  thread: VehicleThread | null;
}) {
  // Phase 4: Show quality risk if significant
  const showQuality = vehicle.quality_risk >= 0.35;
  
  return (
    <>
      <div>
        <span>{vehicle.variant} · Digital build record</span>
        <strong>{vehicle.vehicle_id}</strong>
      </div>
      {showQuality && (
        <Metric 
          label="Quality risk" 
          value={`${Math.round(vehicle.quality_risk * 100)}%`}
          tone={vehicle.quality_risk >= 0.60 ? "warning" : "info"}
        />
      )}
      <Metric label="Process" value={vehicle.current_station ?? "Transfer"} />
      <Metric label="Line time" value={clock(vehicle.total_line_time)} />
      <Metric
        label="Build steps"
        value={`${thread?.completed_steps.length ?? 0} complete`}
      />
      <Metric
        label="Progress"
        value={
          thread
            ? `${Math.round(thread.line_progress * 100)}%`
            : `${Math.round(vehicle.progress * 100)}%`
        }
      />
    </>
  );
}
function Metric({ label, value, tone }: { label: string; value: string; tone?: "info" | "warning" }) {
  return (
    <div className={tone ? `metric-${tone}` : ""}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function StationList({
  stations,
  events,
  selectedId,
  onSelect,
  dataView,
  prediction,
}: {
  stations: Station[];
  events: OperationalEvent[];
  selectedId: string;
  onSelect: (id: string) => void;
  dataView: "twin" | "observed" | "forecast";
  prediction: PredictionState | null;
}) {
  return (
    <aside className="station-sidebar">
      <div className="sidebar-title">
        <span>Stations</span>
        <b>{stations.length}</b>
      </div>
      <div className="station-scroll">
        {sections.map((section) => (
          <section className="station-group" key={section}>
            <h2>{section}</h2>
            {stations
              .filter((station) => station.section === section)
              .map((station) => (
                <button
                  key={station.id}
                  className={`station-row ${station.id === selectedId ? "selected" : ""}`}
                  onClick={() => onSelect(station.id)}
                >
                  <i className={stateTone(station.operational_state)} />
                  <span>
                    <strong>
                      {station.name}
                      {(prediction?.assessments.find(
                        (item) => item.station_id === station.id,
                      )?.risk ?? 0) >= 0.35 && (
                        <b
                          className="forecast-marker"
                          title="Meaningful future risk"
                        >
                          ◇
                        </b>
                      )}
                    </strong>
                    <small>
                      {station.operational_state === "RUNNING"
                        ? dataView === "twin" || dataView === "forecast"
                          ? `Running · ~${station.cycle_time.toFixed(1)}s est.`
                          : station.observation?.cycle_time !== null &&
                              station.observation?.cycle_time !== undefined
                            ? `Running · ${station.observation.cycle_time.toFixed(1)}s observed`
                            : "Running · indirect timing"
                        : `${station.operational_state} · Queue ${station.queue_length}`}
                    </small>
                  </span>
                </button>
              ))}
          </section>
        ))}
      </div>
      <section className="recent-events">
        <h2>Recent events</h2>
        {events.slice(0, 4).map((event) => (
          <Event key={event.event_id} event={event} />
        ))}
      </section>
    </aside>
  );
}
function Event({ event }: { event: OperationalEvent }) {
  return (
    <div className="event">
      <span>{clock(event.simulation_time).slice(3)}</span>
      <p>
        <b>{event.source}</b> — {event.message}
      </p>
    </div>
  );
}

function IncidentsView({
  incidents,
  selectedIncident,
  filter,
  onFilter,
  onSelect,
  onAction,
  onNote,
}: {
  incidents: Incident[];
  selectedIncident: Incident | null;
  filter: "ACTIVE" | "RESOLVED";
  onFilter: (filter: "ACTIVE" | "RESOLVED") => void;
  onSelect: (incident: Incident) => void;
  onAction: (action: "acknowledge" | "investigate" | "resolve", incident: Incident) => void;
  onNote: (incident: Incident, note: string) => void;
}) {
  const [note, setNote] = useState("");
  const active = selectedIncident && incidents.some((item) => item.incident_id === selectedIncident.incident_id) ? selectedIncident : incidents[0] ?? null;
  const formatTime = (seconds: number | null) => seconds === null ? "—" : seconds < 60 ? `${Math.round(seconds)} sec` : `${(seconds / 60).toFixed(1)} min`;
  return (
    <section className="incidents-layout">
      <aside className="incidents-list">
        <div className="sidebar-title"><div><span>Attention needed</span><small>{filter === "ACTIVE" ? `${incidents.length} active incidents` : `${incidents.length} resolved incidents`}</small></div><b>{incidents.length}</b></div>
        <div className="quality-filters"><button className={filter === "ACTIVE" ? "active" : ""} onClick={() => onFilter("ACTIVE")}>ACTIVE</button><button className={filter === "RESOLVED" ? "active" : ""} onClick={() => onFilter("RESOLVED")}>RESOLVED</button></div>
        <div className="incident-list-scroll">
          {incidents.length === 0 ? <div className="incident-empty"><CheckCircle2 size={26}/><b>{filter === "ACTIVE" ? "No active incidents" : "No resolved incidents yet"}</b><small>{filter === "ACTIVE" ? "LineLens is monitoring production and vehicle quality. Factory operation is within expected conditions." : "Resolved incidents will remain here for this simulation session."}</small></div> : incidents.map((incident) => <button key={incident.incident_id} onClick={() => onSelect(incident)} className={`incident-row ${active?.incident_id === incident.incident_id ? "selected" : ""}`}><i className={incident.severity.toLowerCase()} /><span><b>{incident.title}</b><small>{incident.source} · {incident.status.replaceAll("_", " ")}</small></span><em>{incident.incident_id}</em></button>)}
        </div>
      </aside>
      {active ? <>
        <section data-tour="incident-response" className="incident-detail incident-simple">
          <header className="incident-heading"><div><span>{active.type === "QUALITY" ? "Quality containment" : "Early warning"} · {active.incident_id}</span><h1>{active.title}</h1><small>{active.source} · detected at {clock(active.detected_at)}</small></div><b className={`incident-status ${active.status.toLowerCase()}`}>{active.status}</b></header>
          <section className="incident-section"><span>What happened</span><p>{active.summary}</p></section>
          <section className="incident-section impact"><span>What may happen next</span><p>{active.expected_impact}</p></section>
          <section className="incident-section"><span>Why?</span><div className="incident-evidence">{active.evidence.slice(0,3).map((evidence) => <div key={evidence.label}><small>{evidence.label}</small><b>{evidence.value}</b>{evidence.detail && <em>{evidence.detail}</em>}</div>)}</div></section>
          <section className="incident-section"><span>What should we check?</span><ol className="incident-checks">{active.recommended_checks.slice(0,3).map((check) => <li key={check}>{check}</li>)}</ol>{active.recommended_checks.length > 3 && <details className="app-details"><summary>More playbook checks <ChevronDown size={14}/></summary><ol className="incident-checks">{active.recommended_checks.slice(3).map((check) => <li key={check}>{check}</li>)}</ol></details>}</section>
          <section className="incident-section"><span>Affected stations and vehicles</span><div className="incident-scope">{active.affected_assets.map((asset) => <div key={asset.asset_id}><b>{asset.name}</b><small>{asset.area} · {asset.role}</small></div>)}{active.affected_vehicles.map((vehicle) => <div key={vehicle.vehicle_id}><b>{vehicle.vehicle_id} · {Math.round(vehicle.quality_risk * 100)}%</b><small>{vehicle.current_location} · {vehicle.inspection_status.replaceAll("_", " ")}</small></div>)}</div></section>
          {active.status === "RESOLVED" && <section className="incident-section resolved-summary"><span>Resolved summary</span><div className="incident-evidence"><div><small>Detected</small><b>{clock(active.detected_at)}</b></div><div><small>Acknowledged</small><b>{active.acknowledged_at === null ? "—" : clock(active.acknowledged_at)}</b></div><div><small>Investigation</small><b>{active.investigating_at === null ? "—" : clock(active.investigating_at)}</b></div><div><small>Resolved</small><b>{active.resolved_at === null ? "—" : clock(active.resolved_at)}</b></div><div><small>Prediction lead</small><b>{formatTime(active.response_metrics.detection_lead_time_seconds)}</b></div><div><small>Vehicles exposed</small><b>{active.response_metrics.vehicles_exposed}</b></div></div></section>}
        </section>
        <aside data-tour="incident-response-panel" className="incident-response">
          <section><div className="twin-section-title"><span>Who / when</span></div><b>{active.owner_role}</b><small>{active.response_window_seconds !== null ? `${formatTime(active.response_window_seconds)} remaining before expected downstream impact` : "Review before normal End-of-Line inspection where possible."}</small></section>
          <section className="incident-actions"><div className="twin-section-title"><span>Response tracking</span></div>{active.status === "NEW" && <button onClick={() => onAction("acknowledge", active)}>Acknowledge</button>}{(active.status === "NEW" || active.status === "ACKNOWLEDGED") && <button onClick={() => onAction("investigate", active)}>Start investigation</button>}{active.status !== "RESOLVED" && <button className="quiet" onClick={() => onNote(active, "Recommended check completed.")}>Mark check complete</button>}{active.status !== "RESOLVED" && <div className="incident-note"><input value={note} placeholder="Add response note" onChange={(event) => setNote(event.target.value)} /><button className="quiet" onClick={() => { if (note.trim()) { onNote(active, note); setNote(""); } }}>Add note</button></div>}{active.status !== "RESOLVED" && <button className="resolve" onClick={() => onAction("resolve", active)}>Resolve incident</button>}<small>Workflow tracking only. These buttons do not control machinery.</small></section>
          <details className="app-details incident-technical"><summary>Prediction and response details <ChevronDown size={14}/></summary><section><div className="twin-section-title"><span>Response metrics</span></div><div className="incident-metrics"><Operation label="Detection lead" value={formatTime(active.response_metrics.detection_lead_time_seconds)} /><Operation label="Acknowledged" value={formatTime(active.response_metrics.acknowledgement_seconds)} /><Operation label="Investigation" value={formatTime(active.response_metrics.investigation_seconds)} /><Operation label="Resolution" value={formatTime(active.response_metrics.resolution_seconds)} /><Operation label="Vehicles exposed" value={active.response_metrics.vehicles_exposed.toString()} /></div></section><section className="incident-outcome"><div className="twin-section-title"><span>Predicted vs actual</span></div><small>Predicted impact: {active.outcome.predicted_impact_happened === null ? "awaiting confirmation" : active.outcome.predicted_impact_happened ? "observed" : "not observed"}.</small><small>Inspection finding: {active.outcome.suspected_factor_confirmed === null ? "awaiting engineering confirmation" : active.outcome.suspected_factor_confirmed ? "confirmed" : "not confirmed"}.</small><small>Process recovery: {active.outcome.process_returned_toward_baseline === null ? "not recorded" : active.outcome.process_returned_toward_baseline ? "returned toward normal" : "not yet returned toward normal"}.</small></section></details>
          <section className="incident-timeline"><div className="twin-section-title"><span>Timeline</span></div>{active.timeline.map((entry, index) => <div key={`${entry.timestamp}-${index}`}><time>{clock(entry.timestamp)}</time><span><b>{entry.kind === "USER" ? entry.actor : "LineLens"}</b><small>{entry.message}</small></span></div>)}</section>
        </aside>
      </> : <section className="incident-healthy"><CheckCircle2 size={36}/><span>No active incidents</span><h1>Factory operating within expected conditions.</h1><p>LineLens is monitoring production and vehicle quality.</p></section>}
    </section>
  );
}

function SimplifiedQualityView({ qualityVehicles, selectedVehicle, onSelectVehicle, qualityRecord, genealogy, metrics, scenario, filter, onFilter, incident, onOpenIncident }: {
  qualityVehicles: QualityVehicleListItem[];
  selectedVehicle: QualityVehicleListItem | null;
  onSelectVehicle: (vehicle: QualityVehicleListItem | null) => void;
  qualityRecord: VehicleQualityRecord | null;
  genealogy: GenealogyAnalysis | null;
  metrics: QualityMetrics | null;
  scenario: QualityScenario | null;
  filter: "REVIEW" | "WATCH" | "INSPECT" | "ALL";
  onFilter: (filter: "REVIEW" | "WATCH" | "INSPECT" | "ALL") => void;
  incident: Incident | null;
  onOpenIncident: (incident: Incident | null) => void;
}) {
  const reviewCount = qualityVehicles.filter((vehicle) => vehicle.risk >= .35).length;
  const inspectCount = qualityVehicles.filter((vehicle) => vehicle.risk >= .6).length;
  const filtered = qualityVehicles.filter((vehicle) => filter === "ALL" ? true : filter === "INSPECT" ? vehicle.risk >= .6 : filter === "WATCH" ? vehicle.risk >= .35 && vehicle.risk < .6 : vehicle.risk >= .35);
  const prediction = qualityRecord?.current_prediction;
  const factors = genealogy?.common_factors ?? [];
  const primaryFactor = factors[0];
  const warningsChecked = metrics ? metrics.true_positives + metrics.false_positives : 0;
  return <section className="quality-layout quality-simple">
    <aside data-tour="quality-vehicle-list" className="quality-sidebar">
      <div className="sidebar-title"><div><span>Vehicles to review</span><small>{reviewCount ? `${reviewCount} need attention` : "No urgent quality review"}</small></div><b>{reviewCount}</b></div>
      <div className={`quality-summary-line ${reviewCount ? "attention" : "calm"}`}>{reviewCount ? <CircleAlert size={15}/> : <CheckCircle2 size={15}/>}<span><b>{inspectCount ? `${inspectCount} inspect now` : "Quality looks calm"}</b>{reviewCount ? `${reviewCount - inspectCount} additional vehicles are on watch` : "All monitored vehicles remain below the watch level"}</span></div>
      <div className="quality-filters">{(["REVIEW","INSPECT","WATCH","ALL"] as const).map((item) => <button key={item} className={filter === item ? "active" : ""} onClick={() => onFilter(item)}>{item === "REVIEW" ? "TO REVIEW" : item === "ALL" ? "ALL VEHICLES" : item}</button>)}</div>
      <div className="quality-scroll">{filtered.length === 0 ? <div className="quality-empty"><Shield size={24}/><p>No vehicles need review</p><small>Use All vehicles to inspect the full monitored population.</small></div> : filtered.map((vehicle) => <button key={vehicle.vehicle_id} className={`quality-row ${selectedVehicle?.vehicle_id === vehicle.vehicle_id ? "selected" : ""}`} onClick={() => onSelectVehicle(vehicle)}><div className="quality-risk-indicator" style={{backgroundColor: vehicle.risk >= .6 ? "#e07b35" : vehicle.risk >= .35 ? "#d89a3b" : "#4f85a6"}}/><div className="quality-vehicle-info"><strong>{vehicle.vehicle_id}</strong><small>{vehicle.current_station}</small></div><div className="quality-risk-score"><b>{Math.round(vehicle.risk * 100)}%</b><small>{vehicle.risk >= .6 ? "INSPECT" : vehicle.risk >= .35 ? "WATCH" : "OK"}</small></div></button>)}</div>
    </aside>
    <section className="quality-detail">
      {selectedVehicle && qualityRecord && prediction && (selectedVehicle.risk >= .35 || filter === "ALL") ? <div className="quality-vehicle-detail">
        <header className="quality-simple-heading"><div><span>Vehicle quality</span><h1>{selectedVehicle.vehicle_id}</h1><small>{selectedVehicle.variant || "Vehicle"} · {selectedVehicle.current_station}</small></div><div className={`quality-risk-hero ${prediction.risk >= .6 ? "inspect" : prediction.risk >= .35 ? "watch" : "normal"}`} title="Chance that this vehicle may need extra inspection."><span>Quality risk</span><b>{Math.round(prediction.risk * 100)}%</b><small>{prediction.risk >= .6 ? "Inspect" : prediction.risk >= .35 ? "Watch" : "Within normal range"}</small></div></header>
        <section className="quality-story"><div><span>Why?</span><b>{prediction.risk >= .35 ? "Weld process looked abnormal earlier." : "No unusual production pattern found."}</b><small>{prediction.evidence[0]?.value ?? "Production evidence is within the normal range."}</small></div><div><span>Likely origin</span><b>{prediction.likely_origin_station === "BIW-02" ? "Robotic Weld" : prediction.likely_origin_station ?? "No likely origin"}</b><small>Suspected only until inspection confirms it.</small></div><div className="quality-what-to-do"><span>What to do</span><b>{prediction.risk >= .6 ? "Inspect this vehicle before the next major process." : prediction.risk >= .35 ? "Watch this vehicle through the next process." : "Continue standard inspection."}</b><small>Location: {prediction.recommended_inspection_point ?? "Standard End-of-Line"}<br/>Reason: {prediction.risk >= .35 ? "Earlier weld data looks abnormal." : "No extra inspection signal."}</small></div></section>
        {incident && <button className="incident-context-link" onClick={() => onOpenIncident(incident)}>Part of quality incident · {incident.incident_id}<span>Open incident</span></button>}
        <BuildRecord record={qualityRecord} currentStation={selectedVehicle.current_station}/>
        <details className="app-details technical-quality"><summary>View technical evidence <ChevronDown size={14}/></summary><div className="quality-grid"><Operation label="Confidence" value={`${Math.round(prediction.confidence * 100)}%`}/><Operation label="Inspection point" value={prediction.recommended_inspection_point ?? "Standard EOL"}/><Operation label="Model" value={prediction.model_version}/><Operation label="Predictions retained" value={qualityRecord.prediction_history.length.toString()}/></div><div className="risk-sequence">{qualityRecord.prediction_history.map((item) => <div key={`${item.station_at_prediction}-${item.prediction_timestamp}`} className={item.risk >= .6 ? "inspect" : item.risk >= .35 ? "watch" : "normal"}><i style={{height:`${Math.max(8,item.risk*44)}px`}}/><small>{item.station_at_prediction}</small><b>{Math.round(item.risk*100)}%</b></div>)}</div>{qualityRecord.inspection_result && <div className={`inspection-result ${qualityRecord.inspection_result.result.startsWith("FAIL") ? "failed" : "passed"}`}><span>End-of-Line outcome</span><b>{qualityRecord.inspection_result.result}</b></div>}</details>
      </div> : <div className="quality-empty-detail"><Shield size={32}/><p>{reviewCount ? "Select a vehicle to review" : "No urgent quality review"}</p><small>LineLens is still monitoring every vehicle.</small></div>}
    </section>
    <aside className="quality-right quality-simple-right">
      {scenario?.active && <div className="demo-active-small"><i/>Demo active · Weld quality issue</div>}
      <section data-tour="common-pattern" className="genealogy-panel common-pattern-simple"><div className="twin-section-title"><span>Common pattern</span><b className="inferred-tag">{genealogy?.cohort_size ?? 0} risky</b></div>{primaryFactor ? <><p><b>{primaryFactor.support} of {genealogy?.cohort_size} risky vehicles</b> passed through:</p><h2>{primaryFactor.factor_name}</h2>{factors.length > 1 && <div className="also-common"><span>Also common</span>{factors.slice(1,3).map((factor) => <b key={factor.factor_id}>{factor.factor_name}</b>)}</div>}<details className="app-details"><summary>View analysis <ChevronDown size={14}/></summary>{factors.slice(0,4).map((factor) => <div className="analysis-row" key={factor.factor_id}><b>{factor.factor_name}</b><small>{factor.risk_lift.toFixed(1)}× more common · {factor.support}/{genealogy?.cohort_size ?? factor.support} vehicles · baseline {(factor.baseline_prevalence*100).toFixed(1)}%</small></div>)}<small>Patterns indicate where to investigate; they do not prove cause.</small></details></> : <div className="genealogy-empty"><CheckCircle2 size={17}/><span>No shared problem pattern.<small>LineLens continues comparing tools, cells and component lots.</small></span></div>}</section>
      {metrics && <section className="quality-metrics validation-simple-card"><div className="twin-section-title"><span>How well is LineLens doing?</span></div><div className="validation-primary"><div><small>Warnings checked</small><b>{warningsChecked}</b></div><div><small>Correct warnings</small><b>{metrics.precision == null ? "Awaiting outcomes" : `${Math.round(metrics.precision*100)}%`}</b></div><div><small>Median time gained</small><b>{metrics.prediction_lead_time_mean == null ? "Awaiting outcomes" : `${(metrics.prediction_lead_time_mean/60).toFixed(1)} min`}</b></div></div><details className="app-details"><summary>View technical metrics <ChevronDown size={14}/></summary><div className="metrics-grid"><Operation label="Predictions" value={metrics.total_predictions.toString()}/><Operation label="Defect rate" value={`${(metrics.defect_rate*100).toFixed(1)}%`}/><Operation label="Precision" value={metrics.precision == null ? "—" : `${(metrics.precision*100).toFixed(1)}%`}/><Operation label="Recall" value={metrics.recall == null ? "—" : `${(metrics.recall*100).toFixed(1)}%`}/></div></details></section>}
    </aside>
  </section>;
}

function QualityView({
  qualityVehicles,
  selectedVehicle,
  onSelectVehicle,
  qualityRecord,
  genealogy,
  metrics,
  onToggleWeldDrift,
  weldDriftActive,
  scenario,
  filter,
  onFilter,
  incident,
  onOpenIncident,
}: {
  qualityVehicles: QualityVehicleListItem[];
  selectedVehicle: QualityVehicleListItem | null;
  onSelectVehicle: (vehicle: QualityVehicleListItem | null) => void;
  qualityRecord: VehicleQualityRecord | null;
  genealogy: GenealogyAnalysis | null;
  metrics: QualityMetrics | null;
  onToggleWeldDrift: () => void;
  weldDriftActive: boolean;
  scenario: QualityScenario | null;
  filter: "ALL" | "WATCH" | "INSPECT" | "CONFIRMED";
  onFilter: (filter: "ALL" | "WATCH" | "INSPECT" | "CONFIRMED") => void;
  incident: Incident | null;
  onOpenIncident: (incident: Incident | null) => void;
}) {
  const inspectionCount = qualityVehicles.filter((vehicle) => vehicle.risk >= 0.6).length;
  const filtered = qualityVehicles.filter((vehicle) =>
    filter === "ALL" ? true : filter === "WATCH" ? vehicle.risk >= 0.35 && vehicle.risk < 0.6 : filter === "INSPECT" ? vehicle.risk >= 0.6 : vehicle.inspection_status === "CONFIRMED",
  );
  const prediction = qualityRecord?.current_prediction;
  const completed = qualityRecord?.prediction_history ?? [];
  const processSteps = qualityRecord ? [] : [];
  const riskTone = prediction && prediction.risk >= 0.6 ? "inspect" : prediction && prediction.risk >= 0.35 ? "watch" : "normal";
  return (
    <section className="quality-layout">
      <aside className="quality-sidebar">
        <div className="sidebar-title">
          <div><span>Vehicle quality</span><small>{qualityVehicles.length} monitored units</small></div>
          <b>{inspectionCount}</b>
        </div>
        <div className="quality-summary-line">
          <CircleAlert size={15} />
          <span><b>Inspection required</b>{inspectionCount ? `${inspectionCount} vehicles require review` : "No vehicles currently require targeted inspection"}</span>
        </div>
        <div className="quality-filters">
          {(["ALL", "WATCH", "INSPECT", "CONFIRMED"] as const).map((item) => (
            <button key={item} className={filter === item ? "active" : ""} onClick={() => onFilter(item)}>{item}</button>
          ))}
        </div>
        <div className="quality-scroll">
          {filtered.length === 0 ? (
            <div className="quality-empty">
              <Shield size={24} />
              <p>No matching vehicles</p>
              <small>Quality monitoring remains active across the production line.</small>
            </div>
          ) : (
            filtered.map((vehicle) => (
              <button
                key={vehicle.vehicle_id}
                className={`quality-row ${selectedVehicle?.vehicle_id === vehicle.vehicle_id ? "selected" : ""}`}
                onClick={() => onSelectVehicle(vehicle)}
              >
                <div className="quality-risk-indicator" style={{
                  backgroundColor: vehicle.risk >= 0.82 ? "#d55352" : vehicle.risk >= 0.60 ? "#f08c37" : vehicle.risk >= 0.35 ? "#d89a3b" : "#4f85a6"
                }} />
                <div className="quality-vehicle-info">
                  <strong>{vehicle.vehicle_id}</strong>
                  <small>{vehicle.variant || "Vehicle"} · {vehicle.current_station}</small>
                </div>
                <div className="quality-risk-score">
                  <b>{Math.round(vehicle.risk * 100)}%</b>
                  <small>{vehicle.quality_level}</small>
                </div>
              </button>
            ))
          )}
        </div>
      </aside>

      <section className="quality-detail">
        {selectedVehicle && qualityRecord ? (
          <div className="quality-vehicle-detail">
            <div className="inspector-heading">
              <div>
                <span>Vehicle Quality Twin</span>
                <h1>{selectedVehicle.vehicle_id}</h1>
                <small>
                  {selectedVehicle.variant || "Vehicle"} · {selectedVehicle.current_station} · {Math.round(selectedVehicle.line_progress * 100)}% production progress
                </small>
              </div>
              <b className={`quality-chip ${selectedVehicle.quality_level.toLowerCase()}`}>
                {selectedVehicle.quality_level}
              </b>
            </div>

            {prediction && (
              <>
                <div className="quality-grid">
                  <Operation
                    label="Quality risk"
                    value={`${Math.round(prediction.risk * 100)}%`}
                  />
                  <Operation
                    label="Prediction confidence"
                    value={`${Math.round(prediction.confidence * 100)}%`}
                  />
                  <Operation
                    label="Quality state"
                    value={prediction.risk < 0.35 ? "Within expected envelope" : "Elevated quality signature"}
                  />
                  <Operation
                    label="Inspection"
                    value={prediction.risk >= 0.6 ? prediction.recommended_inspection_point || "Quality hold" : "Standard End-of-Line"}
                  />
                </div>
                <div className={`risk-threshold ${riskTone}`}><i style={{ width: `${Math.max(4, prediction.risk * 100)}%` }} /><span>Normal</span><span>Watch 35%</span><span>Inspect 60%</span></div>
                {prediction.risk >= 0.6 && <div className="recommended-action"><ClipboardCheck size={18}/><div><span>Recommended action</span><b>Targeted body geometry inspection · {prediction.recommended_inspection_point}</b><small>Risk signal emerged after Robotic Weld; inspect before further value-add where physically possible.</small></div></div>}

                {qualityRecord.inspection_result && (
                  <div className={`inspection-result ${qualityRecord.inspection_result.result.startsWith("FAIL") ? "failed" : "passed"}`}>
                    <span>Inspection result</span>
                    <b>{qualityRecord.inspection_result.result}</b>
                    <small>
                      {qualityRecord.inspection_result.defect_family || "No defect family specified"}
                    </small>
                  </div>
                )}
              </>
            )}
            <section className="quality-timeline">
              <div className="twin-section-title"><span>Risk progression</span><small>{completed.length} retained predictions</small></div>
              <div className="risk-sequence">{completed.map((item) => <div key={`${item.station_at_prediction}-${item.prediction_timestamp}`} className={item.risk >= .6 ? "inspect" : item.risk >= .35 ? "watch" : "normal"}><i style={{height: `${Math.max(8, item.risk * 44)}px`}}/><small>{item.station_at_prediction}</small><b>{Math.round(item.risk * 100)}%</b></div>)}</div>
            </section>
            {incident && <button className="incident-context-link" onClick={() => onOpenIncident(incident)}>Part of quality incident · {incident.incident_id}<span>Open incident</span></button>}
            <BuildRecord record={qualityRecord} currentStation={selectedVehicle.current_station} />
          </div>
        ) : (
          <div className="quality-empty-detail">
            <Shield size={32} />
            <p>Select a vehicle to view quality analysis</p>
            <small>Digital thread evidence and risk attribution</small>
          </div>
        )}
      </section>

      <aside className="quality-right">
        <div className="scenario-control">
          <div>
            <b>Simulation scenario</b>
            <span>{weldDriftActive ? "Weld process drift · Active" : "Weld process · Normal"}</span>
          </div>
          <button
            className={weldDriftActive ? "active" : ""}
            onClick={onToggleWeldDrift}
          >
            {weldDriftActive ? "Restore normal process" : "Simulate weld drift"}
          </button>
        </div>
        {scenario && <div className="weld-evidence"><div className="twin-section-title"><span>Weld process evidence</span><small>{scenario.elapsed_seconds ? `${(scenario.elapsed_seconds / 60).toFixed(1)} simulated min` : "Monitoring"}</small></div><Operation label="Energy deviation" value={`${scenario.energy_deviation >= 0 ? "+" : ""}${(scenario.energy_deviation * 100).toFixed(1)}%`} /><Operation label="Process variability" value={`${scenario.process_variability.toFixed(2)}× baseline`} /><Operation label="Tool condition" value={scenario.tool_condition} /><Operation label="Vehicles exposed" value={scenario.vehicles_exposed.toString()} /><small>{scenario.affected_tool} · Electrode lot {scenario.electrode_lot}</small></div>}

        <section className="genealogy-panel">
            <div className="twin-section-title">
              <span>Common pattern</span>
              <b className="inferred-tag">{genealogy?.cohort_size ?? 0} elevated</b>
            </div>
            {genealogy && genealogy.common_factors.length > 0 ? <><div className="genealogy-factors">{genealogy.common_factors.slice(0, 4).map((factor, idx) => (
                <div key={idx} className="genealogy-factor">
                  <div className="factor-header">
                    <b>{factor.factor_name}</b>
                    <span className="factor-lift">{factor.risk_lift.toFixed(1)}× more common</span>
                  </div>
                  <div className="factor-stats">
                    <small>Suspected common factor · {factor.support}/{genealogy.cohort_size} elevated vehicles</small>
                    <small>Baseline: {(factor.baseline_prevalence * 100).toFixed(1)}%</small>
                  </div>
                </div>
              ))}</div>
            {genealogy.likely_origin_process && (
              <div className="genealogy-origin">
                <span>Likely process origin</span>
                <b>{genealogy.likely_origin_process}</b>
              </div>
            )}</> : <div className="genealogy-empty"><GitBranch size={17}/><span>No enriched common factor detected.<small>Cohort 0 above inspection threshold · monitoring tool, fixture, cell, consumable lot, variant, and time window.</small></span></div>}
            <small className="genealogy-note">Shows how often this pattern appears in higher-risk vehicles compared with recent normal production. Engineering confirmation is still required.</small>
          </section>

        {metrics && (
          <section className="quality-metrics">
            <div className="twin-section-title">
              <span>Quality validation metrics</span>
              <b className="telemetry-tag">Synthetic</b>
            </div>
            <div className="metrics-grid">
              <Operation
                label="Total predictions"
                value={metrics.total_predictions.toString()}
              />
              <Operation
                label="Defect rate"
                value={`${(metrics.defect_rate * 100).toFixed(1)}%`}
              />
              <Operation label="Precision" value={metrics.precision === null ? "—" : `${(metrics.precision * 100).toFixed(1)}%`} />
              <Operation label="Recall" value={metrics.recall === null ? "—" : `${(metrics.recall * 100).toFixed(1)}%`} />
              <Operation label="Median lead time" value={metrics.prediction_lead_time_mean === null ? "—" : `${(metrics.prediction_lead_time_mean / 60).toFixed(1)} min`} />
              <Operation label="Early interception" value={metrics.early_interception_opportunity === null ? "—" : `${(metrics.early_interception_opportunity * 100).toFixed(0)}%`} />
            </div>
            <small className="metrics-note">
              {metrics.validation_state === "AWAITING_EOL_OUTCOMES" ? "Awaiting EOL outcomes for live validation." : metrics.validation_state === "CONFIRMED_ZERO_FAILURES" ? "Confirmed outcomes available; no failures observed yet." : "Live metrics based on confirmed EOL outcomes."}<br/>Model: {metrics.model_version} · {metrics.model_status.mode === "fallback" ? "Fallback scoring" : "Synthetic · Prediction"}
            </small>
          </section>
        )}
      </aside>
    </section>
  );
}

function BuildRecord({ record, currentStation }: { record: VehicleQualityRecord; currentStation: string }) {
  const threadSteps = (record as VehicleQualityRecord & { build_record?: VehicleThread["completed_steps"] }).build_record ?? [];
  const warning = (record.current_prediction?.risk ?? 0) >= .35;
  return <section data-tour="digital-build-record" className="build-record build-history-simple"><div className="twin-section-title"><span>Build history</span><small>Saved for this vehicle</small></div><div className="build-story">{threadSteps.map((step) => <div key={`${step.station_id}-${step.exit_time}`} className={warning && step.station_id === "BIW-02" ? "pattern" : "done"}>{warning && step.station_id === "BIW-02" ? <CircleAlert size={15}/> : <CheckCircle2 size={15}/>}<span><b>{step.station_name}</b><small>{warning && step.station_id === "BIW-02" ? "Pattern found" : "Complete"}</small></span></div>)}<div className="current"><i/><span><b>{currentStation}</b><small>Current</small></span></div></div><details className="app-details"><summary>Build details <ChevronDown size={14}/></summary><div className="build-steps technical-build">{threadSteps.map((step) => <details key={`${step.station_id}-${step.exit_time}`}><summary><CheckCircle2 size={15}/><span><b>{step.station_name}</b><small>{step.cycle_time.toFixed(1)} s · {step.equipment_id}</small></span><ChevronDown size={14}/></summary>{Object.keys(step.metadata).length > 0 && <div className="step-evidence">{Object.entries(step.metadata).filter(([key]) => ["fixture","robot_cell","weld_gun","electrode_cap_lot","weld_energy_deviation","weld_variance_multiplier","twin_confidence"].includes(key)).map(([key,value]) => <small key={key}><span>{key.replaceAll("_"," ")}</span><b>{typeof value === "number" && key.includes("deviation") ? `${value >= 0 ? "+" : ""}${(value*100).toFixed(1)}%` : String(value)}</b></small>)}</div>}</details>)}</div></details></section>
}

function RightPanel({
  state,
  selected,
  dataView,
  vehicle,
  vehicleThread,
  onTestCondition,
  testCondition,
  assessment,
  forecast,
  onToggleDrift,
  incident,
  vehicleIncident,
  onOpenIncident,
}: {
  state: TwinState;
  selected: Station;
  dataView: "twin" | "observed" | "forecast";
  vehicle: Vehicle | null;
  vehicleThread: VehicleThread | null;
  onTestCondition: (
    stationId: string,
    condition: { drop?: boolean; noise?: number },
  ) => void;
  testCondition: { drop: boolean; noise: number };
  assessment: BottleneckAssessment | null;
  forecast: ForwardResult | null;
  onToggleDrift: () => void;
  incident: Incident | null;
  vehicleIncident: Incident | null;
  onOpenIncident: (incident: Incident | null) => void;
}) {
  return (
    <aside className="right-sidebar">
      <section className="overview">
        <h2>Factory overview</h2>
        <div className="overview-grid">
          <OverviewMetric
            label="Throughput"
            value={`${state.throughput_per_hour}`}
            suffix="veh/h"
            icon={<Gauge size={15} />}
          />
          <OverviewMetric
            label="In process"
            value={`${state.simulation.vehicles_in_process}`}
            icon={<Users size={15} />}
          />
          <OverviewMetric
            label="Running"
            value={`${state.simulation.stations_running}`}
            suffix={`/ ${state.stations.length}`}
            icon={<Activity size={15} />}
          />
          <OverviewMetric
            label="Twin confidence"
            value={
              state.synchronization
                ? `${Math.round(state.synchronization.overall_confidence * 100)}`
                : "—"
            }
            suffix="%"
            icon={<Crosshair size={15} />}
          />
        </div>
      </section>
      {vehicle ? (
        <VehicleInspector vehicle={vehicle} thread={vehicleThread} incident={vehicleIncident} onOpenIncident={onOpenIncident} />
      ) : (
        <SimplifiedStationInspector
          selected={selected}
          dataView={dataView}
          assessment={assessment}
          forecast={forecast}
          incident={incident}
          onOpenIncident={onOpenIncident}
        />
      )}
    </aside>
  );
}
function SimplifiedStationInspector({ selected, dataView, assessment, forecast, incident, onOpenIncident }: {
  selected: Station;
  dataView: "twin" | "observed" | "forecast";
  assessment: BottleneckAssessment | null;
  forecast: ForwardResult | null;
  incident: Incident | null;
  onOpenIncident: (incident: Incident | null) => void;
}) {
  const twin = selected.twin;
  const observation = selected.observation;
  const sourceLabel = selected.sensor_mode === "FULL TELEMETRY" ? "Direct data" : selected.sensor_mode === "LIMITED TELEMETRY" ? "Partial data" : "Basic data";
  const currentCycle = dataView === "observed" ? observation?.cycle_time : twin?.estimated_cycle;
  return <section data-tour="station-inspector" className="inspector-panel station-simple">
    <div className="inspector-heading"><div><span>Selected station</span><h1>{selected.name}</h1><small>{selected.section} · {selected.process}</small></div><b className={`health-chip ${stateTone(selected.operational_state)}`}>{selected.operational_state}</b></div>
    <div className="station-primary-grid"><Operation label="Current vehicle" value={selected.current_vehicle ?? "Between vehicles"}/><Operation label="Current cycle" value={currentCycle == null ? "No direct signal" : `${currentCycle.toFixed(1)} s`}/><Operation label="Normal cycle" value={`${(twin?.expected_cycle ?? selected.nominal_cycle_time).toFixed(1)} s`}/><Operation label="Difference from normal" value={twin ? `${twin.residual >= 0 ? "+" : ""}${twin.residual.toFixed(1)} s · ${twin.residual_trend === "RISING" ? "getting worse" : twin.residual_trend.toLowerCase()}` : "—"}/><div title="How strong the available evidence is."><Operation label="Confidence" value={twin ? `${Math.round(twin.confidence*100)}%` : "—"}/></div><Operation label="Queue" value={selected.buffer_capacity ? `${selected.buffer_level} / ${selected.buffer_capacity}` : selected.queue_length.toString()}/></div>
    <div className="data-source-summary"><span>{sourceLabel}</span><small>{sourceLabel === "Basic data" ? "LineLens combines available production events with the station's normal pattern." : sourceLabel === "Partial data" ? "LineLens fills sensor gaps using production flow and timing." : "Fresh station measurements are available."}</small></div>
    {incident && <button className="incident-context-link station-incident-link" onClick={() => onOpenIncident(incident)}><span>Active incident</span><b>{incident.title}</b><small>Open incident</small></button>}
    {dataView === "forecast" && assessment && forecast && <PredictivePanel assessment={assessment} forecast={forecast}/>} 
    <details className="app-details station-details"><summary>Why? / Details <ChevronDown size={14}/></summary><p>{selected.sensor_mode === "LEGACY / BASIC SIGNALS" ? "Direct cycle sensing is unavailable. The Twin estimate uses arrival and departure events, conveyor occupancy, nearby station flow, and the station's normal cycle." : selected.sensor_mode === "LIMITED TELEMETRY" ? "The Twin estimate combines available timestamps and conveyor occupancy with the station's normal cycle." : "The Twin estimate combines fresh station measurements with the station's learned normal cycle."}</p>{twin && <div className="technical-grid"><Operation label="Estimated range" value={`${twin.estimated_range_low.toFixed(1)}–${twin.estimated_range_high.toFixed(1)} s`}/><Operation label="Data age" value={`${twin.data_age.toFixed(1)} s`}/><Operation label="Raw data class" value={selected.sensor_mode}/><Operation label="Source" value={twin.source}/></div>}<div className="sensor-rows">{selected.temperature !== null && <Sensor label="Process temperature" value={`${selected.temperature} °C`}/>} {selected.vibration !== null && <Sensor label="Vibration" value={`${selected.vibration} mm/s`}/>} {selected.power !== null && <Sensor label="Power" value={`${selected.power} kW`}/>} {selected.torque !== null && <Sensor label="Torque" value={`${selected.torque} Nm`}/>}</div></details>
  </section>;
}
function StationInspector({
  selected,
  dataView,
  onTestCondition,
  testCondition,
  assessment,
  forecast,
  scenarioActive,
  onToggleDrift,
  incident,
  onOpenIncident,
}: {
  selected: Station;
  dataView: "twin" | "observed" | "forecast";
  onTestCondition: (
    stationId: string,
    condition: { drop?: boolean; noise?: number },
  ) => void;
  testCondition: { drop: boolean; noise: number };
  assessment: BottleneckAssessment | null;
  forecast: ForwardResult | null;
  scenarioActive: boolean;
  onToggleDrift: () => void;
  incident: Incident | null;
  onOpenIncident: (incident: Incident | null) => void;
}) {
  const observation = selected.observation,
    twin = selected.twin;
  const observedCycle = observation?.cycle_time;
  return (
    <section className="inspector-panel">
      <div className="inspector-heading">
        <div>
          <span>Station inspector · {dataView}</span>
          <h1>{selected.name}</h1>
          <small>
            {selected.section} · {selected.process}
          </small>
        </div>
        <b className={`health-chip ${stateTone(selected.operational_state)}`}>
          {selected.operational_state}
        </b>
      </div>
      <div className="operation-grid">
        <Operation
          label="Current vehicle"
          value={
            dataView === "observed"
              ? (observation?.vehicle_id ??
                (selected.sensor_mode === "FULL TELEMETRY"
                  ? "No signal (dropped)"
                  : "Not instrumented"))
              : (selected.current_vehicle ?? "Estimated")
          }
        />
        <Operation
          label="Cycle progress"
          value={
            dataView === "observed"
              ? observation?.cycle_progress !== null &&
                observation?.cycle_progress !== undefined
                ? `${Math.round(observation.cycle_progress * 100)}%`
                : "Not instrumented"
              : `${Math.round(selected.cycle_progress * 100)}%`
          }
        />
        <Operation
          label={dataView === "observed" ? "Observed cycle" : "Twin cycle"}
          value={
            dataView === "observed"
              ? observedCycle !== null && observedCycle !== undefined
                ? `${observedCycle.toFixed(1)}s`
                : "No direct signal"
              : `${selected.cycle_time.toFixed(1)}s`
          }
        />
        <Operation
          label={
            selected.buffer_capacity
              ? (selected.buffer_name ?? "Buffer")
              : "Queue"
          }
          value={
            selected.buffer_capacity
              ? `${dataView === "observed" ? (observation?.queue_level ?? "—") : selected.buffer_level} / ${selected.buffer_capacity}`
              : `${dataView === "observed" ? (observation?.queue_level ?? "—") : selected.queue_length}`
          }
        />
      </div>
      <div className="progress-bar">
        <i
          style={{
            width: `${(dataView === "observed" ? (observation?.cycle_progress ?? 0) : selected.cycle_progress) * 100}%`,
          }}
        />
      </div>
      {dataView !== "observed" && twin && (
        <section className="twin-inspector">
          <div className="twin-section-title">
            <span>Twin estimate</span>
            <b
              className={
                twin.estimated_from_indirect_evidence
                  ? "inferred-tag"
                  : "telemetry-tag"
              }
            >
              {twin.estimated_from_indirect_evidence
                ? "INFERRED"
                : "OBSERVED + FILTERED"}
            </b>
          </div>
          <div className="twin-grid">
            <Operation
              label="Normal cycle"
              value={`${twin.expected_cycle.toFixed(1)}s`}
            />
            <Operation
              label="Current estimate"
              value={`${twin.estimated_cycle.toFixed(1)}s`}
            />
            <Operation
              label="Difference from normal"
              value={`${twin.residual >= 0 ? "+" : ""}${twin.residual.toFixed(1)}s · ${twin.residual_trend.toLowerCase()}`}
            />
            <Operation
              label="Confidence"
              value={`${Math.round(twin.confidence * 100)}%`}
            />
          </div>
          <p className="estimate-range">
            Estimated range {twin.estimated_range_low.toFixed(1)}–
            {twin.estimated_range_high.toFixed(1)}s · data age{" "}
            {twin.data_age.toFixed(1)}s
          </p>
          <div className="evidence">
            <span>Source · {twin.source}</span>
            <small>{twin.evidence.join(" · ")}</small>
          </div>
        </section>
      )}
      {dataView === "forecast" && assessment && forecast && (
        <PredictivePanel assessment={assessment} forecast={forecast} />
      )}
      {incident && (
        <button className="incident-context-link station-incident-link" onClick={() => onOpenIncident(incident)}>
          <span>Active incident</span><b>{incident.title}</b><small>Open incident</small>
        </button>
      )}
      {dataView === "observed" && observation && (
        <section className="twin-inspector observed-inspector">
          <div className="twin-section-title">
            <span>Observation source</span>
            <b className="inferred-tag">SYNTHETIC</b>
          </div>
          <p className="estimate-range">
            {observation.source} · quality{" "}
            {Math.round(observation.quality * 100)}% · age{" "}
            {(selected.twin?.data_age ?? 0).toFixed(1)}s
          </p>
          <div className="evidence">
            <span>Available signals</span>
            <small>{observation.signals.join(" · ")}</small>
          </div>
        </section>
      )}
      {dataView === "observed" && !observation && (
        <section className="twin-inspector observed-inspector">
          <div className="twin-section-title">
            <span>Observation source</span>
            <b className="inferred-tag" style={{ color: "#d55352" }}>
              TELEMETRY DROPPED
            </b>
          </div>
          <p className="estimate-range">
            No synthetic PLC or sensor packets received · telemetry stream
            interrupted
          </p>
          <div className="evidence">
            <span>Signal status</span>
            <small>
              Direct telemetry dropped · twin state continues via baseline &
              flow estimation
            </small>
          </div>
        </section>
      )}
      <div className="sensor-rows">
        {selected.temperature !== null && (
          <Sensor
            label="Process temperature"
            value={`${selected.temperature} °C`}
          />
        )}
        {selected.vibration !== null && (
          <Sensor label="Vibration" value={`${selected.vibration} mm/s`} />
        )}
        {selected.power !== null && (
          <Sensor label="Welding power" value={`${selected.power} kW`} />
        )}
        {selected.torque !== null && (
          <Sensor label="Torque" value={`${selected.torque} Nm`} />
        )}
        {selected.calibration_status !== null && (
          <Sensor label="Calibration" value={selected.calibration_status} />
        )}
        <Sensor label="Data source" value={selected.sensor_mode} />
        <Sensor
          label="Current feed"
          value={observation ? "Available" : "Unavailable"}
        />
        <Sensor
          label="Transfer"
          value={selected.transfer_mode.replaceAll("_", " ").toLowerCase()}
        />
        <Sensor
          label="Vehicles completed"
          value={`${selected.vehicles_completed}`}
        />
      </div>
      {dataView === "twin" && (
        <>
          <TwinTestingControls
            stationId={selected.id}
            onTestCondition={onTestCondition}
            condition={testCondition}
          />
          {selected.id === "FA-02" && (
            <div className="scenario-control">
              <div>
                <b>Physical scenario</b>
                <span>Chassis fixture alignment delay · simulation control</span>
              </div>
              <button
                className={scenarioActive ? "active" : ""}
                onClick={onToggleDrift}
              >
                {scenarioActive ? "Restore normal process" : "Simulate process drift"}
              </button>
            </div>
          )}
        </>
      )}
      <div className="operational-summary">
        <b>How this estimate is made</b>
        <p>
          {selected.sensor_mode === "LEGACY / BASIC SIGNALS"
            ? "Direct cycle sensor is unavailable. Twin state is estimated from upstream/downstream flow timestamps, conveyor occupancy, topology continuity, and the station's learned healthy baseline."
            : selected.sensor_mode === "LIMITED TELEMETRY"
              ? "Direct cycle sensor is unavailable. Twin state is estimated from arrival/departure timestamps, conveyor occupancy, and the station's learned healthy baseline."
              : !observation
                ? "Direct telemetry stream is currently interrupted. Twin state estimator continues operating using historical process model and topology continuity."
                : "Current twin state blends fresh synthetic telemetry (PLC and tool sensors) with adaptive filtering and the station's learned healthy baseline."}
        </p>
      </div>
    </section>
  );
}
function PredictivePanel({
  assessment,
  forecast,
}: {
  assessment: BottleneckAssessment;
  forecast: ForwardResult;
}) {
  const first = forecast.impacts[0];
  const currentThroughput =
    forecast.metrics.throughput_per_hour /
    Math.max(0.01, 1 + forecast.metrics.throughput_change_percent / 100);
  return (
    <section data-tour="forecast-impact" className="predictive-panel">
      <div className="twin-section-title">
        <span>What may happen next</span>
        <b className={`risk-level ${assessment.level.toLowerCase()}`}>
          PROTOTYPE · {assessment.level}
        </b>
      </div>
      <div className="twin-grid">
        <Operation
          label="Slowdown risk"
          value={`${Math.round(assessment.risk * 100)}%`}
        />
        <Operation
          label="Confidence"
          value={`${Math.round(forecast.forecast_confidence * 100)}%`}
        />
        <Operation
          label="Trend"
          value={assessment.features.residual_trend.toLowerCase()}
        />
        <Operation
          label="First impact"
          value={first ? first.entity_id : "None material"}
        />
      </div>
      {first && (
        <p className="estimate-range">
          {first.impact_type.replaceAll("_", " ").toLowerCase()} · ETA{" "}
          {(first.eta_seconds / 60).toFixed(1)} min · range{" "}
          {(first.eta_range_low / 60).toFixed(1)}–
          {(first.eta_range_high / 60).toFixed(1)} min
        </p>
      )}
      <div className="projected-output">
        <span>Projected output</span>
        <b>
          {currentThroughput.toFixed(0)} →{" "}
          {forecast.metrics.throughput_per_hour.toFixed(0)} veh/h
        </b>
        <small>
          {forecast.scenario.horizon_seconds / 60} min · no intervention
        </small>
      </div>
      <div className="why-panel">
        <span>Why LineLens flagged this</span>
        {assessment.evidence.map((item) => (
          <small key={item}>{item}</small>
        ))}
      </div>
    </section>
  );
}
function TwinTestingControls({
  stationId,
  onTestCondition,
  condition,
}: {
  stationId: string;
  onTestCondition: (
    stationId: string,
    condition: { drop?: boolean; noise?: number },
  ) => void;
  condition: { drop: boolean; noise: number };
}) {
  const dropped = condition.drop;
  const noise = condition.noise;
  return (
    <div className="twin-testing">
      <div className="twin-section-title">
        <span>Testing · synthetic</span>
        <b className="inferred-tag">PROTOTYPE</b>
      </div>
      <div className="testing-row">
        <span>Drop telemetry</span>
        <button
          className={dropped ? "test-btn active" : "test-btn"}
          onClick={() => {
            const next = !dropped;
            void onTestCondition(stationId, { drop: next });
          }}
        >
          {dropped ? "Restore" : "Drop"}
        </button>
      </div>
      <div className="testing-row">
        <span>Inject noise</span>
        <input
          type="range"
          min="0"
          max="5"
          step="0.5"
          value={noise}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            void onTestCondition(stationId, { noise: v });
          }}
        />
        <b>{noise.toFixed(1)}s</b>
      </div>
      <small>
        Observation condition testing for twin estimation resilience.
      </small>
    </div>
  );
}
function VehicleInspector({
  vehicle,
  thread,
  incident,
  onOpenIncident,
}: {
  vehicle: Vehicle;
  thread: VehicleThread | null;
  incident: Incident | null;
  onOpenIncident: (incident: Incident | null) => void;
}) {
  // Phase 4: Quality information
  const showQualityInfo = vehicle.quality_risk >= 0.20; // Show even low-quality info
  
  return (
    <section className="inspector-panel vehicle-inspector">
      <div className="inspector-heading">
        <div>
          <span>Digital build record</span>
          <h1>{vehicle.vehicle_id}</h1>
          <small>
            {vehicle.variant} · Batch {vehicle.batch_id}
          </small>
        </div>
        <div className="heading-right">
          {showQualityInfo && (
            <b className={`quality-chip ${vehicle.quality_level.toLowerCase()}`}>
              {vehicle.quality_level}
            </b>
          )}
          <b className="health-chip idle">
            {thread ? `${Math.round(thread.line_progress * 100)}%` : "SYNCING"}
          </b>
        </div>
      </div>
      
      {showQualityInfo && (
        <div className="quality-grid">
          <Operation 
            label="Quality risk" 
            value={`${Math.round(vehicle.quality_risk * 100)}%`}
          />
          <Operation 
            label="Quality level" 
            value={vehicle.quality_level}
          />
        </div>
      )}
      {incident && <button className="incident-context-link" onClick={() => onOpenIncident(incident)}>Part of quality incident · {incident.incident_id}<span>Open incident</span></button>}
      
      <div className="operation-grid">
        <Operation
          label="Current station"
          value={vehicle.current_station ?? "Transfer"}
        />
        <Operation
          label="Line time"
          value={clock(thread?.total_line_time ?? vehicle.total_line_time)}
        />
        <Operation
          label="Build steps"
          value={`${thread?.completed_steps.length ?? 0} complete`}
        />
        <Operation label="Status" value={vehicle.status.toLowerCase()} />
      </div>
      <div className="thread-steps">
        {thread?.completed_steps.length ? (
          thread.completed_steps.map((step) => (
            <div key={`${step.station_id}-${step.exit_time}`}>
              <span>{step.station_name}</span>
              <b>{step.cycle_time.toFixed(1)}s</b>
              <small>
                {step.equipment_id} · {step.result}
              </small>
            </div>
          ))
        ) : (
          <p>
            Process events will be retained as this vehicle completes each
            station.
          </p>
        )}
      </div>
    </section>
  );
}
function OverviewMetric({
  label,
  value,
  suffix,
  icon,
}: {
  label: string;
  value: string;
  suffix?: string;
  icon: ReactNode;
}) {
  return (
    <div>
      <span>
        {icon}
        {label}
      </span>
      <strong>{value}</strong>
      {suffix && <small>{suffix}</small>}
    </div>
  );
}
function Operation({ label, value }: { label: string; value: string }) {
  return (
    <div className="operation">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}
function Sensor({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function MachinesView({
  stations,
  dataView,
  onSelect,
}: {
  stations: Station[];
  dataView: "twin" | "observed" | "forecast";
  onSelect: (id: string) => void;
}) {
  return (
    <section className="simple-page">
      <div>
        <span>Twin station directory</span>
        <h1>Automotive stations</h1>
        <p>
          {dataView !== "observed"
            ? "Estimated state combines synthetic telemetry, topology, and station-specific history."
            : "Observed view shows only direct synthetic telemetry, PLC, conveyor, and MES-style evidence."}
        </p>
      </div>
      <div className="machine-table twin-machine-table">
        <div className="machine-head">
          <span>Station</span>
          <span>Source</span>
          <span>Observed</span>
          <span>Twin</span>
          <span>Expected</span>
          <span>Residual</span>
          <span>Confidence</span>
        </div>
        {stations.map((station) => {
          const twin = station.twin,
            observation = station.observation;
          return (
            <button key={station.id} onClick={() => onSelect(station.id)}>
              <i className={stateTone(station.operational_state)} />
              <span>
                <b>{station.name}</b>
                <small>
                  {station.section} · {station.operational_state}
                </small>
              </span>
              <em>
                {dataView === "observed"
                  ? (observation?.source ?? "Feed unavailable")
                  : (twin?.source ?? station.sensor_mode)}
              </em>
              <em>
                {observation?.cycle_time !== null &&
                observation?.cycle_time !== undefined
                  ? `${observation.cycle_time.toFixed(1)}s`
                  : observation
                    ? "Indirect evidence"
                    : "—"}
              </em>
              <em>
                {dataView !== "observed" && twin
                  ? `${twin.estimated_cycle.toFixed(1)}s`
                  : "—"}
              </em>
              <em>
                {dataView !== "observed" && twin
                  ? `${twin.expected_cycle.toFixed(1)}s`
                  : "—"}
              </em>
              <em>
                {dataView !== "observed" && twin
                  ? `${twin.residual >= 0 ? "+" : ""}${twin.residual.toFixed(1)}s`
                  : "—"}
              </em>
              <em>
                {dataView !== "observed" && twin
                  ? `${Math.round(twin.confidence * 100)}%`
                  : "—"}
              </em>
            </button>
          );
        })}
      </div>
    </section>
  );
}
function AnalyticsView({
  history,
  station,
  stations,
  onSelect,
  assessment,
  forecast,
}: {
  history: HistoryPoint[];
  station: Station;
  stations: Station[];
  onSelect: (id: string) => void;
  assessment: BottleneckAssessment | null;
  forecast: ForwardResult | null;
}) {
  const recent = history.slice(-28);
  return (
    <section className="simple-page analytics-page">
      <div className="analytics-heading">
        <div>
          <span>Twin history</span>
          <h1>Observed, estimated, expected</h1>
          <p>
            One station's evolving prototype twin state over the current
            synthetic shift.
          </p>
        </div>
        <label>
          Station
          <select
            value={station.id}
            onChange={(event) => onSelect(event.target.value)}
          >
            {stations.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <TwinCycleChart station={station} />
      <ResidualTrendChart station={station} />
      <div className="forecast-analytics-grid">
        <RiskTrendChart assessment={assessment} />
        <QueueTrajectoryChart station={station} forecast={forecast} />
      </div>
      <div className="analytics-grid">
        <ChartCard
          title="Line throughput"
          unit="veh/h"
          values={recent.map((point) => point.throughput_per_hour)}
          color="#1585a1"
        />
        <ChartCard
          title="Average cycle time"
          unit="sec"
          values={recent.map((point) => point.avg_cycle_time)}
          color="#357f9d"
        />
        <ChartCard
          title="Section utilization"
          unit="%"
          values={recent.map(
            (point) =>
              (point.body_utilization +
                point.paint_utilization +
                point.final_utilization) /
              3,
          )}
          color="#3a9a78"
        />
      </div>
    </section>
  );
}
function RiskTrendChart({
  assessment,
}: {
  assessment: BottleneckAssessment | null;
}) {
  const points = assessment?.history.slice(-40) ?? [];
  const line = points
    .map(
      (point, index) =>
        `${index ? "L" : "M"}${index * (320 / Math.max(1, points.length - 1))},${56 - point.risk * 46}`,
    )
    .join(" ");
  return (
    <section className="risk-chart-card">
      <div>
        <span>Bottleneck risk</span>
        <strong>
          {assessment ? `${Math.round(assessment.risk * 100)}%` : "—"}
        </strong>
      </div>
      <small>Risk follows persistent Twin deviation, not a raw threshold</small>
      <svg viewBox="0 0 320 60" aria-label="Bottleneck risk trend">
        <path d="M0 44H320" stroke="#e6d9c3" strokeDasharray="4 4" />
        <path d={line} fill="none" stroke="#c58a2d" strokeWidth="2" />
      </svg>
    </section>
  );
}
function QueueTrajectoryChart({
  station,
  forecast,
}: {
  station: Station;
  forecast: ForwardResult | null;
}) {
  const points = forecast?.trajectory ?? [];
  const values = points.map((point) => point.station_queues[station.id] ?? 0);
  const high = Math.max(1, ...values);
  const line = values
    .map(
      (value, index) =>
        `${index ? "L" : "M"}${index * (320 / Math.max(1, values.length - 1))},${56 - (value / high) * 42}`,
    )
    .join(" ");
  return (
    <section className="risk-chart-card">
      <div>
        <span>Queue trajectory · no action</span>
        <strong>{values.at(-1) ?? "—"} projected</strong>
      </div>
      <small>
        Now → +{forecast ? forecast.scenario.horizon_seconds / 60 : 0} min ·
        simulation-derived
      </small>
      <svg viewBox="0 0 320 60" aria-label="Forecast queue trajectory">
        <path
          d={`M0 ${56 - ((values[0] ?? 0) / high) * 42}H320`}
          stroke="#8397a1"
        />
        <path
          d={line}
          fill="none"
          stroke="#c58a2d"
          strokeWidth="2"
          strokeDasharray="5 3"
        />
      </svg>
    </section>
  );
}
function TwinCycleChart({ station }: { station: Station }) {
  const points = station.twin?.history.slice(-32) ?? [];
  const latest = points.at(-1);
  const all = points.length
    ? points.flatMap((point) => [
        point.estimated_cycle,
        point.expected_cycle,
        ...(point.observed_cycle === null ? [] : [point.observed_cycle]),
      ])
    : [station.twin?.expected_cycle ?? station.cycle_time];
  const low = Math.min(...all, station.twin?.estimated_range_low ?? 0) - 0.7,
    high = Math.max(...all, station.twin?.estimated_range_high ?? 1) + 0.7;
  const rangeSeconds =
    points.length > 1
      ? points.at(-1)!.simulation_time - points[0].simulation_time
      : 0;
  const line = (values: Array<number | null>) =>
    values
      .map((value, index) =>
        value === null
          ? ""
          : `${values.slice(0, index).at(-1) === null ? "M" : index ? "L" : "M"}${index * (320 / Math.max(1, values.length - 1))},${70 - ((value - low) / Math.max(0.1, high - low)) * 56}`,
      )
      .join(" ");
  return (
    <section className="twin-chart-card">
      <div className="twin-chart-head">
        <div>
          <span>{station.name}</span>
          <strong>
            {latest
              ? `${latest.estimated_cycle.toFixed(1)} sec`
              : "Assimilating"}
          </strong>
          <small>
            {latest
              ? `Residual ${latest.residual >= 0 ? "+" : ""}${latest.residual.toFixed(1)}s · ${Math.round(latest.confidence * 100)}% confidence`
              : "Waiting for synthetic observations"}
          </small>
          <small>
            Last {Math.round(rangeSeconds)} simulated seconds · Expected
            baseline {station.twin?.expected_cycle.toFixed(1) ?? "—"}s
            {station.sensor_mode !== "FULL TELEMETRY" &&
              " · Observed cycle is unavailable at this sensor maturity"}
          </small>
        </div>
        <div className="chart-legend">
          <i className="observed" />
          Observed
          <i className="estimated" />
          Twin estimate
          <i className="expected" />
          Expected
        </div>
      </div>
      <svg
        viewBox="0 0 320 76"
        aria-label="Observed versus twin estimate versus expected cycle time"
      >
        <path d="M0 72H320" stroke="#dce5e9" />
        <text x="2" y="10" fill="#8b9aa3" fontSize="7">
          {high.toFixed(1)}s
        </text>
        <text x="2" y="69" fill="#8b9aa3" fontSize="7">
          {low.toFixed(1)}s
        </text>
        <path
          d={line(points.map((point) => point.expected_cycle))}
          fill="none"
          stroke="#91a4ad"
          strokeDasharray="4 4"
          strokeWidth="1.5"
        />
        <path
          d={line(points.map((point) => point.estimated_cycle))}
          fill="none"
          stroke="#168da6"
          strokeWidth="2.2"
        />
        <path
          d={line(points.map((point) => point.observed_cycle))}
          fill="none"
          stroke="#557788"
          strokeWidth="1.8"
        />
      </svg>
    </section>
  );
}
function ResidualTrendChart({ station }: { station: Station }) {
  const points = station.twin?.history.slice(-32) ?? [];
  const trend = station.twin?.residual_trend ?? "STABLE";
  if (!points.length) return null;
  const residuals = points.map((p) => p.residual);
  const absMax = Math.max(2, ...residuals.map((r) => Math.abs(r)));
  const pad = absMax * 0.15;
  const low = -absMax - pad,
    high = absMax + pad;
  const zeroY = 52 - ((0 - low) / Math.max(0.1, high - low)) * 44;
  const line = residuals
    .map(
      (r, i) =>
        `${i ? "L" : "M"}${i * (320 / Math.max(1, residuals.length - 1))},${52 - ((r - low) / Math.max(0.1, high - low)) * 44}`,
    )
    .join(" ");
  const fill = `${line}L${320},${zeroY}L0,${zeroY}Z`;
  const trendColor =
    trend === "RISING"
      ? "#c98a22"
      : trend === "FALLING"
        ? "#2988a0"
        : "#6d8390";
  return (
    <section className="residual-chart-card">
      <div className="residual-chart-head">
        <div>
        <span>Difference from normal</span>
          <strong style={{ color: trendColor }}>{trend}</strong>
        </div>
        <small>
          Deviation from station-specific baseline over recent synthetic shift
        </small>
      </div>
      <svg viewBox="0 0 320 56" aria-label="Twin residual trend over time">
        <path
          d={`M0 ${zeroY}H320`}
          stroke="#c1cdd4"
          strokeDasharray="3 3"
          strokeWidth="1"
        />
        <path
          d={fill}
          fill={
            trend === "RISING" ? "rgba(201,138,34,.08)" : "rgba(22,141,166,.06)"
          }
        />
        <path d={line} fill="none" stroke={trendColor} strokeWidth="2" />
        <text
          x="324"
          y={zeroY + 3}
          fill="#9aa8b1"
          fontSize="7"
          textAnchor="start"
        >
          0
        </text>
      </svg>
    </section>
  );
}
function ChartCard({
  title,
  unit,
  values,
  color,
}: {
  title: string;
  unit: string;
  values: number[];
  color: string;
}) {
  const latest = values.at(-1) ?? 0;
  const points = values.length
    ? values
        .map(
          (value, index) =>
            `${index * (180 / Math.max(1, values.length - 1))},${42 - ((value - Math.min(...values)) / Math.max(1, Math.max(...values) - Math.min(...values))) * 30}`,
        )
        .join(" ")
    : "";
  return (
    <section className="chart-card">
      <span>{title}</span>
      <strong>
        {latest.toFixed(1)} <small>{unit}</small>
      </strong>
      <svg viewBox="0 0 180 46">
        <path d={`M${points}`} fill="none" stroke={color} strokeWidth="2" />
        <path d="M0 43H180" stroke="#d9e1e7" />
      </svg>
    </section>
  );
}
function EventsView({
  events,
  forecastAlerts,
  validation,
}: {
  events: OperationalEvent[];
  forecastAlerts: ForecastAlert[];
  validation: ForecastValidation | null;
}) {
  const combined = [
    ...forecastAlerts.map((alert) => ({
      event_id: alert.alert_id,
      simulation_time: alert.simulation_time,
      severity: alert.severity,
      source: alert.source,
      message: alert.message,
      forecast: true,
    })),
    ...events.map((event) => ({ ...event, forecast: false })),
  ].sort((a, b) => b.simulation_time - a.simulation_time);
  return (
    <section className="simple-page">
      <div>
        <span>Operational log</span>
        <h1>Live events</h1>
        <p>
          Operational events and deduplicated simulation-derived forecast
          alerts.
        </p>
      </div>
      <div className="events-log">
        {combined.map((event) => (
          <article key={event.event_id}>
            <i className={event.severity.toLowerCase()} />
            <time>{clock(event.simulation_time)}</time>
            <div>
              <b>
                {event.forecast ? "FORECAST · " : ""}
                {event.source}
              </b>
              <p>{event.message}</p>
            </div>
            <span>{event.severity}</span>
          </article>
        ))}
      </div>
      {validation && (
        <section className="validation-summary">
          <span>Synthetic forecast validation</span>
          <b>
            {validation.prediction_lead_time_seconds !== null
              ? `Lead time ${clock(validation.prediction_lead_time_seconds)} · impact ETA error ${clock(validation.impact_eta_error_seconds ?? 0)}`
              : "Awaiting material actual impact"}
          </b>
          <small>
            {validation.metrics
              .map((metric) =>
                metric.evaluated
                  ? `+${metric.horizon_seconds / 60}m queue MAE ${metric.queue_mae} · accumulator MAE ${metric.accumulator_mae} · throughput MAE ${metric.throughput_mae} · state ${Math.round((metric.state_accuracy ?? 0) * 100)}%`
                  : `+${metric.horizon_seconds / 60}m pending`,
              )
              .join("  |  ")}
          </small>
        </section>
      )}
    </section>
  );
}
