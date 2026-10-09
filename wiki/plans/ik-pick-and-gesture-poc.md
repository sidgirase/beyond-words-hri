---
title: IK-driven pick-up and gesture proof of concept (in-process MuJoCo)
type: plan
sources: [mujoco-primer, stretch-3-robot, dev-environment, ambiguous-scene-design, clarification-strategies, open-issues, stretch_mujoco submodule @ c78d6a1]
updated: 2026-10-09
status: implemented
---

# Plan: IK-driven pick-up and gesture proof of concept

Requested 2026-10-09, revised the same day after reading the stretch_mujoco submodule, running a throwaway
prototype, surveying IK libraries and getting the user's answers to the open questions. **Status: implemented on 2026-10-09** (approved the same day). The code is described in [[codebase/README|codebase]] and the progress is in [[logs/ik-pick-and-gesture-poc-progress]]. This page is kept as the design record and evidence; **where it differs from the codebase pages, the codebase pages are right.** The one open item (the final gesture depth) is [[open-issues]] OI-19.

**Superseded in part (2026-10-09, after implementation):** the gesture was redesigned at the user's request. The wrist now stays pitched down at -1.57 at all times, so the straight-gripper sections of this page (gesture design 3.4 to 3.6, the "two safe poses" rule, the wrist-swing milestones and the `gripper` option) describe the first version only. The gesture is now: turn toward the object while closing the gripper, extend the arm over it, lower the lift halfway (fraction 0.5); the base turns whenever the lift is at carry height, with the arm left extended; a pick at the same object just opens the gripper. See [[codebase/skills-api]] and [[codebase/ik-and-motion]].

## 1. Goal
A small, fast MuJoCo simulation of a Stretch 3 next to a table with two cylinders (blue, green), driven
by **inverse kinematics only**, with no camera rendering and no VLA in the loop, so the only compute
latency in a motion is the IK solve. It must support:

1. **Pick up** either cylinder (verified separately for blue and for green). A successful pick **ends the
   episode**: the simulation stops with the cylinder lifted, the last frame stays visible in the viewer, and
   a skill function closes the window.
2. **Gesture** toward either cylinder, in this order: rotate the mobile base until the telescoping arm points
   at it; swing the gripper from hanging down to **straight** and close it (together); lower the lift; finally
   extend the arm a fraction of the way to the grasp pose; and pause. This is the "reach-and-pause" intent signal of condition 3 in
   [[clarification-strategies]].
3. **Combinations** in one episode: gesture then pick the other cylinder, gesture then pick the same one,
   two gestures then a pick, and so on. The pick is always the last step.
4. All of the above exposed as **plain blocking Python functions**, so scripts (and a GUI later, in a
   separate plan) drive the robot through the same calls.

Out of scope: bin, placing and releasing ([[open-issues]] OI-10), ambiguous object sets, teleop input,
policies, speech, user-study logging, any GUI (web or otherwise; to be planned later).

## 2. Context and evidence

### 2.1 What the submodule is
`src/stretch_mujoco/` is a git submodule of hello-robot/stretch_mujoco (`.gitmodules`), at commit
`c78d6a1`. That is one README-only commit after `d107e09`, the commit pinned in `environment.yml`, so
**the code and models are identical** to what [[stretch-3-robot]] describes. For this PoC we need only the
model files, so the plan loads `src/stretch_mujoco/stretch_mujoco/models/stretch.xml` by path and needs
**no `import stretch_mujoco`**. The conda environment still lists the package, which does no harm; our code
depends on `mujoco`, `numpy` and `mink`.

### 2.2 Facts read from the source (stretch.xml, utils.py, config.py, mujoco_server.py)
- The base is a free joint on `base_link`. The wheel joints sit at y = ±0.17035, wheel radius 0.05, and
  **the wheel axle midpoint is the `base_link` origin**, so a pure wheel spin rotates the robot about the
  origin. A frictionless caster sphere (r = 0.02) sits at x = −0.24.
- Wheel actuators are `velocity` type with `gear=3`, `ctrlrange ±6`. **The control value is 3 times the
  wheel joint speed.** stretch_mujoco's own rotate command (1.0 rad/s through
  `diff_drive_inv_kinematics`, using wheel separation 0.3153 from `config.py`, the real robot's value)
  therefore turns the base at only about 0.3 rad/s. The MJCF track is 0.3407, so even that number is
  slightly off. A feedback controller on measured yaw avoids depending on either constant.
- The arm is one DOF in practice: `joint_arm_l0..l3`, each range 0 … 0.13, tied together by `equality`
  joint constraints (l0 = l1 = l2 = l3), driven by a fixed tendon `extend` (all coefficients 1) with
  actuator `arm` range 0 … 0.52. So `arm / 4` per joint is correct.
