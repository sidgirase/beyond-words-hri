---
title: Project overview
type: overview
sources: [proposal-beyond-words, dogan-2022-follow-up-clarifications, course-project-overview]
updated: 2026-10-09
---

# Beyond Words — project overview

**Title:** *Beyond Words: Evaluating Verbal and Gestural Clarification Strategies During Ambiguous Robot
Instructions* — Om Shivam Verma, Rena Nakashima, Siddhesh Girase (CS 7633, Fall 2026).
Source: [[proposal-beyond-words]].

## Research question
How do robot clarification strategies affect **task success rate, completion time, frustration, trust
and perceived competence** when a person gives an ambiguous pick-up instruction?

Hypothesis: a reach-pause-and-gesture confirmation (optionally combined with speech) is seen as more
efficient and human-like than the alternatives. See [[clarification-strategies]].

## The task
A person asks a Stretch robot to pick an object from a table cluttered with look-alike objects and put
it in a bin/basket. The robot only knows what the person communicates. This mirrors the table setups of
[[dogan-2022-follow-up-clarifications]] (where the participant put each described object in a basket).
Scene design: [[ambiguous-scene-design]].

## Method in one line
Build in simulation (Hello Robot's `stretch_mujoco`, [[stretch-3-robot]]), then move to a physical
Stretch 2/3 for the actual user study; 4 clarification conditions; factorial design. See [[study-design]].

## Current status (2026-10-09)
- Proposal submitted (due 2026-09-17).
- **First code exists:** `src/hri_sim/` is a simulation of a Stretch 3 next to a table with a blue and a green
  cylinder, driven by inverse kinematics (mink) through two blocking skills: `gesture` (turn the base toward a cylinder
  while closing the gripper, extend the arm over it, lower the lift halfway, pause) and `pick` (top-down
  grasp and lift; the simulation then freezes on the last frame). Combinations of the two work. See
  [[codebase/README|codebase]], [[codebase/how-to-run]] and the progress log
  [[logs/ik-pick-and-gesture-poc-progress]].
- **Environment:** verified with a throwaway uv environment (Python 3.11, MuJoCo 3.2.6, mink 0.0.13); the conda
  env `hri_stretch` still has to be updated by the human ([[open-issues]] OI-8). Constraints in
  [[dev-environment]], [[stretch-3-robot]], [[ambiguous-scene-design]]; how the simulator works:
  [[mujoco-primer]].
- **Next for the user:** run `python scripts/demo_gesture_variants.py` and choose how far the lift goes down in the
  gesture (OI-19); `python scripts/demo.py ... --record` saves a video to `src/outputs/`.
- Not built yet: bin and placing, ambiguous object sets, a GUI, teleop, a policy or VLA, speech, study logging.
- Next deadline: **Check-In Day 1, 2026-10-08** has passed; the proposal promised "VLA deployment on the
  simulated robot" + chat/audio GUI + scoring metric. See [[timeline]].
