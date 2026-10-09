---
title: IK-driven pick-up and gesture proof of concept (in-process MuJoCo)
type: plan
sources: [mujoco-primer, stretch-3-robot, dev-environment, ambiguous-scene-design, clarification-strategies, open-issues]
updated: 2026-10-09
status: draft
---

# Plan: IK-driven pick-up and gesture proof of concept

Requested 2026-10-09. **Status: draft, waiting for approval. No code has been written.**

## 1. Goal
A small, fast MuJoCo simulation of a Stretch 3 next to a table with two cylinders (blue, green), driven
by **inverse kinematics only**, with no camera rendering and no VLA in the loop, so the only compute
latency in a motion is the IK solve. It must support:

1. **Pick up** either cylinder (verified separately for blue and for green).
2. **Gesture** toward either cylinder: rotate the mobile base until the telescoping arm points at it,
   extend the arm about half way, and pause. This is the "reach-and-pause" intent signal of
   condition 3 in [[clarification-strategies]].
3. **Combinations** in one episode: gesture then pick the other cylinder, gesture then pick the same one,
   and so on.
4. All of the above exposed as **plain blocking Python functions**, so a script now and a GUI later can
   drive the robot through the same calls.

Out of scope: bin and placing ([[open-issues]] OI-10), ambiguous object sets, teleop input, policies,
speech, user-study logging.

## 2. Context
- Architecture is **option B** of [[mujoco-primer]] §4: load the stretch_mujoco model files, build the
  scene with `MjSpec`, run our own `mj_step` loop in one process. This gives direct access to `MjData`
  (object poses, contacts, resets) and avoids the IPC and free-running physics of the stock server.
  Would resolve [[open-issues]] OI-1 (confirm this is the choice) and OI-11 (base motion in-process).
- Performance rules from [[dev-environment]] apply: Python 3.11, `mujoco==3.2.6`, **sensor stage disabled**
  (the 360 lidar rays cost ~10 ms/step), **no sim cameras**. Stepping then costs 0.15–0.3 ms.
- Robot facts from [[stretch-3-robot]]: arm extends toward −y at home, `link_grasp_center` sits at about
  (0.03, −0.61) with arm 0.5 and wrist pitch −1.57, actuator ranges, default table top at z = 0.48.
- Grasp recipe already verified in raw MuJoCo ([[ambiguous-scene-design]], Graspability): wrist pitch −1.57,
  lower the lift until the grasp centre reaches the object, close, lift. A cylinder of r = 3.5 cm and
  h = 9 cm (mass 0.1 kg, `condim=6`, friction `1.0 0.01 0.002`) was lifted about 21 cm.

## 3. Design

### 3.1 Layers
```
 script / future GUI
        │   gesture("blue"), pick("green"), release(), go_home(), abort()
        ▼
 skills.py     high-level skills; each returns a SkillResult (ok, reason, timings)
        │   Cartesian goals  (grasp-centre position, wrist pitch)
        ▼
 ik.py         damped least squares on a scratch MjData → joint targets (yaw, lift, arm, wrist)
        │   joint targets
        ▼
 robot.py      motion executor: rate-limited targets into data.ctrl, wheel P-control for yaw,
        │      gripper open/close, wait-until-settled
        ▼
 sim.py        owns MjModel + MjData, steps physics, syncs the passive viewer, reset(), object poses
        ▲
 scene.py      builds the model: stretch + floor + table + two cylinders (MjSpec)
```
Everything is synchronous. A skill call returns when the motion is finished (or failed or aborted). The
viewer is synced from inside the step loop, so the window stays alive while a skill runs.

### 3.2 Scene (`scene.py`)
World frame: robot rotation centre at the origin, facing +x, arm toward −y. All numbers below are
**initial values to be tuned in M1/M2**, and all live in `SceneConfig`.

