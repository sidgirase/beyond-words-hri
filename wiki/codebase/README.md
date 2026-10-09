---
title: Codebase (current state)
type: codebase
sources: [hri_sim package, scripts, plans/ik-pick-and-gesture-poc]
updated: 2026-10-09
---

# Codebase

Describes the code **as it exists now**. Must never drift from `src/`.

**Status 2026-10-09:** the first plan is implemented. `src/hri_sim/` is a small MuJoCo simulation of a
Stretch 3 next to a table with a blue and a green cylinder, driven by inverse kinematics (the third-party
library mink) through two blocking skills, `gesture` and `pick`. The gripper hangs down the whole time. A
successful pick freezes the simulation on the last frame; `demo.py --record` saves a video. It was verified with the check scripts in a throwaway uv environment
(Python 3.11, `mujoco==3.2.6`, `mink==0.0.13`); the conda environment `hri_stretch` has not been rebuilt
with mink yet, and not every check script was re-run after the last edits; see [[codebase/how-to-run]].

## Pages
- [[codebase/architecture]] — layers, modules, scene layout, how a skill call flows.
- [[codebase/ik-and-motion]] — mink setup, the motion executor, pose rules, speeds, why each exists.
- [[codebase/skills-api]] — `gesture`, `pick`, results, failure reasons, episode end, window functions.
- [[codebase/how-to-run]] — environment, demos, the viewing session, checks, tuning.

## Layout of `src/`
```
src/
  hri_sim/            the package (config, scene, sim, ik, robot, skills, recorder)
  scripts/            demos and check scripts (run from src with python scripts/NAME.py)
  outputs/            videos from demo.py --record (created on first use, git-ignored)
  stretch_mujoco/     git submodule: only its model files are used (models/stretch.xml)
  environment.yml     conda env hri_stretch (now with mink==0.0.13)
  wiki/               this wiki
```

Design history and evidence: [[plans/ik-pick-and-gesture-poc]] (status implemented) and the progress log
[[logs/ik-pick-and-gesture-poc-progress]]. Library choice: [[ik-library-survey]].
