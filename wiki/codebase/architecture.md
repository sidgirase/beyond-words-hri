---
title: Architecture of hri_sim
type: codebase
sources: [hri_sim/config.py, hri_sim/scene.py, hri_sim/sim.py, hri_sim/ik.py, hri_sim/robot.py, hri_sim/skills.py]
updated: 2026-10-09
---

# Architecture of `hri_sim`

One Python process, no IPC. MuJoCo is run in-process (option B of [[mujoco-primer]]), so object poses,
contacts and resets are directly readable. Only `mujoco`, `numpy` and `mink` are imported by the package;
`stretch_mujoco` is not imported, only its model file is loaded.

## Layers
```
 script
   │   gesture("blue"), pick("green"), hold_final_frame(), close_window(), abort()
   ▼
 skills.py     Skills: gesture, pick; returns SkillResult
   │   grasp-centre positions
   ▼
 ik.py         IKSolver (mink): (yaw, lift, arm) for a position of link_grasp_center
   │   joint targets
   ▼
 robot.py      Robot: rate-limited joint moves, wheel yaw controller that moves joints during the turn
   │   ctrl values, step calls
   ▼
 sim.py        StretchSim: model, data, stepping, pacing, viewer, contact monitor, freeze
   ▲
 scene.py      build_model: stretch.xml + floor + table + cylinders, sensors disabled
 config.py     SceneConfig, MotionConfig, SkillConfig (every tunable number)
```

## Modules
| Module | What it holds |
|---|---|
| `config.py` | Three dataclasses. `SceneConfig` (model path, table, cylinders, layout), `MotionConfig` (carry pose, joint speeds, settle and trim rules, yaw controller gains, pacing), `SkillConfig` (grasp and pre-grasp heights, lift after grasp, gesture fraction and minimum clearance, "already in place" tolerances, IK tolerances); `OUTPUTS_DIR` (`src/outputs`). |
| `scene.py` | `build_model(cfg)` loads `stretch.xml` with `MjSpec`, adds floor, light, table and cylinders, compiles, ORs `mjDSBL_SENSOR` into `opt.disableflags` (lidar off). `cylinder_home_xy`. |
| `sim.py` | `StretchSim`. Owns `MjModel` and `MjData`; `reset()` writes the carry pose; `step(n)` runs physics, syncs the viewer every 8 steps, paces to wall-clock time, checks the abort flag and records contact violations; `freeze()`; `hold_final_frame()`; `close_window()`; read-only queries (`object_position`, `base_pose`, `joint`, `grasp_center`, `fingers_touching`, `ik_state`); an event log of moves for the checks. `SkillInterrupt` is the control-flow exception (reasons aborted, window_closed, timeout). |
| `ik.py` | `IKSolver` wraps mink on a private copy of the robot model. `IKResult`, `IKStat`. Details in [[codebase/ik-and-motion]]. |
| `robot.py` | `Robot`: `move(targets)`, `turn_to(yaw, joints)` (the gripper can close or open during the turn), `stop_wheels()`, `at_carry_height()`. |
| `skills.py` | `Skills` and `SkillResult`; `_turn` (lift to carry height, then turn) and the skip-if-already-in-place rules. Details in [[codebase/skills-api]]. |
| `recorder.py` | `VideoRecorder`: offscreen rendering with the viewer's camera every 1/fps of sim time into an mp4 (optional, needs imageio); hooked into `StretchSim.step` through `sim.recorder`. |

## Scene (defaults in `SceneConfig`)
World frame: the robot's rotation centre (the midpoint of its wheel axle) is the origin, facing +x; the arm
extends toward -y, toward the table.

| Item | Value |
|---|---|
| Table | box 1.2 x 1.0 x 0.48 m, top at z = 0.48, near edge 0.36 m from the origin along -y |
| Cylinders | radius 0.035, height 0.10, mass 0.1 kg, `condim=6`, friction 1.0 0.01 0.002; blue at (-0.228, -0.489), green at (+0.228, -0.489), 0.54 m from the origin, 25 degrees either side of the -y axis |
| Robot start | the carry pose (lift 0.80, arm in, gripper open), wrist pitched down to -1.57 and never moved again, yaw 0 |
| Physics | timestep 0.002 s, about 0.05 ms per step, about 33 times real time unpaced |

## How a skill call flows
1. `Skills._run` validates the target colour, the episode state and the window, clears the abort flag, and
   remembers the contact-violation counts.
2. The skill body asks IK for yaw, lift and arm, checks the residual, then issues moves through `Robot`.
3. Every `Robot` move steps `StretchSim`, which steps MuJoCo, syncs and paces. An abort or a closed window
   raises `SkillInterrupt`, which `_run` turns into a result with that reason.
4. New contact violations during the skill turn a success into `collision`.
5. A successful pick calls `sim.freeze()`: stepping becomes a no-op and `episode_over` is set.

## What was reused from stretch_mujoco
Only `stretch_mujoco/models/stretch.xml` and its mesh assets, read through the git submodule at
`src/stretch_mujoco/` (commit `c78d6a1`). Its server, client, base controller and URDF kinematics are not
used. See [[stretch-3-robot]] for what the model contains.
