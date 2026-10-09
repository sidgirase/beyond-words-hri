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
- [[ik-library-survey]] — which IK libraries fit MuJoCo 3.2.6 on Windows; mink 0.0.13 chosen, pitfalls.
- [[dev-environment]] — machine specs, conda env (`environment.yml`), required Python/MuJoCo versions, performance findings and the rules that follow.
- [[study-design]] — design, IVs/DVs, instruments, what the sim must log.
- [[timeline]] — milestones, promised deliverables, rubric.

## Codebase
- [[codebase/README|codebase]] — current state of the code: `hri_sim` package and scripts (IK-driven pick and gesture PoC).
- [[codebase/architecture]] — layers, modules, scene, how a skill call flows.
- [[codebase/ik-and-motion]] — mink IK setup, motion executor, pose rules, geometry.
- [[codebase/skills-api]] — `gesture`, `pick`, results, failure reasons, window and episode end.
- [[codebase/how-to-run]] — environment, demos, checks and their results, tuning.

## Plans
- [[plans/README|plans]] — how plans work.
- [[plans/ik-pick-and-gesture-poc]] — IMPLEMENTED 2026-10-09: design record and evidence for the IK-driven pick and gesture PoC (code in [[codebase/README|codebase]]).

## Logs
- [[logs/ik-pick-and-gesture-poc-progress]] — timestamped progress log of the PoC implementation.

## Raw sources not ingested
- `../proposal/howell.pdf` — Howell et al., IROS 2023; only supports the rejected Idea 4.