- Position servos only: lift `gainprm 400, biasprm 0 -200 -100`, arm `150 / 0 -100 -10`,
  gripper `kp 4000`, wrist pitch `kp 50`. Keyframes `home` (lift 0.6, arm 0.1) and `stow` are
  **ctrl-only**: `mujoco_server.py` copies the keyframe's `ctrl` and does not touch `qpos`.
- `scene.xml` includes `docking_station.xml`, a wooden table at (0, −1, 0.24), and two free bodies
  `object1`, `object2`. We do not use it; we build our own scene from `stretch.xml`.
- `get_ee_pose` and `get_link_pose` use `urchin` on the URDF from `hello-robot-stretch-urdf`, not MJCF
  kinematics. We compute everything from the MJCF so it matches the simulated geometry.

### 2.3 Facts measured in a throwaway prototype (2026-10-09)
A scratch venv (uv, Python 3.11, `mujoco==3.2.6`, numpy 2.4.6, **not** the conda env and not project code)
loaded `stretch.xml`, built the scene with `MjSpec`, and ran a hand-written IK and skills (the prototype used
its own small solver; the plan uses mink instead, see 3.3). Results that shape this plan:

| Finding | Value |
|---|---|
| Model size | 38 bodies, 21 joints, 10 actuators, 722 keyframes, 362 sensors |
| Scene build from `stretch.xml` with `MjSpec` (floor, light, table, 2 cylinders) | works, 0.6 s to compile; sensors disabled afterwards through `opt.disableflags` |
| Physics speed, sensors off, with contacts | about 0.05 ms per `mj_step`, roughly 37× real time headless |
| Idle stability, 10 s | cylinders and base moved under 0.01 mm |
| Passive viewer opened from our own process on Windows, with real-time pacing | works; a 7.39 s gesture took 7.39 s wall time |
| Grasp centre (`link_grasp_center`) in the base frame, top-down (wrist pitch −1.57) | x = −0.0215, y = −(0.1207 + arm), z = lift − 0.131 |
| Same with wrist pitch 0 (gripper straight) | y = −(0.4148 + arm), z = lift + 0.1145 |
| Fingers close along **world x**, i.e. perpendicular to the arm | fingertip gap 0.002 m (gripper −0.02), 0.069 (0), 0.206 (0.04) |
| Base footprint | x from −0.28 (caster) to +0.05, y ±0.17; swept radius about 0.26 |
| Wheel yaw P-controller on measured yaw (control ±6, gain 12 per rad, 0.4° deadband) | 25° turn settles in about 3.5–4.3 s, peak 0.76 rad/s, final error under 0.4° |
| Base creep during rotations | about 3–5 mm toward −x per rotation, 7 mm after a 3-skill sequence |
| Servo steady-state error | lift lags its target by 4–10 mm under load; arm 0 mm |
| Pick, each colour from a fresh reset (final layout, 3.2) | both succeeded; cylinder rose about 14 cm, both fingers in contact; about 16 s of sim time |
| Pick sweep, cylinder distance from the rotation centre, table edge 0.36 m | OK at 0.44, 0.48, 0.54, 0.60 and 0.64 m for both colours; an earlier run failed with `ik_failed` at 0.66 m (max reach 0.642 m) |
| Gesture then pick with ±2 cm random cylinder offsets, 10 trials per colour | 10/10 and 10/10 |
| Gesture with a straight gripper, final layout | gripper-tip radial distance = 0.415 + arm; cylinder at 0.538, so fraction 0.15 gives 0.478 (short of the cylinder), **0.3 gives 0.540 (tip right above it)**, 0.5 gives 0.624 (8.6 cm beyond it); no contact and 0.0 mm cylinder displacement in all three |
| Sequences, 9 tried from fresh resets (final layout, **new gesture order**, per-step contact monitor) | all passed (list in M5); non-target cylinder never moved; **zero robot-table and robot-cylinder contacts at any step**; gesture then pick with ±2 cm offsets 10/10 per colour; all 6 fraction and gripper variants clean |
| Time per skill (sim, new order) | pick from the carry pose about 15 s; gesture from the carry pose about 12 s with a 1 s hold; pick right after a gesture 20 to 24 s; second gesture 6 s (same cylinder) or 10 s (other cylinder); longest sequence (two gestures and a pick) 43 s |

Problems the prototype exposed (they drive design choices below):
- **Pitching the wrist down near the table crashes the fingertips into the table edge** when the gripper
  starts pointing forward; a 15 s timeout followed. The robot must start and travel in a **carry pose**
  (hanging gripper, high lift), and any pitch change must happen at carry height.
- Waiting for "joint within 3 mm of target" never succeeds on the lift (steady-state lag) and never
  succeeds on the gripper when it holds a cylinder. Settling must be judged by joint velocity, followed by a
  small trim.
- Targets must be read live from `MjData`, not remembered from the start of the episode.

