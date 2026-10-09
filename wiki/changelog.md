# Code changelog

Append-only. One entry per implemented plan: `## [YYYY-MM-DD] {plan-slug}` + what changed in the code.

## [2026-10-09] ik-pick-and-gesture-poc
First code in the repository: an IK-driven pick-up and gesture simulation of a Stretch 3 in MuJoCo.
- New package `src/hri_sim/`: `config.py` (scene, motion and skill settings), `scene.py` (stretch.xml plus floor, table and blue and green cylinders through `MjSpec`), `sim.py` (`StretchSim`: stepping, real-time pacing, passive viewer, per-step contact monitor, freeze, window functions), `ik.py` (mink-based IK wrapper), `robot.py` (joint moves with velocity-based settling and trim, wheel yaw controller), `skills.py` (`Skills.gesture`, `Skills.pick`, `SkillResult`).
- New scripts in `src/scripts/`: `demo.py`, `demo_gesture_variants.py`, and the checks `check_scene.py`, `check_pick.py`, `check_gesture.py`, `check_sequences.py`, `check_api.py` (plus the helper `_common.py`).
- `environment.yml`: added `mink==0.0.13` (pip section). `.gitignore`: added `__pycache__/` and `*.pyc`.
- The model is read from the submodule `src/stretch_mujoco/` (commit c78d6a1); the `stretch_mujoco` package itself is not imported.
- Verified in a throwaway uv environment (not the conda env): all five check scripts pass (14 + 30 + 38 + 9 + 10 checks, plus the viewer variants of two of them: 17 + 17). See [[codebase/how-to-run]].

## [2026-10-09] gesture-redesign-recording-cleanup
Follow-up changes to `src/hri_sim/` after the first implementation, at the user's request.
- **Gesture redesigned:** the wrist stays at -1.57 (gripper hanging) at all times. `gesture(color, fraction=0.5, hold_s=2.0)` now turns toward the cylinder while the gripper closes, extends the arm over it, then lowers the lift `fraction` of the way from carry height to the grasp height (0.5 is halfway; never lower than 1 cm above the cylinder top). The `gripper` option and the wrist swing were removed.
- **Between skills:** the arm is no longer retracted. The base turns whenever the lift is at carry height (`Skills._turn` lifts first), with the arm left out, so gesture or pick at the other cylinder is lift, turn, continue. A pick at the cylinder already pointed at only opens the gripper, then descends. Moves that would change almost nothing are skipped (turn under 1 degree, arm or lift under 3 mm).
- `Robot.turn_to(yaw, joints)` moves joints (the gripper) during the turn.
- **Cleanup:** removed `robot_state`, `close`, the wrist pitch and straight-gripper code, `gc_height_above_lift`, the wrist predicates and the unused joint lookups; renamed `pitch_down` to `wrist_pitch`; checked with pyflakes and vulture and by confirming every config field is used.
- **Video recording:** new `hri_sim/recorder.py` (`VideoRecorder`, offscreen render with the window's camera, H.264 mp4) and `scripts/demo.py --record [NAME]` (plus `--video-fps`, `--video-size`, `--record-tail`), saving to `src/outputs/` (git-ignored). `environment.yml` gained `imageio` and `imageio-ffmpeg`.
- Scripts: `check_gesture.py` rewritten for the new behaviour, `check_scene.py` sweep changed, new `check_recording.py`, `demo_gesture_variants.py` now varies the lift fraction (0.25, 0.5, 1.0).
- Verified in the throwaway uv environment: `check_gesture` 42, `check_sequences` 9, `check_pick` 30, `check_scene` 15, `check_api` 10 passed after the redesign; `check_recording` 13 passed after recording was added. The other scripts were not re-run after the recording feature and the final tidy-up. See [[codebase/how-to-run]].
