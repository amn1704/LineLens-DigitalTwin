export const TOUR_STORAGE_KEY = "linelens.final-tour-seen";
export const GUIDE_STORAGE_KEY = "linelens.page-guide-progress";

export type TourPage = "Dashboard" | "Machines" | "Quality" | "Incidents" | "Analytics";
export type Scenario = "bottleneck" | "quality";
export interface TourStep { id: string; page: TourPage; target: string; title: string; text: string; hint?: string; stationId?: string; scenario?: Scenario; dataView?: "observed" | "twin" | "forecast"; qualityFilter?: "REVIEW" | "WATCH" | "INSPECT" | "ALL"; validation?: boolean; }
export interface GuideChapter { id: string; label: string; page: TourPage; duration: string; summary: string; steps: readonly TourStep[]; }

const step = (id: string, page: TourPage, target: string, title: string, text: string, extra: Partial<TourStep> = {}): TourStep => ({ id, page, target, title, text, ...extra });

// One deliberate product story. Demo steps wait for the same backend simulation calls
// used by the visible Demo controls; this file never supplies operational values.
export const TOUR_STEPS: readonly TourStep[] = [
  step("welcome", "Dashboard", "factory-canvas", "Your digital factory", "Vehicles move through Body Shop, Paint Shop and Final Assembly. LineLens keeps an evolving view as the synthetic factory changes."),
  step("line", "Dashboard", "factory-canvas", "The production line", "This view shows the complete line and the vehicles moving between its three main sections."),
  step("choose", "Dashboard", "station-list", "Choose a station", "Select any station to see what is happening there now and where its evidence comes from."),
  step("station", "Dashboard", "station-inspector", "Understand a station", "The inspector compares the current cycle with normal behaviour, queue and confidence in one place.", { stationId: "FA-02", dataView: "twin" }),
  step("observed", "Dashboard", "forecast-control", "Observed", "Observed is information coming directly from the factory. This prototype labels synthetic telemetry clearly when it is the source.", { dataView: "observed" }),
  step("twin", "Dashboard", "forecast-control", "Twin", "Twin is LineLens’s best estimate of what is happening now when evidence is incomplete.", { dataView: "twin" }),
  step("forecast", "Dashboard", "forecast-control", "Forecast", "Forecast shows what LineLens expects may happen next if nothing changes.", { dataView: "forecast" }),
  step("gap", "Dashboard", "station-inspector", "Sensor gaps", "Not every station has modern sensors. At a basic-data station, LineLens combines the data that exists and shows lower confidence.", { stationId: "FA-01", dataView: "twin" }),
  step("explore", "Dashboard", "viewport-controls", "Explore the factory", "Use Orbit to inspect the line, Walk for first-person exploration, and Flythrough for an automatic view of the production line."),
  step("bottleneck", "Dashboard", "station-inspector", "Developing bottleneck", "LineLens is now running the real Bottleneck demonstration. It waits for the simulator and prediction pipeline before showing a warning.", { stationId: "FA-02", scenario: "bottleneck", dataView: "twin" }),
  step("why", "Dashboard", "station-inspector", "Why it was flagged", "A warning is based on a persistent pattern: current cycle, normal cycle, difference and queue—not one random slow cycle.", { stationId: "FA-02", dataView: "twin" }),
  step("impact", "Dashboard", "forecast-impact", "What may happen next", "The computed no-intervention forecast shows potential queue growth and downstream starvation using the live simulator output.", { stationId: "FA-02", dataView: "forecast" }),
  step("incident", "Incidents", "incident-list", "From warning to incident", "Important predictions become Incidents so the plant team has one focused place to investigate."),
  step("checks", "Incidents", "incident-response", "What to check", "The incident explains what happened, what may happen next, why it was detected and what the team can check. People decide what to do."),
  step("quality", "Quality", "quality-vehicle-list", "Vehicle quality", "LineLens now runs the real Weld quality demonstration. Production problems are not only about speed; every vehicle also has a quality history.", { scenario: "quality", qualityFilter: "ALL" }),
  step("record", "Quality", "digital-build-record", "Digital build record", "For one vehicle, LineLens keeps the stations, tools, batches and meaningful process evidence that shaped its build.", { qualityFilter: "ALL" }),
  step("early", "Quality", "quality-primary", "Early quality warning", "A vehicle can be flagged before normal End-of-Line confirmation when earlier process evidence looks unusual. The warning includes risk, likely origin and next check.", { qualityFilter: "INSPECT" }),
  step("pattern", "Quality", "common-pattern", "Common pattern", "When several risky vehicles share a real tool, cell or lot from the Quality pipeline, LineLens highlights the pattern. It is a lead to investigate, not a confirmed root cause.", { qualityFilter: "INSPECT" }),
  step("stations", "Machines", "station-directory", "See the bigger picture", "Stations compares the whole line. Trends then shows how one station’s behaviour changes over time."),
  step("trust", "Analytics", "validation-summary", "Trust and finish", "Predictions are checked against later simulated outcomes. Wrong predictions are not hidden. You now know the LineLens story: see now, predict next, trace affected vehicles and respond with evidence.", { validation: true }),
] as const;