**Contradiction:** [[stretch-3-robot]] (verified 2026-09-30) puts the grasp centre at about (0.03, −0.61)
with arm 0.5 and wrist pitch −1.57. The 2026-10-09 forward kinematics give (−0.0215, −0.6207). The y values
agree to 1 cm; the sign and size of the x offset differ. The new number comes from the MJCF kinematics
with all other joints at zero; the old one was measured in a running simulation, possibly with a nonzero
wrist yaw. The plan treats the new value as a starting estimate only, because the IK solver reads the real
offset from the model.

## 3. Design

### 3.1 Layers
```
 script (a GUI can sit here later)
        │   gesture("blue"), pick("green"), hold_final_frame(), close_window(), abort()
        ▼
 skills.py     high-level skills; each returns a SkillResult (ok, reason, timings)
        │   Cartesian goals  (grasp-centre position, fixed wrist pitch)
        ▼
 ik.py         mink 0.0.13 differential IK on a scratch copy → (yaw, lift, arm)
        │   joint targets
        ▼
 robot.py      motion executor: rate-limited ctrl, velocity-based settling + trim,
        │      wheel P-control for yaw, gripper close-until-stall
        ▼
 sim.py        owns MjModel + MjData, steps physics, syncs the passive viewer, reset(), freeze(), live poses
        ▲
 scene.py      builds the model: stretch.xml + floor + table + two cylinders (MjSpec)
```
A skill call returns when the motion is finished (or failed or aborted). The viewer is synced from inside the
step loop, so the window stays alive while a skill runs.

### 3.2 Scene (`scene.py`), fixed layout
World frame: robot rotation centre at the origin, facing +x, arm toward −y. The layout is **fixed** (no
randomising, no swapping); numbers are values in `SceneConfig`.

| Item | Value | Reason |
|---|---|---|
| Table | box, half-size 0.6 × 0.5 × 0.24, top at z = 0.48, **near edge at y = −0.36** (centre y = −0.86), friction `1.0 0.01 0.002` | same height as the default table; the edge is 0.10 m beyond the base's swept radius (0.26), moved back from 0.32 m at your request so nothing touches it at the start or while turning |
| Cylinders | r = 0.035, h = 0.10, mass 0.1, `condim=6`, friction `1.0 0.01 0.002`; blue `0.1 0.2 1`, green `0.1 0.75 0.2`; bodies `cyl_blue`, `cyl_green`; free joint | verified grasped and lifted at exactly this size |
| Positions | **0.54 m** from the rotation centre, ±25° from the −y axis: blue at (−0.228, −0.489), green at (+0.228, −0.489) | the pick needs arm 0.418 m, 80 % of travel, with about 0.10 m of leeway outward (max reach 0.642 m) and plenty inward; the cylinders are 0.46 m apart, wide enough for the open gripper (0.206 m gap) and for clearly different gestures; each is about 0.09 m from the table edge |
| Robot start | **carry pose** (3.4), at the origin, yaw 0, gripper hanging down | the stock `home` keyframe has a straight gripper, which hits the table when the wrist is pitched down |
| Model options | OR `mjDSBL_SENSOR` into `opt.disableflags`, timestep 0.002 | lidar off ([[dev-environment]]) |

The scene is built with `MjSpec.from_file(stretch.xml)` then `worldbody.add_geom/add_body/add_light`
(verified in MuJoCo 3.2.6). The default `scene.xml` is not used, so nothing needs deleting.

### 3.3 Inverse kinematics (`ik.py`): the third-party library mink 0.0.13
**Decision (requested 2026-10-09):** IK is done by a third-party library with **no hand-written solver and no
cross-check solver in the project**. A background agent surveyed IK libraries (mink, dm_control, ikpy,
Pinocchio and pink, PyBullet, Drake, roboticstoolbox, MJX-based tools, pytorch_kinematics, Hello Robot's
own IK, others); mink is the only one that passes our filters (MuJoCo 3.2.6, Windows with Python 3.11
wheels, no GPU, usable license). The agent itself would have kept a hand-written solver for the PoC; the
decision to use mink now is the user's. Summary and sources in 3.3.1.

- **What mink is:** a differential IK library for MuJoCo models. Each step it solves a small quadratic program
  for a joint velocity that reduces the task error, then integrates it. It reads the MJCF directly, so no URDF
  and no model conversion. Version **0.0.13** (2025-09-12) requires MuJoCo 3.1.6 or newer and qpsolvers with
  daqp 4.3.1 or newer, so it installs next to `mujoco==3.2.6`. **Do not install a newer mink**: 1.0.0 to
  1.3.0 require MuJoCo from 3.3.6 up to 3.10.0, and a plain `pip install mink` pulls MuJoCo 3.10 or newer,
  which breaks the Stretch model. mink ships a Stretch 3 example (`examples/mobile_stretch.py` and
  `examples/hello_robot_stretch_3`) that we read for the setup.
