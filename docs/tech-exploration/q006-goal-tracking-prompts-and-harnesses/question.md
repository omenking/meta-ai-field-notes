---
question: Does Muse with the same prompt perform differently when used in different coding harnesses?
date: 2026-10-27
status: unexplored
scope:
  - muse-wonder
  - system-prompting
  - agent-harnesses
  - long-running-coding-tasks
---

## Observation

A community member observed that Muse can become increasingly focused on the immediate subtask during longer coding sessions. Each step may appear productive, yet the work gradually narrows around recent changes rather than returning to the user's broader goal. The result can be a locally improved implementation that stops short of fulfilling the original request.

In their experience, Codex and Claude more often pause to reassess what remains and adjust their next steps against the overall objective. They reported a similar difficulty with Argon despite finding it strong at gathering and synthesizing information. This raises a useful distinction to investigate: having the knowledge to solve individual problems may not be enough to sustain progress toward a larger outcome.

The central question is whether a deliberate goal-review loop can address this behavior through prompting or harness design. These observations are anecdotal; the exact model versions, harnesses, and tasks were not supplied, and the comparison has not been independently tested.

## What to explore

Can explicit goal reviews prevent the agent from repeatedly optimizing the most recent subtask while leaving the original request incomplete? How much improvement comes from system instructions alone, and how much requires the harness to preserve the goal and trigger reviews?

## Proposed test

Since Muse can be loaded into other coding harensses we should test Muse in:
- Claude Code
- Codex
- Cursor
- OpenCode
- Muse Code
The same prompt