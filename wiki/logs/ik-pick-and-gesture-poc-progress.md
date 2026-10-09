# Progress log: IK-driven pick-up and gesture PoC

Append-only. One entry per step of the implementation of [[plans/ik-pick-and-gesture-poc]], newest at the
bottom. Every entry has a timestamp (local time, EDT), the milestone it belongs to, what changed, which files
were touched, how it was verified, and any open items. Written by the agent; read it top to bottom for the
story, or jump to a milestone name (M0 to M6).

Entry layout:
- Heading: date, time, milestone, short title.
- Status: done, in progress or blocked.
- What changed: bullets, plain words.
- Files: path and one phrase each.
- Verification: the command and what it showed.
- Notes and open items.

---

### 2026-10-09 12:46 EDT · M0 · Environment and bookkeeping

**Status:** done for the agent side, conda build left to the user

**What changed**
- Plan status set to in-progress; this progress log, the `wiki/logs/` folder and a rule for it in `AGENTS.md` were created.
- `mink==0.0.13` added to the pip section of `environment.yml` (with a comment on why it must stay pinned).
- `wiki/concepts/dev-environment.md` now documents the mink pin and the reason.

**Files**
- `environment.yml` — added `mink==0.0.13` next to `mujoco==3.2.6`.
- `wiki/concepts/dev-environment.md` — mink requirement and pitfall.
- `AGENTS.md`, `wiki/index.md`, `wiki/plans/ik-pick-and-gesture-poc.md` — logs folder rule, index entry, status.

**Verification**
- Throwaway uv venv (not conda), `uv pip install mujoco==3.2.6 mink==0.0.13` resolved 13 packages; import check printed mujoco 3.2.6, numpy 2.4.6, qpsolvers 4.13.0, daqp 0.10.3 and `FrameTask`, `EqualityConstraintTask`, `ConfigurationLimit` all present.
- All development tests in this log run in that throwaway venv, because the agent does not touch conda environments.

**Notes and open items**
- **For you:** the conda environment has not been built or updated by me. Run `conda env update -f environment.yml --prune` (or `conda env create -f environment.yml` the first time), then `python -c "import mujoco, mink; print(mujoco.__version__)"` should print 3.2.6. Until then the conda part of M0 is open (OI-8).

---

### 2026-10-09 12:50 EDT · M1-M2 · Core package written, first smoke run

**Status:** in progress

**What changed**
- Wrote the `hri_sim` package: scene builder, simulation core, mink-based IK wrapper, motion executor and the two skills (`gesture`, `pick`), plus the config dataclasses.
- Scene: `stretch.xml` from the submodule plus floor, table (near edge 0.36 m) and two cylinders (blue, green) at 0.54 m, built with `MjSpec`; lidar sensors switched off.
- Simulation core: real-time pacing, viewer sync, per-step contact monitor (robot against table and against the non-target cylinder), freeze after a successful pick, window handling, abort flag.
- IK: mink `FrameTask` (position only) on `link_grasp_center`, arm sections tied by the model's own equality constraints, every other joint frozen, base yaw is the only free base variable; a residual check decides `ik_failed` / `unreachable`.

**Files**
- `src/hri_sim/config.py` — `SceneConfig`, `MotionConfig`, `SkillConfig` (all tunable numbers).
- `src/hri_sim/scene.py` — `build_model`, cylinder home positions.
- `src/hri_sim/sim.py` — `StretchSim`, `SkillInterrupt`.
- `src/hri_sim/ik.py` — `IKSolver`, `IKStat`, `IKResult`.
- `src/hri_sim/robot.py` — `Robot` (joint moves, wheel yaw controller, pose predicates).
- `src/hri_sim/skills.py` — `Skills`, `SkillResult`.
- `src/hri_sim/__init__.py` — package exports.