- **How we use it (always on a scratch copy, never the live `MjData`):**
  1. `mink.Configuration(model)` holds its own data. Each solve sets it to the live joint state, including the
     live base x, y so creep is absorbed, then iterates.
  2. Task: one `FrameTask` on the body `link_grasp_center` with **position cost 1 and orientation cost 0**
     (position only; the wrist pitch is held at −1.57 by freezing it, not by an orientation task).
  3. Coupled arm: an `EqualityConstraintTask` (cost about 1000) keeps `joint_arm_l0..l3` equal, using the
     model's own equality constraints, so the arm behaves as one DOF; its value is the sum of the four joints.
  4. Free base: the free-joint position and tilt dofs (0 to 4) are frozen; **dof 5 (yaw) is the only free base
     variable**. The free joint's angular dofs are in the body frame, so dof 5 is pure yaw while the base is
     upright.
  5. Every joint not needed for the pick (wrist yaw, roll and pitch, gripper, head) is frozen. Freezing is a
     small custom `Limit` (about 15 lines) that clamps those dofs to plus or minus 1e-6 of their current value.
     mink 0.0.13 has no built-in freeze; mink 1.x has `DofFreezingTask`.
  6. Solver `daqp`. The loop runs `solve_ik` and `integrate_inplace` until the position error is under 1 mm or
     an iteration cap (50, a parameter) is reached.
- **Result read back:** `base_yaw` from the free joint, `lift`, and `arm` (sum of the four joints). Skills turn
  these into wheel and servo motions (3.4). The gesture uses the same solve (yaw for the pick pose, and
  `arm_pick` to scale the extension). In the survey's test mink kept the four arm joints identical.
- **Latency:** the survey measured **0.55 to 1.1 ms per solve and 2 to 3 iterations** with mink 0.0.13 on this
  3-DOF task. Every solve is timed with `perf_counter` and returned as an `IKStat` (iterations, residual,
  milliseconds), so "the only latency is IK" stays a measured number.
- **Failure handling:** an unreachable target does not raise. In the survey a target beyond the 0.52 m arm
  stopped at the arm limit after 59 iterations and about 22 ms with a large residual. We therefore **always
  check the residual** after the solve and return `ik_failed` or `unreachable` when it exceeds 2 mm.
