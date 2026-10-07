import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { GUIDE_CHAPTERS, PITCH_STEPS, TOUR_STEPS, completedGuides, hasSeenTour, newTour, nextTourStep, previousTourStep, rememberGuide, rememberTour, tourSteps } from "../src/tour.ts";

// The data-tour attributes the app really renders; a tour step pointing anywhere else
// would leave the presenter without a spotlight.
const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const KNOWN_TARGETS = new Set([...appSource.matchAll(/data-tour="([^"]+)"/g)].map((match) => match[1]));
const PAGES = ["Dashboard", "Quality", "Incidents", "Machines", "Analytics", "Activity"];
const SCENARIOS = ["bottleneck", "quality"];

const storage = () => {
  const values = new Map();
  return { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
};

test("first run, skip persistence, and replay state", () => {
  const memory = storage();
  assert.equal(hasSeenTour(memory), false);
  rememberTour(memory);
  assert.equal(hasSeenTour(memory), true);
  assert.deepEqual(newTour(), { step: 0, complete: false });
});

test("full product tour has twenty valid, navigable story steps", () => {
  assert.equal(TOUR_STEPS.length, 20);
  for (const step of TOUR_STEPS) {
    assert.ok(step.target);
    assert.ok(["Dashboard", "Quality", "Incidents", "Machines", "Analytics"].includes(step.page));
  }
  assert.equal(TOUR_STEPS.find((step) => step.id === "gap")?.stationId, "FA-01");
  assert.equal(TOUR_STEPS.find((step) => step.id === "bottleneck")?.scenario, "bottleneck");
  assert.equal(TOUR_STEPS.find((step) => step.id === "quality")?.scenario, "quality");
});

test("tour controller moves back, forward, and completes", () => {
  let state = newTour();
  state = nextTourStep(state);
  assert.equal(state.step, 1);
  state = previousTourStep(state);
  assert.equal(state.step, 0);
  for (let index = 0; index < TOUR_STEPS.length; index += 1) state = nextTourStep(state);
  assert.equal(state.complete, true);
});

test("product guide covers every important workspace with valid targets", () => {
  assert.deepEqual(GUIDE_CHAPTERS.map((chapter) => chapter.id), ["dashboard", "quality", "incidents", "stations", "trends", "activity"]);
  const expectedStepCounts = { dashboard: 7, quality: 7, incidents: 6, stations: 5, trends: 6, activity: 4 };
  for (const chapter of GUIDE_CHAPTERS) {
    assert.equal(chapter.steps.length, expectedStepCounts[chapter.id], `${chapter.label} guide should remain complete`);
    assert.ok(chapter.summary, `${chapter.label} needs a plain-language purpose`);
    for (const step of chapter.steps) assert.ok(step.target && step.title && step.text && step.hint, `${chapter.label} step needs a target, explanation, and action`);
  }
});

test("completed chapters persist without storing factory entities", () => {
  const memory = storage();
  assert.deepEqual(completedGuides(memory), []);
  rememberGuide(memory, "dashboard");
  rememberGuide(memory, "quality");
  rememberGuide(memory, "dashboard");
  assert.deepEqual(completedGuides(memory), ["dashboard", "quality"]);
});

test("every tour and guide step points at a rendered data-tour target", () => {
  assert.ok(KNOWN_TARGETS.size > 10);
  for (const step of [...TOUR_STEPS, ...GUIDE_CHAPTERS.flatMap((chapter) => chapter.steps)]) {
    assert.ok(KNOWN_TARGETS.has(step.target), `${step.id} targets unknown data-tour "${step.target}"`);
  }
});

test("pitch demo is a short story over known targets and valid scenarios", () => {
  assert.ok(PITCH_STEPS.length >= 8 && PITCH_STEPS.length <= 9);
  assert.equal(new Set(PITCH_STEPS.map((step) => step.id)).size, PITCH_STEPS.length);
  for (const step of PITCH_STEPS) {
    assert.ok(KNOWN_TARGETS.has(step.target), `${step.id} targets unknown data-tour "${step.target}"`);
    assert.ok(PAGES.includes(step.page), `${step.id} uses unknown page ${step.page}`);
    if (step.scenario) assert.ok(SCENARIOS.includes(step.scenario), `${step.id} uses unknown scenario ${step.scenario}`);
    if (step.dataView) assert.ok(["observed", "twin", "forecast"].includes(step.dataView));
    const words = step.text.trim().split(/\s+/).length;
    assert.ok(words <= 25, `${step.id} has ${words} words; keep pitch text narratable`);
  }
  assert.deepEqual(PITCH_STEPS.filter((step) => step.scenario).map((step) => step.scenario), ["bottleneck", "quality"]);
  for (const target of ["impact-overview", "incident-impact", "sustainability-card", "common-pattern", "validation-summary"]) {
    assert.ok(PITCH_STEPS.some((step) => step.target === target), `pitch should show ${target}`);
  }
});

test("pitch steps read their evidence while the matching scenario is live", () => {
  const index = (predicate) => PITCH_STEPS.findIndex(predicate);
  const bottleneck = index((step) => step.scenario === "bottleneck");
  const quality = index((step) => step.scenario === "quality");
  for (const target of ["impact-overview", "incident-impact", "sustainability-card"]) {
    const position = index((step) => step.target === target);
    assert.ok(position > bottleneck && position < quality, `${target} must sit between the bottleneck and quality scenarios`);
  }
  assert.ok(index((step) => step.target === "common-pattern") > quality);
});

test("tour controller completes either story", () => {
  assert.equal(tourSteps("full"), TOUR_STEPS);
  assert.equal(tourSteps("pitch"), PITCH_STEPS);
  let state = newTour();
  for (let index = 0; index < PITCH_STEPS.length - 1; index += 1) state = nextTourStep(state, PITCH_STEPS);
  assert.deepEqual(state, { step: PITCH_STEPS.length - 1, complete: false });
  assert.equal(nextTourStep(state, PITCH_STEPS).complete, true);
});