**Verification**
- First smoke run (throwaway venv, headless, unpaced): scene builds in 0.6 s; `gesture("blue")` ok, 13.1 s sim, pointing error 0.36 degrees, tip 0.541 m from the centre, gripper 0.067 m above the cylinder top, cylinders unmoved; `pick("green")` after it ok, 23.9 s sim, cylinder rose 0.139 m, both fingers touching, no contact violations; a further skill returned `episode_over`.
- IK solves took 1.1 to 1.9 ms each (3 iterations, residual under 0.5 mm).
- Event log shows the new gesture order: turn, wrist swing with gripper, lower lift, extend arm.

**Notes and open items**
- Grasp-centre error after the descent was 6.4 mm, just above the 6 mm target of M2; to be looked at with the M2 checks.
- Trim loops make some moves slower than needed (lower_lift 3.4 s); acceptable for now.
- Check scripts and demo scripts are next.

---

### 2026-10-09 12:51 EDT · M1 · Scene, sim loop and viewer checks

**Status:** done

**What changed**
- Added the shared check helper and the M1 check script `check_scene.py`.
- `StretchSim.realtime` is now independent of `headless`, so pacing can be tested without a window.

**Files**
- `src/scripts/_common.py` — makes `hri_sim` importable from `scripts/`, prints a pass or fail table, returns an exit code.
- `src/scripts/check_scene.py` — M1 checks (headless, plus `--viewer` for the window).

**Verification**
- `python scripts/check_scene.py --viewer` (throwaway venv): **17 passed, 0 failed**.
  - Idle 10 s: cylinders moved 0.001 mm, base 0.000 mm; arm sections equal (spread 8e-9).
  - Headless unpaced speed 33x real time; paced run 3.00 s of wall time for 3 s of sim.
  - Yaw sweep of plus and minus 40 degrees: zero contact violations in the carry pose and in the pointing pose with the arm in.
  - The contact monitor does flag a deliberate collision (extended hanging gripper lowered into the table).
  - Viewer window opened from our own process, paced at 1.00x, and `close_window()` closed it.

**Notes and open items**
- M1 is met. The viewer window flashed on screen for about 3 s during the check.

---

### 2026-10-09 12:52 EDT · M2-M3 · IK and pick checks

**Status:** done

**What changed**
- Added the M2 and M3 check script `check_pick.py`: IK convergence, an out-of-reach IK target, nominal picks per colour (each from a fresh reset), seeded plus and minus 2 cm offsets (20 trials per colour), and a distance sweep from 0.44 to 0.64 m.
- Skills now report `turn_error_deg` and (for picks) `grasp_centre_error_mm` in `SkillResult.info`.

**Files**
- `src/scripts/check_pick.py` — M2 and M3 checks (`--quick` for nominal picks only).
- `src/hri_sim/skills.py` — extra `info` fields.

**Verification**
- `python scripts/check_pick.py` (throwaway venv, headless): **30 passed, 0 failed**, 34 s wall time.
  - IK for both cylinders at grasp height and pre-grasp height converged under 0.3 mm in 3 iterations, 1.1 to 2.5 ms each (median 1.48 ms); a target 0.95 m away was reported as not reached (residual 349 mm).
  - Nominal picks: both succeeded, both fingers touching, rise 0.138 m, base turn error 0.40 and 0.37 degrees, grasp-centre error 3.9 mm (blue) and 5.0 mm (green), simulation frozen, a later skill returned `episode_over`, zero unwanted contacts, the other cylinder moved 0.00 mm.
  - Plus and minus 2 cm offsets: 20 of 20 for blue and 20 of 20 for green.
  - Distance sweep 0.44, 0.48, 0.52, 0.56, 0.60, 0.64 m: both colours picked at every distance.

**Notes and open items**
- M2 and M3 are met, and the M3 gate to M4 (100 % nominal, at least 90 % within 2 cm) is passed.
- One earlier smoke run measured 6.4 mm grasp-centre error after a gesture; this will be watched in the sequence checks.

---

### 2026-10-09 12:53 EDT · M4 · Gesture checks

**Status:** done (viewing session with the user still to come)

**What changed**
- Added `check_gesture.py` for M4.
- Gesture skips moves that would change nothing (a second gesture no longer re-sends the same gripper command or a zero-length lift move), comparing the gripper command rather than its position because closed fingers rest at -0.011, not at the commanded -0.02.