- **Known pitfalls (from the survey; design around them):**
  - mink's joint limits make the quadratic program infeasible when a frozen joint starts **outside** its range.
    The stock wrist pitch range is −1.57 … 0.56; starting at −1.5708 made the solver fail ("failed to find a
    solution"). **Use −1.57 everywhere** (carry pose, reset, frozen value). The prototype ran with −1.57 as its
    constant in its final version.
  - The same applies to every frozen joint: clamp the start state into its range before solving.
  - A frozen-dof slack of 1e-6 was used; exact zero after fixing the start state was not tested.
  - An unpinned install pulls a newer MuJoCo (see above), so `environment.yml` must pin mink.
- **Dependencies added:** `mink==0.0.13` and, through it, `qpsolvers` (LGPL-3.0 per its PyPI classifier) and
  `daqp` (MIT, Windows wheel available). All are fine for a course project. mink is Apache-2.0 per its
  repository and its 1.3.0 metadata **(unverified for the 0.0.13 release: its PyPI metadata has no license
  field)**.

#### 3.3.1 Survey summary (2026-10-09)
| Library                                                                        | Verdict      | Why                                                                                                                                                                                                         |
| ------------------------------------------------------------------------------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| mink 0.0.13                                                                    | **chosen**   | MJCF native, requires MuJoCo 3.1.6 or newer, wheels only on Windows, ran on our model                                                                                                                       |
| mink 1.0.0 to 1.3.0                                                            | avoid        | require MuJoCo 3.3.6 to 3.10.0; 1.3.0 also ran on 3.2.6 with `--no-deps` (median 0.32 ms) but that combination is unsupported                                                                               |
| dm_control IK                                                                  | skip         | newer releases need newer MuJoCo (1.0.26 is the last one that accepts MuJoCo 3.2.6); needs a dm_control Physics wrapper; ignores joint limits                                                               |
| ikpy 4.1.0                                                                     | skip         | no MuJoCo dependency, but 7 to 50 ms per solve claimed; `Chain.from_mjcf_file` on `stretch.xml` returned only the origin link in the survey's test                                                          |
| Pinocchio, pink, placo, RoboPlan                                               | skip         | no Windows wheels on PyPI (conda-forge has pinocchio win-64 4.0.0); URDF-oriented                                                                                                                           |
| PyBullet, Drake                                                                | skip         | no cp311 Windows wheel; no Windows pip package                                                                                                                                                              |
| roboticstoolbox, pytorch_kinematics, mjinx and MJX, mujoco_mpc, ik-geo, curobo | skip         | URDF only and heavy, pulls torch, needs `jax[cuda]`, not pip-installable on Windows, license unspecified, or GPU only                                                                                       |
| Hello Robot's own IK                                                           | not reusable | stretch_mujoco has no IK (it only uses `urchin` for forward kinematics); Hello Robot's tutorial uses ikpy on the URDF with a virtual base joint and says position IK cannot solve a differential-drive base |

Sources (from the survey agent): mink on PyPI (`pypi.org/pypi/mink/json` and per-version JSON for 0.0.13 and
1.3.0), the mink repository (`github.com/kevinzakka/mink`, with `examples/hello_robot_stretch_3` and
`examples/mobile_stretch.py`), `pypi.org/pypi/daqp/json`, `pypi.org/pypi/qpsolvers/json`,
`pypi.org/pypi/dm-control/json`, `pypi.org/pypi/ikpy/json`, `pypi.org/pypi/libpinocchio/json`,
`pypi.org/pypi/placo/json`, `drake.mit.edu/installation.html`, `github.com/google-deepmind/mujoco_mpc`, and
the Hello Robot forum and tutorial pages on Stretch IK. **I re-checked the mink pins, the daqp license and the
Stretch example against PyPI and GitHub; everything else here is as the agent reported it.** Its benchmark
scripts are in the session scratchpad, not in the project.

### 3.4 Motion execution (`robot.py`)
- **Two safe poses.** The **carry pose** (the start pose): lift 0.80, arm 0, wrist pitch −1.57, gripper open
  0.04; the hanging gripper (lowest fingertip about 0.63 m high) is well above the 0.48 m table top and inside a
  0.25 m radius. The **pointing pose** (gesture end): wrist straight (pitch 0), gripper closed (or open, by the
  `gripper` option), lift about 0.54 so the gripper is 0.07 m above the cylinder top, arm extended.
  **Rules:** (1) the wrist pitch changes only at carry height (lift 0.80); a swing nearer the table would hit
  the table edge; (2) the base rotates only with the **arm fully retracted** and from one of the two safe poses.
  With the arm in, the straight gripper's tip is 0.415 m from the rotation centre, 8 cm short of the nearest
  cylinder surface (0.503 m), at a height above the cylinder tops, so turning in the pointing pose with the
  arm in is safe. `prepare_to_turn()` enforces this: retract the arm fully first (the wrist and gripper stay as
  they are, so after a gesture the gripper stays straight and closed while it turns); only if the robot is in
  neither safe pose (for example after a failed pick) does it bring it back to carry (lift up, pitch down, arm in).
  `reset()` writes `qpos` and `ctrl` directly into the carry pose and steps 1 s to settle.
- **Joint moves:** `ctrl` ramps toward the target at a per-joint rate (initial: lift 0.15 m/s, arm 0.15 m/s,
  wrist 0.8 rad/s, gripper 0.05 m/s). A move is finished when all moved joints have joint speed near zero for
  about 0.1 s, then a trim loop adds the remaining position error to `ctrl` (up to 3 times, for lift and arm).
- **Base yaw:** wheel velocity actuators driven with opposite signs, ctrl = clip(12 × yaw error, ±6), with a
  floor of 0.7 so it does not stall on wheel friction, and a 0.4° deadband. It needs only the sign convention
  (positive ctrl on both wheels drives forward, from the wheel axis orientation and the formulas in
  `utils.py`). Wheel spinning works in-process, so no kinematic fallback is needed.
- **Gripper close:** drive `ctrl` to −0.005 and wait for the fingers to stall (speed near zero), then require
  both fingers touching the cylinder before lifting.
- **Pacing:** **real-time by default** (`realtime=True`): the step loop sleeps so wall time follows sim time
  and the viewer is synced each tick, so the user can watch every motion. `realtime=False` runs flat out
  (about 37× real time) for checks. `headless=True` skips the viewer.
- **Contact monitor:** the step loop records any contact between a robot body and the table (fingertips
  excluded while grasping) so checks can assert there were none during the whole run, not only at the end.
- `abort()` sets a `threading.Event` checked every control tick, so a caller can cancel a motion.

### 3.5 Skills (`skills.py`), the public API
```python
from hri_sim import StretchSim, SceneConfig, Skills

sim = StretchSim(SceneConfig(), headless=False, realtime=True)   # real-time, viewer on
sim.reset()
skills = Skills(sim)

skills.gesture("blue", fraction=0.3, gripper="closed", hold_s=2.0)    # returns SkillResult
skills.pick("green")                                 # returns SkillResult; episode ends on success
skills.hold_final_frame()                            # keeps the window alive on the last frame
skills.close_window()                                # closes the viewer window
```
| Skill | Steps |
|---|---|
| `gesture(color, fraction=0.3, gripper="closed", hold_s=2.0)` | read the cylinder's live position → IK for the pick pose (gives yaw and `arm_pick`) → `prepare_to_turn` (a previous gesture's arm is fully retracted first; wrist and gripper stay as they are) → **turn the base** so the arm axis points at the cylinder → **swing the wrist from −1.57 to 0 and set the gripper (`closed`, or `open`) at the same time** (skipped if already straight) → **lower the lift** until the gripper is `clearance` (0.07 m) above the cylinder top → **extend the arm** to `fraction × arm_pick` → hold `hold_s` seconds. Leaves the robot in the pointing pose. The wrist swing and the gripper command are issued together by the same rate-limited move; if issuing them together turns out to disturb the motion, they run one after the other (wrist first), which is an equally valid gesture |
| `pick(color)` | read the cylinder's live position → IK for pre-grasp (0.12 m above grasp height) and grasp (grasp centre 0.06 m above the table top) → `prepare_to_turn` (after a gesture the arm is retracted completely, gripper still straight and closed) → turn the base → **if the wrist is straight (after a gesture): lift to carry height, then pitch the wrist down while opening the gripper** → move to pre-grasp → **re-solve IK from the live pose** → descend → close until stall → lift 0.15 m → check. **On success: freeze the simulation (no more stepping), keep the last frame in the viewer, mark the episode over** |
| `hold_final_frame()` | keep syncing the viewer (so the window stays responsive and the camera can still be moved) until the window is closed or `close_window()` is called; blocks |
| `close_window()` | close the viewer window (also ends `hold_final_frame()`) |
| `abort()` | cancel the running skill and zero the wheels |
| `sim.reset()` | restart a new episode (carry pose, cylinders back in place); allowed after the episode ended |

