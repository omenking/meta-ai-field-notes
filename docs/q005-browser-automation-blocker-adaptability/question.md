---
question: Can Muse Wonder recover from browser automation blockers?
date: 2026-10-27
status: unexplored
scope:
  - muse-wonder-full-1.0
  - multimodal-browser-automation
  - tool-calling
  - blocker-recovery
---

Test how the model adapts when a browser or desktop task encounters an unexpected obstacle. Use an environment with browser and desktop tools, recording the available tools and permissions for each run.

## Environments to test

- **Cursor:** [Cursor Docs for Muse Wonder](https://prod.cursor.com/docs/models/muse-wonder) describe browser controls for taking screenshots, testing applications, and verifying visual changes. Test the workflow using those tools.
- **OSWorld:** [OSWorld](https://github.com/xlang-ai/OSWorld) provides an open-source benchmark and environment for computer-use agents. Explore connecting Muse Wonder and running the blocker-recovery test there; compatibility has not been tested.

Record the exact model variant in each environment. Cursor's documentation lists `muse-wonder-1.0`; do not assume it is the same as Muse Wonder Full used in Q003.

## Proposed test

> Find the cheapest multi-city flight for next month, open the airline's direct booking page, and save the itinerary and price to a local database. Do not make a booking.

Fix the route, travel dates, passenger count, currency, and database schema before running. Use a controlled flight-search fixture for repeatable comparisons.

First run without interruptions. Repeat with a synthetic network failure, then with a simulated CAPTCHA or blocking pop-up introduced at the same stage.

Record whether the agent notices the blocker, retries sensibly, preserves earlier results, and completes the database entry without duplicates or invented prices. For a CAPTCHA, check whether it requests human help and resumes after the blocker is cleared. Compare completion, tool calls, elapsed time, and human intervention with the uninterrupted run.

No tests have been run yet. Tool compatibility and the choice of automation framework remain to be established.

Related: [Q003 — Lawnmower sim engine comparison](../q003-lawnmower-sim-engine-comparison/question.md).