**Files**
- `src/scripts/check_gesture.py` — M4 checks.
- `src/hri_sim/skills.py` — skip no-op moves in `gesture`.

**Verification**
- `python scripts/check_gesture.py` (throwaway venv, headless, 10 s wall): **38 passed, 0 failed** after the fix (one check had failed first on the redundant gripper move).
  - Both colours: pointing error 0.36 and 0.38 degrees (limit 3); arm 0.126 m, exactly 0.3 x the grasp extension of 0.419 m; wrist pitch -0.005 rad; gripper 0.067 m above the cylinder top; no cylinder moved (0.00 mm); zero contact violations; simulation not frozen.
  - Order of motions from the event log is exactly turn, wrist swing with gripper (one move), lower lift, extend arm, each starting after the previous one ended.
  - The two gestures differ by 49.2 degrees of base yaw (blue -22.3, green +26.9).
  - A second gesture goes retract arm, turn, extend arm, with no trip back to the carry pose.
  - All 12 variants (fractions 0.15, 0.3, 0.5, gripper closed and open, both colours) ran collision free; tip radial distance 0.478, 0.54 and 0.624 m as predicted.

**Notes and open items**
- The automated part of M4 is met. Choosing the final fraction and gripper state is the user's viewing session with `demo_gesture_variants.py` (script comes next).

---

### 2026-10-09 12:55 EDT · M5 · Combination checks

**Status:** done

**What changed**
- Added `check_sequences.py`: nine combinations, each from a fresh reset, with the contact monitor active at every step.

**Files**
- `src/scripts/check_sequences.py` — M5 checks.

**Verification**
- `python scripts/check_sequences.py` (throwaway venv, headless, 14 s wall): **9 passed, 0 failed**.
  - gesture(blue) then pick(green); gesture(green) then pick(blue); gesture(blue) then pick(blue); gesture(green) then pick(green); gesture(blue), gesture(green), pick(green); gesture(green), gesture(blue), pick(blue); gesture(blue), gesture(blue), pick(blue); pick(blue) alone; pick(green) alone.
  - Every skill returned ok; zero robot-table and robot-cylinder contacts at any step; the non-target cylinder never moved 5 mm; the target did not move during gestures; the episode ended after each pick and a later skill returned `episode_over`.
  - Base creep at the end of a sequence: 1.7 to 5.3 mm (limit 30 mm). Sim time: 16 s for a lone pick, 34 to 38 s for gesture then pick, 44 s for two gestures then a pick.

**Notes and open items**
- M5 is met. The sequences with two gestures and a pick use the new between-skill behaviour (arm retracts completely, base turns with the gripper straight and closed).

---

### 2026-10-09 12:55 EDT · M6 · Demo scripts and API checks

**Status:** done

**What changed**
- Added the two viewer scripts and the API check script.
- `demo.py` runs a chosen sequence in real time (options for fraction, gripper, hold, fast, headless, `--close-after`), then keeps the final frame open until the window is closed.
- `demo_gesture_variants.py` is the viewing session for you: every fraction and gripper state, labelled in the terminal, each final pose held for 5 s with a draggable camera.
- `check_api.py` covers abort, failure results, episode end and the window controls.

**Files**
- `src/scripts/demo.py`, `src/scripts/demo_gesture_variants.py` — viewer scripts.
- `src/scripts/check_api.py` — M6 checks (`--viewer` for the window behaviours).