- `SkillResult`: `ok`, `skill`, `target`, `reason` (empty on success, otherwise one of `unreachable`,
  `ik_failed`, `no_grasp`, `dropped`, `timeout`, `aborted`, `episode_over`, `window_closed`),
  `sim_time`, `wall_time`, `ik` (list of `IKStat`). Task failures return `ok=False`; they do not raise.
- A failed pick (`no_grasp`) does not end the episode; the caller may retry.
- Colour names are validated against `sim.objects`, so more objects later are a config change.
- **Pick success** (all must hold): both fingers in contact with the cylinder after the lift, the cylinder
  rose at least 0.10 m from its starting height (prototype: about 0.14), and its centre is within 0.05 m
  horizontally of the grasp centre.
- The gesture's `fraction` is a fraction of the arm extension needed for the grasp (your definition), and
  `gripper` is `closed` or `open`. Both are provisional defaults until you have judged them in the viewer
  (3.6).

### 3.6 The gesture with a straight gripper
Your request: start with the gripper hanging, and end the gesture with it straight. The geometry that
matters (measured, section 2.3): with the wrist at pitch 0 the grasp centre sits **0.415 m + arm** from the
rotation centre. The cylinders are 0.538 m away, so even a small extension puts the gripper tip at or past
them. With `fraction` as a share of the grasp extension (0.418 m):

| fraction | arm extension | gripper tip radial distance | relative to the cylinder (0.538 m) |
|---|---|---|---|
| 0.15 | 0.063 m | 0.478 m | 6 cm short |
| **0.3** | 0.125 m | 0.540 m | directly above it |
| 0.5 | 0.209 m | 0.624 m | 8.6 cm beyond it |

The gripper is held 0.07 m above the cylinder top (the lowest part of the open or closed straight gripper
stays clear; no contact in any run), so a tip "beyond" the cylinder just hovers past it. Rendered frames at
0.3 and 0.5 both read as pointing at the blue cylinder, and 0.3 looks the most deliberate. The default is
therefore **0.3** as a provisional value; it is a parameter in `SkillConfig`. The order of motions (turn, swing the
wrist and close the gripper at carry height with the arm in, lower the lift, and extend the arm last) avoids
both the table edge and the cylinders: the swing happens high up, and while lowering the tip is still 8 cm
short of the nearest cylinder surface. Between skills the arm retracts completely and the base turns with the
gripper still straight and closed, as you asked, instead of going back to the carry pose.

**Judging it in the viewer (your request).** `scripts/demo_gesture_variants.py` runs the gesture in real time
from a fresh reset for every combination of fraction (default 0.15, 0.3, 0.5) and gripper state (closed, open),
for the colours you name (default both). It prints the label of each variant in the terminal, holds the final
pose for 5 s (the camera stays draggable, so you can look from the side) and then resets and moves on.
Options: `--fractions`, `--grippers`, `--colors`, `--hold`. You choose the winner; the defaults in `SkillConfig`
are then changed to it. What to look for: does it read as pointing at that cylinder rather than at the other one;
does the straight gripper look deliberate; is the extension visible from the front of the table; closed grippers
look like a pointing finger, open ones look like a hand about to grasp (more like intent to pick, less like a
point).

### 3.7 Ending an episode and the window
A successful `pick` freezes physics: `sim.step()` becomes a no-op, the final state is synced to the viewer
once, and `episode_over` is set. The window then stays open showing the lifted cylinder until
`close_window()` is called (or the user closes it); the view stays draggable (you confirmed this is what you
want). `hold_final_frame()` is the blocking call a demo script ends with. Calling any skill after that returns
`episode_over` until `sim.reset()` starts a new episode. A failed skill does not freeze anything.

