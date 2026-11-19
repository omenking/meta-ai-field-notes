---
question: Can Muse Wonder reproduce a UI and extend its pixel-art style?
date: 2026-10-27
status: unexplored
scope:
  - muse-wonder-full-1.0
  - multimodal-ui-reconstruction
  - pixel-art-sprite-pipelines
---

Test whether the model can turn an existing 2D inventory screenshot or pixel-art sprite sheet into a working UI and matching prompts for new assets.

## Proposed test

Provide a UI mockup screenshot and use this prompt:

> Analyze this 2D inventory screen. Recreate the layout in CSS/Tailwind or Unity UI Toolkit, and write image-generation prompts for five new item icons that match its pixel-art style.

Run the web and Unity versions separately against the same reference image. Keep the reference, prompts, generated code, and screenshots of the rendered results.

Compare layout, spacing, typography, colors, and whether the UI runs. Check whether the five icon prompts consistently specify the reference's palette, pixel scale, perspective, and lighting. If those prompts are used to generate images, record the image model and settings separately so its output is not confused with Muse's visual understanding.

No tests have been run yet.

Related: [Q003 — Lawnmower sim engine comparison](../q003-lawnmower-sim-engine-comparison/question.md).