**Verification**
- `python scripts/demo.py gesture:blue pick:green --close-after 3` (real-time viewer): both skills ok, printed that the simulation stopped on the last frame, the window closed itself 3 s later by `close_window()` from a timer thread, exit code 0, 42 s wall time.
- `python scripts/demo_gesture_variants.py --headless --fast --hold 0.5 --colors blue --fractions 0.3 0.5`: all four variants ran and printed their tip distances (0.541 m and 0.624 m).
- `python scripts/check_api.py --viewer`: **17 passed, 0 failed**.
  - `abort()` from another thread stopped a pick after 2.5 s of sim, wheels stopped, episode not ended, and a gesture right after it worked (returns to a safe pose first).
  - An unknown colour returns `unknown_target`; a cylinder 0.95 m away returns `unreachable` without moving; results carry sim time, wall time and per-solve IK times (1.1 to 1.6 ms).
  - Viewer: stepping after a pick does nothing; `hold_final_frame()` blocks while the window is open and returns 0.10 s after `close_window()` from another thread; closing the window during a gesture stops it with `window_closed`, and the next skill also returns `window_closed`.

**Notes and open items**
- Closing the window by hand (the X button) was not exercised by a script; it goes through the same `viewer.is_running()` check as `close_window()`.
- Still to do: wiki sync (codebase pages, changelog, open issues), a final full run of all checks, and your viewing session with `demo_gesture_variants.py`.

---

### 2026-10-09 12:59 EDT · Wrap-up · Wiki sync and final regression

**Status:** done

**What changed**
- Wiki brought back in sync with the code: new codebase pages (architecture, IK and motion, skills API, how to run), the IK library survey as a concept page, the plan marked `implemented` and kept as the design record, changelog and log entries, index, overview, open issues (OI-1, OI-10, OI-11, OI-13 closed; OI-19 gesture look and OI-20 mink pin added), `dev-environment`, `mujoco-primer` and `ambiguous-scene-design` notes.
- `.gitignore` now ignores `__pycache__/` and `*.pyc`.

**Files**
- `wiki/codebase/README.md`, `architecture.md`, `ik-and-motion.md`, `skills-api.md`, `how-to-run.md`.
- `wiki/concepts/ik-library-survey.md`, plus small edits in three existing concept pages.
- `wiki/plans/ik-pick-and-gesture-poc.md`, `wiki/plans/README.md`, `wiki/open-issues.md`, `wiki/overview.md`, `wiki/changelog.md`, `wiki/log.md`, `wiki/index.md`.

**Verification**
- Final regression on the finished code (throwaway uv environment): `check_scene` 14 passed (17 with `--viewer`), `check_pick` 30, `check_gesture` 38, `check_sequences` 9, `check_api` 10 (17 with `--viewer`); no failures.
- Wiki lint: no unresolved wikilinks, no orphan pages, no angle-bracket characters in any wiki page.

**Notes and open items**
- **For you:** (1) update the conda environment: `conda env update -f environment.yml --prune`, then `python -c "import mujoco, mink; print(mujoco.__version__)"` should print 3.2.6; (2) run `python scripts/demo_gesture_variants.py` from `src` and tell me which fraction and gripper state read best (OI-19); (3) try `python scripts/demo.py gesture:blue pick:green`.
- Nothing is committed to git; the changes are in the working tree.
- Not covered by a script: closing the viewer window with the mouse (same code path as `close_window()`).

---

### 2026-10-09 14:01 EDT · Change 1 · Gesture redesign requested

**Status:** in progress

**What changed**
- Change request received from the user after the wiki sync. New gesture, in the user's words: the wrist stays pitched down at -1.57 the whole time; the robot turns toward the object while closing the gripper (if it was open), extends the telescoping arm to the object, then lowers the lift halfway toward it; that is the gesture. The gripper stays closed throughout. A pick for the same object then opens the gripper and picks. A command for the other object lifts to the initial (carry) height and rotates with the arm still extended, instead of retracting.
- Also requested: remove unused code afterwards, then update the wiki.
- Consequences planned: no wrist swing and no straight gripper any more; the gesture option "gripper open or closed" goes away; "fraction" now means how far down the lift goes from carry height to the grasp height; the base may turn whenever the lift is at carry height (the arm no longer has to be retracted); `pick` skips turning, the pre-grasp move and the lift-up when the robot is already in place.

**Files**
- none yet (design step).