### 3.8 GUI
No GUI is planned now. Skills are blocking functions that return structured results and never raise on task
failures, which is enough for a GUI plan to build on later.

### 3.9 Interfaces later work will rely on
Skills are the single place where "robot intent" is expressed. A GUI button, a scripted study condition
or a VLA wrapper all call `gesture` and `pick`. This matches the later clarification conditions (gesture,
wait, then pick) without committing to a policy interface ([[open-issues]] OI-15).

## 4. File-by-file changes
All new. Package name `hri_sim` is an assumption.

| Path | Contents |
|---|---|
| `src/hri_sim/__init__.py` | exports `StretchSim`, `SceneConfig`, `Skills`, `SkillResult` |
| `src/hri_sim/config.py` | dataclasses `SceneConfig` (model path, table, cylinders, layout), `MotionConfig` (speeds, tolerances, timeouts, yaw gains), `SkillConfig` (pick and pre-grasp heights, lift 0.15, gesture fraction 0.3, clearance 0.07, hold, carry lift) |
| `src/hri_sim/scene.py` | `build_model(cfg)`: `MjSpec` scene as in 3.2, sensors disabled |
| `src/hri_sim/sim.py` | `StretchSim`: model/data, `reset()`, `step()`, `freeze()`, passive viewer, real-time pacing, live object pose and finger-contact queries, robot-table contact monitor, `abort` event |
| `src/hri_sim/ik.py` | `IKSolver` (wraps mink: configuration, frame task, arm equality task, freeze-dofs limit, residual check), `IKStat` |
| `src/hri_sim/robot.py` | actuator and joint lookup, rate-limited moves with velocity settling and trim, wheel yaw controller, gripper close-until-stall, `prepare_to_turn` |
| `src/hri_sim/skills.py` | `Skills` (`gesture`, `pick`, `hold_final_frame`, `close_window`, `abort`), `SkillResult` |
| `src/scripts/demo.py` | viewer demo for a chosen sequence, e.g. `python scripts/demo.py gesture:blue pick:green`; ends with `hold_final_frame()` |
| `src/scripts/demo_gesture_variants.py` | the viewer session for judging gesture fraction and gripper state (3.6) |
| `src/scripts/check_scene.py` `check_pick.py` `check_gesture.py` `check_sequences.py` | verification scripts for M1 to M5 (plain Python with asserts, a pass or fail table and an exit code; no pytest, so no new dependency). There is no separate IK check: mink's residual and the live grasp-centre error in `check_pick.py` cover it |
| `src/environment.yml` | **add `mink==0.0.13`** to the pip section next to `mujoco==3.2.6`, with a comment that a newer mink needs a newer MuJoCo. The agent edits the file and `wiki/concepts/dev-environment.md`; **you run** `conda env update -f environment.yml --prune` (AGENTS.md). `hello-robot-stretch-mujoco` stays listed but is not imported |

On implementation the wiki gets `codebase/` pages (architecture, IK, skills API, how to run), a changelog
entry, and updated [[open-issues]] (OI-1 resolved; OI-10 closed as out of scope; OI-11 narrowed), per `AGENTS.md`.

## 5. Milestones and verification
Run everything in the `hri_stretch` conda env. **M0 is the human's step.** The "Seen in prototype" column
is evidence that the target is reachable, not a substitute for running the project checks.

