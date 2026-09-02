export const TOUR_STORAGE_KEY = "linelens.phase6.tour-seen";

export type TourPage = "Dashboard" | "Quality" | "Incidents";

export interface TourStep {
  id: string;
  page: TourPage;
  target: string;
  stationId?: string;
  title: string;
  text: string;
  hint?: string;
  scenario?: "bottleneck" | "quality";
}

export const TOUR_STEPS: readonly TourStep[] = [
  { id: "factory", page: "Dashboard", target: "factory-canvas", title: "Your live factory", text: "Vehicles move through Body, Paint and Final Assembly. LineLens keeps this digital model updated as production changes.", hint: "Drag to rotate · Scroll to zoom" },
  { id: "sensor-gap", page: "Dashboard", target: "station-inspector", stationId: "FA-01", title: "Even when data is limited", text: "Not every machine has modern sensors. LineLens uses the data that is available and shows how confident it is." },
  { id: "prediction", page: "Dashboard", target: "forecast-control", stationId: "FA-02", title: "See trouble before it spreads", text: "LineLens learns what is normal for each station. When a station begins slowing, it warns where the impact may appear next." },
  { id: "impact", page: "Dashboard", target: "forecast-impact", stationId: "FA-02", scenario: "bottleneck", title: "See what may happen next", text: "Chassis Marriage is slowing. LineLens expects the queue to grow and downstream stations to run short of incoming vehicles." },
  { id: "vehicle-memory", page: "Quality", target: "digital-build-record", title: "Every vehicle has a memory", text: "LineLens remembers which station, tool and batch built each vehicle—and what happened there." },
  { id: "common-pattern", page: "Quality", target: "common-pattern", scenario: "quality", title: "Find what affected vehicles share", text: "Several risky vehicles passed through the same weld tool. That tells the quality team where to investigate first." },
  { id: "response", page: "Incidents", target: "incident-response", title: "From warning to action", text: "LineLens brings the warning, affected vehicles and evidence into one place. The plant team stays in control and decides what to check next." },
] as const;

export interface TourProgress {
  step: number;
  complete: boolean;
}

export const newTour = (): TourProgress => ({ step: 0, complete: false });
export const nextTourStep = (progress: TourProgress): TourProgress =>
  progress.step >= TOUR_STEPS.length - 1 ? { step: progress.step, complete: true } : { step: progress.step + 1, complete: false };
export const previousTourStep = (progress: TourProgress): TourProgress => ({ step: Math.max(0, progress.step - 1), complete: false });
export const hasSeenTour = (storage: Pick<Storage, "getItem">): boolean => storage.getItem(TOUR_STORAGE_KEY) === "1";
export const rememberTour = (storage: Pick<Storage, "setItem">): void => storage.setItem(TOUR_STORAGE_KEY, "1");