**Verification**
- Measured before changing code (scratch script, current package): with the arm extended to a cylinder and the gripper closed and hanging, the fingertips first touch the cylinder top when the grasp centre is 5 mm below the top (lift 0.706, from 0.794 at carry height). Halfway down from carry height to the grasp lift (0.671) is a lift of about 0.733, which leaves about 2 cm above the cylinder: collision free, so 0.5 can be the default.

**Notes and open items**
- Opening the gripper while hovering over the cylinder lowers the fingertips by about 4 cm while they move outward; to be tested for contact with the cylinder top.

---

### 2026-10-09 14:18 EDT · Change 1 · Gesture redesigned and checked

**Status:** done

**What changed**
- Gesture: wrist stays at -1.57; turn toward the cylinder while the gripper closes; extend the arm over it; lower the lift `fraction` (default 0.5) of the way from carry height to the grasp height; hold. The `gripper` option and the wrist swing are gone.
- Between skills: no retract. The base turns whenever the lift is at carry height (lift up first if not), arm left out. Pick at the object just pointed at: open gripper, descend, close, lift. Pick or gesture at the other object: lift to carry height, turn (gripper opens or is already closed), continue.
- `Robot.turn_to(yaw, joints)` ramps joints during the turn. Skills skip moves that change almost nothing (turn under 1 degree, arm or lift under 3 mm, gripper already at its command).
- Config: removed `pitch_straight`, `gesture_gripper`, `gesture_clearance`, the wrist rate; renamed `pitch_down` to `wrist_pitch`; added `gesture_min_clearance`, `no_turn_deg`, `arm_match_tol`, `lift_match_tol`; default `gesture_fraction` 0.5.

**Files**
- `src/hri_sim/config.py`, `ik.py`, `robot.py`, `sim.py`, `skills.py` — rewritten or trimmed for the new behaviour.
- `src/scripts/check_gesture.py` (rewritten), `check_scene.py` (sweep with the arm extended at carry height), `demo.py`, `demo_gesture_variants.py` (lift fractions instead of gripper states).

**Verification** (throwaway uv environment)
- Measured first: with the arm out and the gripper closed and hanging, the fingertips touch the cylinder top when the grasp centre is 6 mm below it (lift 0.706 from 0.794); halfway down (lift about 0.736) leaves 2.2 cm, so 0.5 is a safe default.
- `check_gesture.py`: 42 passed. Gesture events are turn (gripper closing during it), extend arm, lower lift; hover offset 3.9 and 4.9 mm; gripper 2.1 to 2.3 cm above the cylinder; wrist stays at -1.570 rad. At the other object: lift to carry, turn, lower, arm never retracted. Pick after a gesture at the same object: open, descend, close, lift only. Pick at the other object: lift to carry, turn, descend. Fractions 0.25, 0.5, 1.0 (clamped to 0.61, 0.7 to 0.9 cm above) collision free.
- `check_sequences.py` 9, `check_pick.py` 30, `check_scene.py` 15, `check_api.py` 10 passed.

**Notes and open items**
- Two checks first failed for test reasons, not code: a repeated gesture at the same cylinder still makes a 4 mm arm correction (the base creeps about 7 mm between turns, shifting the IK answer), and the lowest-fraction height band was too tight; both tests were corrected.
- Opening the gripper while hovering 2 cm above the cylinder does not touch it (contact monitor, no violations).

---

### 2026-10-09 14:18 EDT · Change 2 · Unused code removed

**Status:** done

**What changed**
- Ran pyflakes and vulture over `hri_sim` and `scripts`, and checked that every config field is read somewhere outside `config.py`.
- Removed: `StretchSim.robot_state` and `close`, unused joint lookups (wrist yaw and roll, head), `IKSolver.gc_height_above_lift` and its scratch data, `Robot` wrist predicates and `arm_is_in`, the `REASONS` constant (the reasons are listed in the `SkillResult` docstring), an unused numpy import in `check_api.py` and an unused variable in `check_scene.py`.
- The `import _common` lines in the scripts are kept on purpose (they put `src` on the import path) and are marked `noqa`; the remaining vulture reports are MuJoCo settings assigned in `scene.py` and `sim.py`, not dead code.

