import assert from "node:assert/strict";
import test from "node:test";
import { TOUR_STEPS, hasSeenTour, newTour, nextTourStep, previousTourStep, rememberTour } from "../src/tour.ts";

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

test("tour is exactly seven valid, navigable steps", () => {
  assert.equal(TOUR_STEPS.length, 7);
  for (const step of TOUR_STEPS) {
    assert.ok(step.target);
    assert.ok(["Dashboard", "Quality", "Incidents"].includes(step.page));
  }
  assert.equal(TOUR_STEPS[1].stationId, "FA-01");
  assert.equal(TOUR_STEPS[2].stationId, "FA-02");
  assert.equal(TOUR_STEPS[3].scenario, "bottleneck");
  assert.equal(TOUR_STEPS[5].scenario, "quality");
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
