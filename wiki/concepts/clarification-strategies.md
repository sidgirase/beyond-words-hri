---
title: Clarification strategies (the four conditions)
type: concept
sources: [proposal-beyond-words, dogan-2022-follow-up-clarifications]
updated: 2026-09-29
---

# Clarification strategies

The independent variable of the study ([[study-design]]). A 2×2 of *voice* × *gesture*
([[proposal-beyond-words]], Table 1):

|              | No gesture | Gesture |
|---|---|---|
| **No voice** | 1. Immediate action | 3. Arm gesture |
| **Voice**    | 2. Ask for clarification | 4. Hybrid ask-and-gesture |

1. **Immediate action** — robot picks its best hypothesis and executes (the "assume" baseline).
2. **Ask** — verbal question; user must answer. [[dogan-2022-follow-up-clarifications]] suggests
   *targeted* questions (spatial relation to a known object) beat "please describe it again".
3. **Arm gesture** — robot leans/reaches toward the hypothesized target and **pauses**; user nudges it
   on or corrects it. Motivated by legibility (Dragan et al. 2013).
4. **Hybrid** — 2 and 3 at the same time.

In 2–4 the robot waits for the human's response before acting.

## What this demands from the software
- A **target hypothesis** (ranked candidate objects) separate from the motion controller.
- Motion primitives beyond pick/place: `reach_toward(target)` + `pause/hold` for conditions 3–4.
- A response channel (speech or chat) and a way to "nudge/correct".
- Timestamped logging of each turn for the DVs.

## Open questions
- How does a user "nudge" a gesture in practice — keyboard/GUI confirm, or physical push on the real
  robot? Not specified in the proposal.
- What question generator is used in condition 2 — template-based spatial questions like Dogan et al.,
  or an LLM/VLA (Ask-to-Clarify)?
