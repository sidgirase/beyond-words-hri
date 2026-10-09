---
title: Stretch 3 robot and the stretch_mujoco simulator
type: concept
sources: [proposal-beyond-words, idea-analysis, github.com/hello-robot/stretch_mujoco @ d107e09 (2026-01-05)]
updated: 2026-09-30
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
  extension of the server, or to run MuJoCo in-process instead. This is a key design decision for the plan.

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

## Default `scene.xml`
Floor, a wooden table box centred at (0, −1, 0.24) with half-size 0.6 × 0.5 × 0.24 (**top at z = 0.48**,
spanning y −1.5 … −0.5), two small free boxes (`object1`, `object2`), and the docking station.

## Physics findings
See [[dev-environment]] for timings. For grasping, see the "Graspability" section of [[ambiguous-scene-design]].
