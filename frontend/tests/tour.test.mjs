import assert from "node:assert/strict";
import test from "node:test";
import { GUIDE_CHAPTERS, TOUR_STEPS, completedGuides, hasSeenTour, newTour, nextTourStep, previousTourStep, rememberGuide, rememberTour } from "../src/tour.ts";

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
  assert.deepEqual(GUIDE_CHAPTERS.map((chapter) => chapter.id), ["dashboard", "quality", "incidents", "stations", "trends"]);
  for (const chapter of GUIDE_CHAPTERS) {
    assert.ok(chapter.steps.length >= 2, `${chapter.label} needs a useful guide`);
    for (const step of chapter.steps) assert.ok(step.target && step.title && step.text);
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