| Item | Initial value | Reason |
|---|---|---|
| Table | box, half-size 0.6 × 0.5 × 0.24, top at z = 0.48, centre (0, −0.80), so its near edge is at y = −0.30 | same table height as the default scene; edge ≥ 0.12 m beyond the base footprint so the base can spin freely **(unverified footprint)** |
| Cylinders | radius 0.035, height 0.10, mass 0.1, `condim=6`, friction `1.0 0.01 0.002`; colours blue `0 0 1 1` and green `0 0.7 0 1`; names `cyl_blue`, `cyl_green`; free joint | within the verified graspable range (cup 9 cm, bottle 20 cm), above the 7 cm rule |
| Cylinder positions | radius 0.48 m from the rotation centre, at ±25° from the −y direction (about 0.20 m left and right of the centreline, 0.435 m out), about 0.39 m apart | see reach calculation below; 0.39 m apart keeps the open gripper off the neighbour and makes the two gestures visibly different |
| Robot start | `home` keyframe at the origin, yaw 0, no translation | PoC never drives the base forward |
| Floor, light | plain floor plus one light | |

**Reach calculation (from the wiki's measured numbers, to be re-measured in M2).** With wrist pitch
−1.57 the grasp centre is at radial distance about 0.61 m when arm = 0.5, so about 0.11 m at arm = 0 and at
most about 0.63 m at the full 0.52 m. A cylinder at 0.48 m therefore needs arm ≈ 0.37 m (71 % of travel).
That leaves **≈ 0.15 m of leeway outward** (cylinder could be 0.15 m farther and still be reachable) and
≈ 0.37 m inward. Farther is better for gesture legibility (more visible half-extension), nearer is safer;
0.48 m is the compromise. The perturbation sweep in M3 measures the real leeway.

The scene is built from stretch_mujoco's model files. Two ways, decided at implementation time
**(unverified which works)**: (a) load `stretch.xml` only and add floor, light, table and cylinders; (b) load
`scene.xml` and remove its table, `object1`, `object2` and docking station. Then set
`model.opt.disableflags |= mjDSBL_SENSOR`.

### 3.3 Inverse kinematics (`ik.py`)
- **Method:** damped least squares (Levenberg–Marquardt) on a private scratch `MjData` that is copied from
  the live one. Forward kinematics only (`mj_kinematics`), never `mj_step`, so it is cheap and cannot
  disturb the simulation. Jacobian by finite differences over the few active DOFs (3 to 4 FK calls per
  iteration), which avoids the tendon-coupling bookkeeping of an analytic Jacobian.
- **Reduced coordinates:** `q = [base_yaw, lift, arm, wrist_yaw, wrist_pitch, wrist_roll]`.
  `base_yaw` is applied by writing the base free-joint quaternion (the base rotates in place, so its x, y
  stay fixed). `arm` is one DOF: the four telescoping joints `joint_arm_l0..l3` are each set to `arm / 4`
  **(unverified: assumes the tendon splits the extension equally; check against the model's tendon and
  equality constraints in M1)**.
- **Per-call configuration:** which DOFs are active, which are fixed, and the target. Joint limits are
  clamped from `model.jnt_range`. Tolerance 1 mm, at most 100 iterations, seeded from the current pose.
- **Targets used in this plan**
  - Pick: grasp-centre position = cylinder x, y and z = table top + 0.06, wrist pitch fixed at −1.57,
    active DOFs `yaw, lift, arm` (3 unknowns, 3 equations, so it is well posed). The yaw solution
    automatically absorbs the ~0.03 m lateral offset of the arm axis from the rotation centre
    (about 3.6° at 0.48 m), so "arm points at the cylinder" is exact rather than approximate.
  - Gesture lift: one-DOF solve for `lift` with yaw and arm fixed, pitch = gesture pitch.
- **Latency accounting:** every solve records iterations, residual and wall time (`time.perf_counter`) in an
  `IKStat`. Skills return them, so "the only latency is IK" is a measured number, not a claim. I expect
  single-digit milliseconds in Python **(unverified, measured in M2)**.
- **No new dependency.** numpy ships with mujoco. A library such as `mink` or `ikpy` is possible but not
  needed for 3 to 4 DOFs.

### 3.4 Motion execution (`robot.py`)
- Lift, arm, wrist and gripper are position servos ([[stretch-3-robot]]). The executor moves the target
  toward the IK solution at a per-joint speed limit (initial values: lift 0.15 m/s, arm 0.15 m/s,
  wrist 0.8 rad/s, gripper 0.05 m/s, all tunable) and steps physics until every joint is within tolerance
  of its target or a timeout expires. Rate limiting avoids violently yanking a 0.1 kg object loose.
- **Base yaw:** wheel velocity actuators `left_wheel_vel` / `right_wheel_vel` driven with opposite signs by
  a P controller on yaw error, read from the base free joint. A feedback loop needs no wheel radius or
  track width, only the sign convention. Yaw tolerance 0.5°, with a speed cap and a timeout.
  **Fallback** if wheel spinning is unreliable on Windows physics (config `base_mode`): `"kinematic"` writes
  the base yaw into `qpos` along a smooth ramp. Less physical, still deterministic and IK-driven.
- **Safe rotation rule:** before any yaw change larger than a small threshold, raise the lift above
  table + cylinder height (plus margin) and retract the arm to about 0 so a swinging arm cannot sweep a
  cylinder off the table. Skills call this `_clear_to_rotate()`. It is what makes combinations like
  "gesture at blue, then pick green" safe.
- Pacing: `realtime=True` sleeps so wall time follows sim time (for demos with the viewer); `False` runs flat
  out (tests). `headless=True` skips the viewer.
- `abort()` sets a `threading.Event` checked every control tick, so a future GUI can cancel a motion.

### 3.5 Skills (`skills.py`), the public API
```python
from hri_sim import StretchSim, SceneConfig, Skills

sim = StretchSim(SceneConfig(), headless=False, realtime=True)
sim.reset(seed=0)
skills = Skills(sim)

skills.gesture("blue", fraction=0.5, hold_s=2.0)   # SkillResult
skills.pick("green")                                # SkillResult
skills.release()                                    # puts the held cylinder back down where it was picked
skills.go_home()                                    # clear, retract, yaw back to 0, gripper closed
sim.close()
```
| Skill | Steps |
|---|---|
| `pick(color)` | clear-to-rotate → IK for the pick pose → yaw to target → lift/arm to a pre-grasp 0.10 m above the grasp height, pitch −1.57, gripper open → descend → close until both fingers touch the cylinder → lift 0.15 m → check |
| `gesture(color, fraction=0.5, hold_s=2.0)` | clear-to-rotate → yaw so the arm axis points at the cylinder (yaw from the pick IK) → set wrist pitch to the gesture pitch (default 0) → lift to the height where the grasp centre is level with the cylinder centre → extend arm to `fraction × arm_pick` → hold `hold_s` seconds. Leaves the robot in the pointing pose; the caller decides what comes next |
| `release()` | lower to the original grasp height, open the gripper, back off, clear |
| `go_home()` | clear-to-rotate, retract, yaw 0 |
| `abort()` | cancel the running skill and zero the wheels |

- `SkillResult` fields: `ok`, `skill`, `target`, `reason` (empty on success, otherwise one of
  `unreachable`, `ik_failed`, `no_grasp`, `dropped`, `timeout`, `aborted`), `sim_time`, `wall_time`, `ik`
  (list of `IKStat`). A skill never raises on a task failure; it returns `ok=False`.
- Colour names are validated against `sim.objects`, so adding more objects later is a config change.
- Read-only helpers for the GUI and tests: `sim.object_position(color)`, `sim.held_object()`,
  `sim.robot_state()` (joint values plus base yaw), `sim.time`.
- **Pick success** (all must hold): both fingers in contact with the cylinder at the top of the lift; the
  cylinder rose at least 0.10 m above its rest height and stays there, within 0.05 m laterally of the grasp
  centre, for 1 s of sim time.

### 3.6 Interfaces later work will rely on
Skills are the single place where "robot intent" is expressed. A GUI button, a scripted study condition
or a VLA wrapper all call `gesture` and `pick`. That matches the later need for the clarification
conditions (gesture, then wait, then pick) without committing to a policy interface yet ([[open-issues]] OI-15).

## 4. File-by-file changes
All new; nothing existing in `src/` is code. Package name `hri_sim` is an assumption.

| Path | Contents |
|---|---|
| `src/hri_sim/__init__.py` | exports `StretchSim`, `SceneConfig`, `Skills`, `SkillResult` |
| `src/hri_sim/config.py` | dataclasses `SceneConfig` (table, cylinders, layout), `MotionConfig` (speed limits, tolerances, timeouts, `base_mode`), `SkillConfig` (pick height offsets, lift height, gesture fraction, pitch, hold) |
| `src/hri_sim/scene.py` | `build_model(cfg)`: MjSpec scene as in 3.2, sensors disabled |
| `src/hri_sim/sim.py` | `StretchSim`: model/data, `reset(seed)`, `step()`, passive viewer, pacing, object pose and contact queries, `abort` event |
| `src/hri_sim/ik.py` | `IKSolver`, `IKStat` |
| `src/hri_sim/robot.py` | actuator and joint id lookup, rate-limited joint motion, wheel yaw controller, gripper helpers |
| `src/hri_sim/skills.py` | `Skills`, `SkillResult` |
| `src/scripts/demo.py` | viewer demo running a chosen sequence, e.g. `python scripts/demo.py gesture:blue pick:green` |
| `src/scripts/check_scene.py` `check_ik.py` `check_pick.py` `check_gesture.py` `check_sequences.py` | verification scripts for M1 to M5 (plain Python with asserts, a pass or fail table and exit code; no pytest, so no new dependency) |
| `src/environment.yml` | **no change expected**. If M1 shows the viewer needs more packages, add them and tell the human to run `conda env update -f environment.yml --prune` |

On implementation the wiki gets: `codebase/` pages (architecture, IK, skills API, how to run), a changelog
entry, and updated [[open-issues]] (OI-1, OI-10 partly, OI-11 resolved or narrowed), per `AGENTS.md`.

## 5. Milestones and verification
Run everything in the `hri_stretch` conda env. **M0 is the human's step.**

| # | Milestone | Verification (pass criteria) |
|---|---|---|
| M0 | Conda env built ([[open-issues]] OI-8) | `python -c "import mujoco, stretch_mujoco; print(mujoco.__version__)"` prints 3.2.6 |
| M1 | Scene + sim loop + viewer | Window opens on Windows with `launch_passive` **(unverified in our own process)**; 10 s of sim with the arm idle: cylinders move less than 2 mm, base drifts less than 5 mm; real-time factor logged (target at least 0.5× with the viewer; much more headless); no robot-table contact when yaw is swept ±40° at the safe pose; arm tendon coupling checked against the model |
| M2 | IK + executor, no grasping | IK for both pre-grasp positions converges in under 100 iterations to under 1 mm; after executing, the live `link_grasp_center` is within 5 mm of the target; wheel yaw reaches target within 0.5° in both directions; IK wall times recorded and reported |
| M3 | Pick, each colour in its own run | `check_pick.py` runs blue-only and green-only from `reset`. Pass: pick success per 3.5. Then a sweep of 20 trials per colour with the cylinder offset randomly by up to ±2 cm in x and y (seeded), then radial offsets of ±5, ±10, ±15 cm, to measure the real leeway. Report success rate. Gate to M4: 100 % at nominal, at least 90 % within ±2 cm |
| M4 | Gesture, each colour | After `gesture`: angle between the arm axis and the line to the cylinder is within 3°; arm extension is `fraction × arm_pick` within 1 cm; no cylinder moved more than 5 mm; no robot-object contact; yaw for blue and green differs by about 50° (the layout angle); result has `ok=True`. Plus a look in the viewer to judge whether it reads as pointing |
| M5 | Combinations | `check_sequences.py` runs each from a fresh `reset`: gesture(blue) → pick(green); gesture(green) → pick(blue); gesture(blue) → pick(blue); gesture(green) → pick(green); gesture(blue) → gesture(green) → pick(green); pick(blue) → release → pick(green); pick(green) → release → gesture(blue). Pass: every skill `ok`, no unintended cylinder displacement during gestures, final held object is the intended one |
| M6 | API polish | Skills callable from a plain script and from a worker thread (abort works mid-motion); `demo.py` runs a sequence end to end; docs written to `codebase/` |

## 6. Assumptions I made (please confirm or correct)
1. **Architecture B**, in one process, with the passive viewer ([[mujoco-primer]] §4 leaning).
2. **The base only rotates in place.** The robot is placed once and never translates, so the PoC needs no
   base navigation. The table and cylinders are laid out around it.
3. **Cylinders:** r = 3.5 cm, h = 10 cm, 0.1 kg; blue and green; fixed positions (seed only changes optional
   jitter). Chosen from the verified grasp sizes, not tested at exactly 10 cm yet.
4. **Top-down grasp** with wrist pitch −1.57 and the gripper straddling the cylinder, reusing the verified recipe.
5. **"Half way" means** half of the arm extension needed to grasp that cylinder (`fraction = 0.5`, a parameter),
   with the arm axis aimed exactly at the cylinder. It is not half of the arm's full travel and not half the
   distance of the fingertip.
6. **Gesture posture:** wrist pitch 0 (gripper in line with the arm so it reads as pointing), gripper closed,
   lift set so the arm points horizontally at the cylinder's centre height. Pitch 0 meaning "in line" is
   **(unverified)**.
7. **After a pick the robot holds the cylinder** 15 cm up. `release()` sets it back where it was; there is
   no bin in this PoC.
8. **Skills are blocking** and run on the caller's thread. GUI use will be a worker thread plus `abort()`.
9. **Own damped least squares IK**, no external IK library, no extra dependency.
10. **Sensors off and no cameras**, per [[dev-environment]]. Nothing renders offscreen.
11. All geometry and speed numbers are **initial placeholders** derived from the wiki's measurements and are
    tuned during M1 and M2.
12. Package `hri_sim` in `src/`, scripts in `src/scripts/`, verification as plain scripts rather than pytest.

## 7. Open questions
1. **Half way:** is "fraction of the extension needed for the grasp" the right definition, or should it be
   half of the arm's full range, or the fingertip halfway along the straight line to the cylinder? With the
   wrist at pitch 0 the gripper tip will land farther out than the arm extension alone suggests.
2. **Gesture posture:** pointing with a straight, closed gripper (my assumption) versus keeping the
   top-down pick posture versus an open gripper. Which will read best to a participant? Easy to change
   later (one parameter), but it affects what you see in the first demo.
3. **Does the gesture include the lift height** matching the cylinder, or should the arm stay at a fixed
   height for all objects (a purer test of the yaw cue)?
4. **After pick:** hold-and-release (assumed) or something else, such as carry to a fixed drop spot? A bin
   is deferred; say if you want it in this PoC.
5. **Layout:** which colour goes left or right, 0.48 m radius and ±25° are my picks. Do you want them
   randomly swapped per `reset`?
6. **Pacing default:** real-time demos with the viewer (assumed) or as fast as possible?
7. **GUI toolkit** you have in mind (Tkinter, a web page, pygame)? Not needed now, but a separate process
   would call for a different boundary than "same-process blocking functions".
8. **Wheel physics fallback:** are you fine with the `kinematic` yaw fallback if the wheel P-control proves
   unreliable on this machine?
9. **Is it a problem that the held cylinder is not placed anywhere,** given that the proposal's task ends
   in a bin ([[proposal-beyond-words]])? This PoC deliberately stops at the lift.

## 8. Risks
- **Model details unconfirmed:** joint and body names, arm tendon split, wheel sign convention, finger
  closing axis versus the arm axis, `stretch.xml` standalone loading. Mitigation: M1 inspects the model
  before anything else is built on it.
- **Base spin physics in-process** ([[open-issues]] OI-11) is untested; the `kinematic` fallback covers it.
- **Viewer in our own process on Windows** is unverified (the passive viewer was only tested inside
  stretch_mujoco's server process). Fallback: headless run plus saved frames, or the viewer in a
  separate thread.
- **Gesture reads poorly** with only about 0.18 m of extension; the cure is a layout farther out or a
  different `fraction`/posture, all parameters.
- **Short objects:** the 10 cm cylinder sits between the verified 9 cm and 20 cm cases, so M3 is a real test,
  not a formality ([[open-issues]] OI-9 does not apply, since 10 cm is above the 7 cm rule).
