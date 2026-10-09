---
title: Stretch 3 robot and the stretch_mujoco simulator
type: concept
sources: [proposal-beyond-words, idea-analysis, github.com/hello-robot/stretch_mujoco @ d107e09 (2026-01-05)]
updated: 2026-10-09
---

# Stretch 3 and `stretch_mujoco`

The proposal builds everything first in Hello Robot's `stretch_mujoco`, then moves to a physical Stretch
2 or 3 ([[proposal-beyond-words]]). Everything below was **verified on 2026-09-30** by cloning the repo
(commit `d107e09`, version 0.5.0) and running it on the team's Windows machine, unless marked otherwise.
Machine setup, measurements and workarounds are in [[dev-environment]].

## Package facts
- Package `hello-robot-stretch-mujoco` 0.5.0, installed with `uv`. `requires-python ≥ 3.10`; the repo pins
  3.10 in `.python-version`, but 3.11 is also declared and works (and is needed on Windows, see [[dev-environment]]).
- **Pins `mujoco==3.2.6`**, required for Robocasa compatibility. The robot MJCF **fails to load on
  MuJoCo 3.4.0** ("mesh volume is too small: base_link_2"), so we must stay on 3.2.6.
- The changelog claims Ubuntu, macOS and Windows support. The only CI workflow is a docs deploy on Ubuntu,
  so Windows isn't CI-tested; we tested it ourselves.
- The Robocasa kitchens are optional extras (they need Python 3.10 and pinned numpy/opencv). **We don't need them**; our
  scene is a table.
- It ships `examples/keyboard_teleop.py` (pynput, WASD base, IJKL lift/arm, wrist, gripper keys) and
  `examples/gamepad_teleop.py`, which are good references for our teleop.

## Architecture
- `StretchMujocoSimulator` (client, user's process) spawns a **separate MuJoCo process**
  (`multiprocessing`, `spawn`) and talks to it through `multiprocessing.Manager` proxies.
  An IPC round trip (`set_status` + `get_command`) takes about 0.27 ms.
- Constructor: `StretchMujocoSimulator(scene_xml_path=None, model=None, camera_hz=30, cameras_to_use=[],
  start_translation=None, start_rotation_quat=None)`.
  **Custom scenes work by passing a compiled `MjModel`** (it pickles fine, and `opt` flags survive).
  Verified: load `stretch_mujoco/models/scene.xml` with `mujoco.MjSpec.from_file`, add bodies to
  `spec.worldbody`, `spec.compile()`, pass it as `model=`.
- `start(show_viewer_ui=False, headless=False, use_passive_viewer=True)`. Three server variants:
  headless, passive viewer and managed viewer.
- Client API: `home()`, `stow()`, `move_to(actuator, pos)`, `move_by(actuator, delta)`,
  `set_base_velocity(v, ω)`, `wait_until_at_setpoint`, `wait_while_is_moving`, `pull_status()`
  (joint pos/vel plus sim time), `pull_camera_data()`, `pull_sensor_data()`, `get_base_pose()` (returns a tuple
  x, y, θ), `get_ee_pose()`, `get_link_pose(name)`, `pull_joint_limits()`, `stop()`.
- **The client cannot read object poses.** Only robot status, cameras and sensors cross the process
  boundary. Checking whether an object is in the bin, or which object is held, needs either our own
  extension of the server, or to run MuJoCo in-process instead. **Resolved 2026-10-09:** the project runs MuJoCo
  in-process and loads only the model file ([[codebase/architecture]]).

## Robot model (from `stretch.xml`)
Actuator names and control ranges (sim units):

| Actuator | Range | Type |
|---|---|---|
| `left_wheel_vel`, `right_wheel_vel` | −6 … 6 | velocity (diff-drive base) |
| `lift` | 0 … 1.1 m | position |
| `arm` | 0 … 0.52 m (4 telescoping joints `joint_arm_l0..l3`, tendon-coupled) | position |
| `wrist_yaw` | −1.39 … 4.42 rad | position |
| `wrist_pitch` | −1.57 … 0.56 rad | position |
| `wrist_roll` | −3.14 … 3.14 rad | position |
| `gripper` | −0.02 (closed) … 0.04 (open) | position (`joint_gripper_slide`) |
| `head_pan` / `head_tilt` | −4.04 … 1.73 / −1.53 … 0.79 rad | position |

- The client API also has virtual actuators `base_translate` / `base_rotate` (position moves done by a
  base controller) and maps the gripper to a "real robot" range of −0.376 … 0.56.
- Useful bodies: `base_link`, `link_grasp_center` (point between the fingertips), `link_lift`,
  `link_gripper_finger_left/right`, `rubber_tip_left/right`.
- Cameras: `d435i_camera_rgb/depth` (head RealSense, 424×240), `d405_rgb/depth` (wrist, 480×270),
  `nav_camera_rgb`.
- Sensors: **360 rangefinders (the 2D lidar)** plus 2 others. There are 720 keyframes (`home000..359`,
  `stow000..359`, plus `home` and `stow`).
- The mesh-heavy model has 112 meshes and about 927k vertices.
- In its home pose the robot is at the origin facing +x, and **the arm extends toward −y**. With the arm at
  0.5 and wrist pitch −1.57, the grasp centre is at about (0.03, −0.61).

## Model details verified from the submodule (2026-10-09)
Source: `src/stretch_mujoco/` (git submodule, commit `c78d6a1`, README-only change after `d107e09`) and
forward-kinematics checks in a throwaway venv. Full table in [[ik-pick-and-gesture-poc]], section 2.
- The base is a free joint; the wheel axle midpoint is the `base_link` origin (wheels at y = ±0.17035,
  radius 0.05), so wheel spin rotates the robot about the origin. Base footprint: x from −0.28 to +0.05,
  y ±0.17.
- Wheel actuators are `velocity` type with `gear=3`: the control value is 3 times the wheel joint speed,
  range ±6. The base turns at most about 0.76 rad/s.
- The arm is one DOF: four slide joints held equal by equality constraints, driven by one tendon; each
  joint is `arm / 4`.
- Top-down grasp (wrist pitch −1.57), base frame: grasp centre x = −0.0215, y = −(0.1207 + arm),
  z = lift − 0.131. With a straight gripper (pitch 0): y = −(0.4148 + arm), z = lift + 0.1145.
- Fingers close along world x (perpendicular to the arm). Fingertip gap: 0.002 m at gripper −0.02, 0.069 m
  at 0, 0.206 m at 0.04.
- Lift servo lags its target by 4 to 10 mm under load; the arm servo does not.
- The `home` and `stow` keyframes are ctrl-only (`mujoco_server.py` copies only `ctrl`).
- `get_ee_pose` and `get_link_pose` use the URDF through `urchin`, not the MJCF.

**Contradiction:** the "Robot model" section above gives the grasp centre as about (0.03, −0.61) with arm 0.5
and pitch −1.57. Forward kinematics on the MJCF give (−0.0215, −0.6207). The y values agree; the x offset
differs in size and sign. The earlier value was read from a running simulation, possibly with a nonzero wrist
yaw. Treat the MJCF value as authoritative for planning; the same note is in [[ik-pick-and-gesture-poc]].

## Default `scene.xml`
Floor, a wooden table box centred at (0, −1, 0.24) with half-size 0.6 × 0.5 × 0.24 (**top at z = 0.48**,
spanning y −1.5 … −0.5), two small free boxes (`object1`, `object2`), and the docking station.

## Physics findings
See [[dev-environment]] for timings. For grasping, see the "Graspability" section of [[ambiguous-scene-design]].