| #   | Milestone                                        | Verification (pass criteria)                                                                                                                                                                                                                                                                                                                                                                                                 | Seen in prototype                                                    |
| --- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| M0  | Conda env built ([[open-issues]] OI-8) with mink | `python -c "import mujoco, mink; print(mujoco.__version__)"` prints 3.2.6 and imports mink; the model path in `SceneConfig` exists (submodule checked out)                                                                                                                                                                                                                                                                   | n/a (used a uv venv; mink was tested in the survey agent's own venv) |
| M1  | Scene, sim loop, viewer                          | Window opens; 10 s idle: cylinders move under 2 mm, base under 5 mm; real-time factor logged (about 1.0 with pacing, many times faster headless); **zero robot-table contacts during the whole run** when yaw is swept ±40° in the carry pose and in the pointing pose with the arm in                                                                                                                                                                                | all met except the per-step contact check (monitor is new)           |
| M2  | IK and executor, no grasping                     | mink solve for both pre-grasp positions converges under 1 mm and `ik_failed` is returned for an out-of-reach target; after execution the live grasp centre is within 6 mm of the target; yaw reaches target within 0.5°; IK times reported                                                                                                                                                                                   | IK 0.55–1.1 ms (survey); grasp-centre error 3–6 mm; yaw error 0.4°   |
| M3  | Pick, each colour in its own run                 | From a fresh `reset`: blue only, then green only; success per 3.5, simulation frozen with the last frame in the viewer, `episode_over` returned for any later skill. Then 20 trials per colour with seeded ±2 cm offsets; then radial positions 0.44 to 0.64 m. Gate to M4: 100 % at nominal and at least 90 % within ±2 cm                                                                                                  | 100 % nominal; 10/10 and 10/10 at ±2 cm; OK at 0.44–0.64 m           |
| M4  | Gesture, each colour                             | Arm axis within 3° of the line to the cylinder; arm extension equal to `fraction × arm_pick` within 1 cm; wrist pitch reaches 0 (within 0.05 rad) and the gripper is 0.05 to 0.09 m above the cylinder top; no cylinder moved more than 5 mm; no robot-object contact; yaw for blue and green differs by about 50°; the logged joint trajectories show the order: turn, then wrist and gripper together, then lift down, then arm out; plus **your viewing session** with `demo_gesture_variants.py` to choose the final fraction and gripper state                           | tip radial 0.540 m at 0.3, 0.0 mm displacement, no contacts          |
| M5  | Combinations                                     | Each from a fresh `reset`: gesture(blue) → pick(green); gesture(green) → pick(blue); gesture(blue) → pick(blue); gesture(green) → pick(green); gesture(blue) → gesture(green) → pick(green); gesture(green) → gesture(blue) → pick(blue); gesture(blue) → gesture(blue) → pick(blue). Pass: every skill `ok`, the non-target cylinder moves under 5 mm, no robot-table or robot-cylinder (non-target) contact at any step, base creep under 3 cm at the end | all 7 and the 2 single picks passed, zero contacts at any step                                  |
| M6  | API polish | `abort()` stops a motion mid-way; `hold_final_frame()` and `close_window()` work (including closing the window by hand); `demo.py` runs a sequence end to end in real time; docs written to `codebase/` | not tried |

## 6. Assumptions I made (please confirm or correct)
1. **Architecture B**, one process, passive viewer ([[mujoco-primer]] §4); needs `mujoco`, `numpy` and `mink`.
2. **The model is loaded from the submodule path**, not from the installed pip package.
3. **The base only rotates in place.** The robot never translates, so there is no navigation.
4. **Layout is fixed** (3.2): cylinders 0.54 m from the rotation centre at ±25°, blue on the −x side and green
   on the +x side; table edge 0.36 m away.
5. **Cylinders:** r = 3.5 cm, h = 10 cm, 0.1 kg, blue and green.
6. **Top-down grasp** at wrist pitch −1.57 with the grasp centre 6 cm above the table top (mid-upper height).
7. **Gesture:** straight gripper at the end, gripper **closed** while pointing (looks like a pointing finger;
   a parameter), hovering 0.07 m above the cylinder top, arm extended to a **fraction of the grasp extension**,
   default **0.3** (your definition of "half way"). Both defaults are provisional until you judge them in the
   viewer (3.6).
8. **Pick ends the episode:** after the lift (0.15 m of lift, cylinder about 14 cm up) the simulation freezes and
   the last frame stays until `close_window()`. There is no release, bin, or placing.
9. **Skills are blocking** and run on the caller's thread; no GUI work in this plan.
10. **IK by mink 0.0.13**, pinned in `environment.yml`, trusted as is: no old solver, no cross-check script.
11. **Sensors off and no cameras**, per [[dev-environment]].
12. All geometry and speed numbers are **starting values** from the measurements in 2.3, tuned during M1 and M2.
13. Package `hri_sim` in `src/`, scripts in `src/scripts/`, verification as plain scripts, not pytest.
14. **Real-time pacing is the default**, so a pick takes about 16 s on screen and a gesture about 13 s plus the
    hold. Speeds are parameters if you want them faster.

## 7. Open questions
Decided by the user on 2026-10-09: mink 0.0.13 is fine as the pin; the final frame stays open and draggable;
GUI work is deferred.
1. **Gesture fraction and gripper state:** to be decided by you after the viewing session in 3.6. Until then
   the defaults are 0.3 and closed.

## 8. Risks
- **Prototype versus project code:** the numbers in 2.3 come from a hand-written scratch script (with its own
  small IK). The project implementation is new code with mink and must reproduce them (M1 to M5 check this).
  mink itself was benchmarked only on the 3-DOF task, in the survey agent's environment.
- **Settling and trim logic** is the fiddly part (velocity thresholds, servo lag); tuned parameters may need
  adjusting on another machine.
- **Wrist swing and lowering:** the swing happens at carry height with the arm fully in, and the lift lowers
  before the arm extends. If the carry lift, cylinder radius or `clearance` change, re-check clearance (the
  monitor in 3.4 flags contacts). Turning in the pointing pose relies on the arm being fully in (tip 8 cm short
  of the cylinders).
- **Rotation near the table:** carry pose and the 0.36 m edge give a 10 cm margin; `table_edge_clearance` is a
  parameter if the base load changes.
- **numpy 2.x versus conda numpy:** the prototype ran numpy 2.4.6 with `mujoco==3.2.6`; the conda env may
  resolve a different numpy. Check at M0 **(unverified in conda)**.
