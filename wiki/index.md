# Wiki index

Read this first. Schema and workflows: `../AGENTS.md`. History: [[log]]. Code history: [[changelog]].

## Overview
- [[overview]] — the project on one page: question, task, method, current status.
- [[open-issues]] — numbered list (OI-1 …) of decisions and unknowns still to resolve.

## Sources
- [[proposal-beyond-words]] — team proposal: 4 clarification strategies (assume / ask / gesture / hybrid) on Stretch, sim then physical.
- [[dogan-2022-follow-up-clarifications]] — HRI 2022: targeted clarification questions beat re-description (N=63); reference ambiguous table scene.
- [[idea-analysis]] — pre-proposal idea ranking; Windows simulator risk; perception-first DV warning.
- [[course-project-overview]] — course requirements, deadlines, grading.

## Concepts
- [[clarification-strategies]] — the 2×2 IV and what each condition needs from the software.
- [[ambiguous-scene-design]] — object inventory, ambiguity levers, verified graspable sizes, rolling fix.
- [[stretch-3-robot]] — Stretch 3 + `stretch_mujoco` (verified): API, process model, actuators, custom-scene injection, limits.
- [[mujoco-primer]] — how MuJoCo and stretch_mujoco work; why our code can't see object poses; fix options A/B/C.
- [[dev-environment]] — machine specs, conda env (`environment.yml`), required Python/MuJoCo versions, performance findings and the rules that follow.
- [[study-design]] — design, IVs/DVs, instruments, what the sim must log.
- [[timeline]] — milestones, promised deliverables, rubric.

## Codebase
- [[codebase/README|codebase]] — current state of the code (none yet).

## Plans
- [[plans/README|plans]] — how plans work.
- [[plans/ik-pick-and-gesture-poc]] — DRAFT: in-process MuJoCo PoC, table + blue/green cylinders, IK-only pick-up and base-rotate/arm-half-extend gesture, as blocking functions.

## Raw sources not ingested
- `../proposal/howell.pdf` — Howell et al., IROS 2023; only supports the rejected Idea 4.
