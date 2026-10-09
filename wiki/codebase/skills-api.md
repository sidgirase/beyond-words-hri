---
title: Skills API (gesture, pick, window, recording)
type: codebase
sources: [hri_sim/skills.py, hri_sim/sim.py, hri_sim/recorder.py, hri_sim/config.py]
updated: 2026-10-09
---

# Skills API

```python
from hri_sim import StretchSim, SceneConfig, Skills

sim = StretchSim(SceneConfig(), headless=False, realtime=True)   # viewer on, paced to real time
skills = Skills(sim)

print(skills.gesture("blue", fraction=0.5, hold_s=2.0))
print(skills.pick("green"))          # on success the simulation freezes on the last frame
skills.hold_final_frame()            # window stays open and draggable until it is closed
skills.close_window()                # closes the window (also ends hold_final_frame, from any thread)
```

Skills are blocking functions that run on the caller's thread. A skill never raises on a task failure; it
returns a `SkillResult`. Only one skill should run at a time. `abort()` and `close_window()` are safe to call
from another thread.

## `gesture(color, fraction=0.5, hold_s=2.0)`
The gripper hangs down (wrist pitch -1.57) the whole time and is closed from the first turn on.
1. If the lift is below carry height (after an earlier gesture), **lift to carry height first**.
2. **Turn the base** until the arm axis points at the cylinder (yaw from IK). **The gripper closes during the
   turn** (if it was open). The arm stays where it is, even if extended.
3. **Extend the arm** until the gripper hangs over the cylinder (the arm extension of the grasp pose). Skipped
   if the arm is already within 3 mm of it (for example when going from one cylinder to the other).
4. **Lower the lift** `fraction` of the way from carry height down to the grasp lift: 0.5 is halfway, which
   leaves the closed gripper about 2 cm above the cylinder top. The lift never goes lower than 1 cm above the
   cylinder top (`gesture_min_clearance`), so fractions above about 0.6 are clamped; `fraction_applied` in
   `info` says what was used.
5. Hold for `hold_s` seconds in real time. The robot stays in this pose.
Gesture at the object it already points at: nothing turns or lifts (at most a few-millimetre arm correction).
`info`: `fraction`, `fraction_applied`, `arm`, `arm_pick`, `lift`, `lift_goal`, `yaw_deg`,
`pointing_error_deg`, `hover_offset` (horizontal distance gripper to cylinder), `height_above_cylinder`,
`max_cylinder_displacement`, `turn_error_deg` (when it turned).
The default fraction is provisional until judged in the viewer ([[open-issues]] OI-19).

## `pick(color)`
1. IK for a pre-grasp pose (grasp centre 0.12 m above grasp height) and the grasp pose (0.06 m above the
   table top); both must be reachable.
2. If the base must turn (the start, or the other cylinder): lift to carry height first, then turn; the gripper
   opens during the turn. The arm is not retracted. If it already faces the cylinder (after a gesture at it):
   no turn, no lifting; **just open the gripper**.
3. If the arm is not already at the cylinder's distance, bring it out (without lowering the lift).
4. **Solve IK again** from the live pose and the live cylinder position (the base creeps a few millimetres per
   turn), descend so the open fingers straddle the cylinder, close the gripper until the fingers stall.
5. Lift 0.15 m. Success needs both fingers touching, the cylinder risen at least 0.10 m, and its centre within
   0.05 m of the grasp centre.
6. On success `sim.freeze()`: no further physics, the last frame stays in the viewer, `episode_over` is set.
A failed grasp (`no_grasp`) does not end the episode.
Event sequence examples (from `sim.events`): from the start `turn, pre_grasp, descend, close_gripper,
lift_up`; after a gesture at the same cylinder `open_gripper, descend, close_gripper, lift_up`; after a gesture
at the other cylinder `lift_to_carry, turn, descend, close_gripper, lift_up`.
`info`: `rise`, `fingers_touching`, `lateral_from_gripper`, `yaw_deg`, `turn_error_deg`,
`grasp_centre_error_mm`.

## `SkillResult`
| Field | Meaning |
|---|---|
| `ok` | the skill did what it should |
| `skill`, `target` | name and colour |
| `reason` | empty when ok; otherwise one of `unknown_target`, `unreachable`, `ik_failed`, `no_grasp`, `collision`, `timeout`, `aborted`, `episode_over`, `window_closed` |
| `sim_time`, `wall_time` | seconds the skill took in simulated and real time |
| `ik` | list of `IKStat` (iterations, residual, ms) for every solve in the skill |
| `info` | the measurements listed under each skill; `unwanted_contacts` if the contact monitor saw any |

`collision` means the per-step contact monitor saw the robot touch the table or a cylinder it should not
touch during the skill (fingertips on the target cylinder during the grasp are allowed).

## Other functions
| Call | Effect |
|---|---|
| `Skills.reset()` / `StretchSim.reset()` | new episode: carry pose, cylinders back in place, physics settled, flags cleared; allowed after the episode ended; fails if the window was closed |
| `Skills.abort()` | stops the running skill at the next control tick, wheels set to zero; the next skill starts from wherever the robot is (it lifts to carry height before turning) |
| `Skills.hold_final_frame()` | blocks, keeping the viewer responsive, until the window is closed or `close_window()` is called |
| `Skills.close_window()` | closes the viewer window |
| `sim.object_position(color)`, `sim.base_pose()`, `sim.grasp_center()`, `sim.joint(name)` | read-only state (`joint` takes lift, arm, gripper); `sim.contact_violations` holds the monitor's counts; `sim.events` holds the moves of the episode |

## Video recording (`VideoRecorder`, `scripts/demo.py --record`)
```python
from hri_sim import VideoRecorder
rec = VideoRecorder(sim, "outputs/run1.mp4", fps=30, width=1280, height=720)   # attaches itself to sim
skills.gesture("blue"); skills.pick("green")
rec.add_still(2.0)                    # hold the final frame for 2 s of video
rec.close()                           # finishes the file
```
- Renders the scene **offscreen** with the viewer window's own camera (so dragging the camera in the window
  changes the recording; without a window the default camera is used) every 1/fps of **simulated** time, and
  writes H.264 mp4. It is not a screen capture: window decorations are not in the video.
- Rendering is slow (about 0.09 s per 1280 x 720 frame with the window open), so a recorded run takes longer
  than real time; the video still plays at the true simulation speed. Recording does not change the physics
  (the same pick takes the same simulated time with and without it).
- `demo.py --record [NAME]` saves to `src/outputs/NAME.mp4` (default name `demo_DATE_TIME`), adds
  `--record-tail` seconds (default 2) of the final frame, and closes the file before waiting on the window.
  Options: `--video-fps`, `--video-size WxH`. The `outputs/` folder is git-ignored.
- Needs `imageio` and `imageio-ffmpeg` (in `environment.yml`); imported only when a recorder is created.

## Configuration
Every number lives in `config.py`: `SceneConfig` (layout, sizes, colours), `MotionConfig` (carry height,
speeds, settle and trim rules, yaw gains, pacing), `SkillConfig` (grasp and pre-grasp heights, lift after
grasp, success thresholds, gesture fraction, minimum clearance and hold, "already in place" tolerances, IK
tolerances), and `OUTPUTS_DIR`. Pass modified copies to `StretchSim` and `Skills`.
