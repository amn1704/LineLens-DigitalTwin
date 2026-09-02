# LineLens Guided Tour

LineLens includes a built-in spotlight walkthrough designed for a first-time evaluator or executive judge. The tour runs automatically, controls the 3D camera, manages simulation state, and highlights key UI components.

## The Seven Steps

1. **Welcome to LineLens**: Introduces the 11-station synthetic factory and the core value proposition (early prediction).
2. **The Digital Twin**: Spotlights the Twin State Estimator, showing how it builds healthy baselines from normal observations.
3. **Sensor Integration**: Highlights the varying sensor maturity tiers and the evidence panel.
4. **Predicting Bottlenecks**: Moves the camera to Chassis Marriage, triggers a synthetic drift, and shows the interpretable risk model in action.
5. **Quality Tracking**: Explains the digital build record and how quality risk is traced per vehicle.
6. **Incident Workflow**: Focuses on the human-in-the-loop response mechanism.
7. **Validation & Trust**: Points to the validation metrics that compare predictions against actual outcomes.

## How the Tour Works

- **Automation**: The tour controls the camera to ensure the subject is always in frame. It slows or pauses the underlying simulation when necessary to keep the presentation clean.
- **Replay**: You can start the tour anytime by clicking the **Tour** button in the header, or by loading the application with the URL parameter `?tour=welcome`.
- **State Management**: Tour completion is stored in the browser's `localStorage` so it doesn't interrupt returning users.

## Completion Options

Upon finishing the ~80-second tour, users are presented with three options to continue their evaluation:
- **Explore LineLens**: Closes the tour and allows free navigation of the healthy factory.
- **Run Bottleneck Demo**: Resets the line and initiates the Chassis Marriage drift scenario.
- **Run Quality Demo**: Resets the line, switches to the Quality workspace, and initiates the Robotic Weld drift scenario.
