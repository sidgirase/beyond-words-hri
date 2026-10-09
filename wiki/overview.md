---
title: Project overview
type: overview
sources: [proposal-beyond-words, dogan-2022-follow-up-clarifications, course-project-overview]
updated: 2026-09-30
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

## Current status (2026-09-30)
- Proposal submitted (due 2026-09-17).
- **No code yet.** See [[codebase/README|codebase]].
- **Environment verified** (2026-09-30): stretch_mujoco runs on this Windows machine with Python 3.11 +
  MuJoCo 3.2.6. Custom table scenes can be injected. The passive viewer works. A top-down grasp lifts
  apple-, cup- and bottle-sized objects. Key constraints: disable the lidar sensors, don't use sim cameras
  during teleop, and the client can't see object poses. See [[dev-environment]], [[stretch-3-robot]] and
  [[ambiguous-scene-design]]. How the simulator works: [[mujoco-primer]]. Unresolved items: [[open-issues]].
- Next engineering goal (requested 2026-09-29): a MuJoCo scene with Stretch 3 + table + ambiguous
  objects + bin, teleoperable to pick-and-place, with the controller swappable for a policy later, and
  later a "pick *this* object" target input. Plan to be written in `plans/`.
- Next deadline: **Check-In Day 1, 2026-10-08** — proposal promises "VLA deployment on the simulated
  robot" + chat/audio GUI + scoring metric by then. See [[timeline]].