**Files**
- `src/hri_sim/*.py`, `src/scripts/*.py`.

**Verification**
- pyflakes: clean apart from the intentional `_common` imports. All config fields used. `check_gesture`, `check_sequences`, `check_pick`, `check_scene`, `check_api` passed before the last tiny edits (unused import and variable); afterwards all files compile.

**Notes and open items**
- See the verification gap noted in the wrap-up entry below.

---

### 2026-10-09 14:18 EDT · Change 3 · Video recording in demo.py

**Status:** done

**What changed**
- New `hri_sim/recorder.py` with `VideoRecorder`: renders the scene offscreen every 1/fps of simulated time with the viewer window's own camera (or the default camera without a window) and writes H.264 mp4 through imageio. `StretchSim.step` calls it through `sim.recorder`.
- `scripts/demo.py --record [NAME]` saves to `src/outputs/NAME.mp4` (default `demo_DATE_TIME`), with `--video-fps`, `--video-size WxH`, `--record-tail` (seconds of the final frame at the end, default 2). The file is closed even if the run fails.
- `environment.yml`: added `imageio` and `imageio-ffmpeg`. `.gitignore`: added `outputs/`.
- New `scripts/check_recording.py`.

**Files**
- `src/hri_sim/recorder.py`, `config.py` (`OUTPUTS_DIR`), `sim.py` (hook), `__init__.py`, `src/scripts/demo.py`, `src/scripts/check_recording.py`, `environment.yml`, `.gitignore`.

**Verification**
- Probe: 1280x720 frames render in 91 ms each with the viewer open; mp4 writes and reads back.
- `check_recording.py`: 13 passed headless (frame count 331 for 10 s of sim at 30 fps plus a 1 s still; size, content, physics unchanged: the same pick takes the same 15.270 s with and without recording; `demo.py --record` end to end; a bad `--video-size` rejected); with `--viewer` the recording has 61 frames for 2 s and moving the window camera changes the video (mean pixel change 13.1).
- Real run: `python scripts/demo.py gesture:blue pick:green --record demo_check --close-after 2` made `src/outputs/demo_check.mp4`: 815 frames, 27.2 s of video, 53 s of wall time; the sampled frames show the table, both cylinders, and the gripper over the blue cylinder and, at the end, holding the green one.

**Notes and open items**
- It is an offscreen re-render with the window's camera, not a screen capture, so window decorations are not in the video.
- `src/outputs/demo_check.mp4` is a test file; delete it if you do not want it.

---

### 2026-10-09 14:18 EDT · Wrap-up · Wiki sync and an honest verification gap

**Status:** done, with one open item

**What changed**
- Wiki brought in line: `codebase/` pages (IK and motion, skills API, how to run, architecture, README), overview, open issues (OI-19 reworded for the lift fraction), dev-environment (imageio), changelog, log, and a note on the plan page that its straight-gripper gesture sections are superseded.

**Files**
- `wiki/codebase/*.md`, `wiki/overview.md`, `wiki/open-issues.md`, `wiki/concepts/dev-environment.md`, `wiki/plans/ik-pick-and-gesture-poc.md`, `wiki/changelog.md`, `wiki/log.md`.

**Verification**
- No angle-bracket characters in the wiki (scanned). All files in `hri_sim` and `scripts` compile and the imports between the package modules resolve.
- **Gap:** the scratch directory with my test environment was withdrawn late in the session, so I did not re-run `check_pick`, `check_gesture`, `check_sequences`, `check_scene` and `check_api` after the last two edits (video recording hook in `sim.step`, and the tidy-up of an unused import and variable). `check_recording` and a recorded demo did run after the hook. Both edits are small, but this is unconfirmed.

**Notes and open items**
- **For you:** build or update the conda environment, then run `python scripts/check_gesture.py`, `check_pick.py`, `check_sequences.py`, `check_scene.py`, `check_api.py` and `check_recording.py` from `src` and tell me about any failure. Then run `python scripts/demo_gesture_variants.py` to choose the gesture depth (OI-19).