export const GUIDE_CHAPTERS: readonly GuideChapter[] = [
  { id: "dashboard", label: "Dashboard", page: "Dashboard", duration: "~2 min", summary: "Factory view and early warning", steps: [step("factory", "Dashboard", "factory-canvas", "Factory view", "Vehicles move through Body, Paint and Final Assembly."), step("list", "Dashboard", "station-list", "Station list", "Choose a station to inspect it."), step("inspector", "Dashboard", "station-inspector", "Selected station", "See the cycle, normal behaviour, difference, queue and confidence."), step("views", "Dashboard", "forecast-control", "Observed, Twin and Forecast", "Observed is direct telemetry. Twin is the estimate now. Forecast is what may happen next."), step("controls", "Dashboard", "viewport-controls", "Explore and demonstrate", "The viewport toolbar contains Walk, Flythrough, simulation and demo controls.")] },
  { id: "quality", label: "Quality", page: "Quality", duration: "~2 min", summary: "Vehicle risk and build history", steps: [step("vehicles", "Quality", "quality-vehicle-list", "Vehicles to review", "Watch and Inspect bring meaningful review needs forward."), step("risk", "Quality", "quality-primary", "Quality risk", "Risk indicates a vehicle may need extra inspection."), step("record", "Quality", "digital-build-record", "Digital build record", "Trace stations, tools and batches for the vehicle."), step("pattern", "Quality", "common-pattern", "Common pattern", "Shared factors guide investigation; they are not automatic root-cause claims.")] },
  { id: "incidents", label: "Incidents", page: "Incidents", duration: "~90 sec", summary: "Human-led response", steps: [step("attention", "Incidents", "incident-list", "Attention needed", "Important predictions become Incidents."), step("story", "Incidents", "incident-response", "Evidence first", "See what happened, expected impact, why and what to check."), step("workflow", "Incidents", "incident-response-panel", "Response tracking", "Acknowledge, investigate and resolve record the team response; they never control equipment.")] },
  { id: "stations", label: "Stations", page: "Machines", duration: "~1 min", summary: "Line-wide comparison", steps: [step("directory", "Machines", "station-directory", "Station directory", "Compare each production station in one place."), step("evidence", "Machines", "station-directory", "Evidence and confidence", "Data source makes direct, partial and basic coverage clear.")] },
  { id: "trends", label: "Trends", page: "Analytics", duration: "~1 min", summary: "How behaviour changes", steps: [step("trends", "Analytics", "trends-page", "Station trends", "Compare factory data, Twin estimate and normal behaviour over time."), step("difference", "Analytics", "difference-chart", "Difference from normal", "A sustained difference is more useful than a single unusual cycle.")] },
] as const;

export interface TourProgress { step: number; complete: boolean; }
export const newTour = (): TourProgress => ({ step: 0, complete: false });
export const nextTourStep = (p: TourProgress): TourProgress => p.step >= TOUR_STEPS.length - 1 ? { step: p.step, complete: true } : { step: p.step + 1, complete: false };
export const previousTourStep = (p: TourProgress): TourProgress => ({ step: Math.max(0, p.step - 1), complete: false });
export const hasSeenTour = (s: Pick<Storage, "getItem">) => s.getItem(TOUR_STORAGE_KEY) === "1";
export const rememberTour = (s: Pick<Storage, "setItem">) => s.setItem(TOUR_STORAGE_KEY, "1");
export const completedGuides = (s: Pick<Storage, "getItem">): string[] => { try { return JSON.parse(s.getItem(GUIDE_STORAGE_KEY) ?? "[]"); } catch { return []; } };
export const rememberGuide = (s: Pick<Storage, "getItem" | "setItem">, id: string) => { const next = [...new Set([...completedGuides(s), id])]; s.setItem(GUIDE_STORAGE_KEY, JSON.stringify(next)); return next; };
