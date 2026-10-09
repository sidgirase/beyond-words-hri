---
title: How to run and verify
type: codebase
sources: [scripts, environment.yml, dev-environment]
updated: 2026-10-09
---

# How to run and verify

## Environment
- Python 3.11, `mujoco==3.2.6`, `mink==0.0.13` (see [[dev-environment]]), plus `imageio` and `imageio-ffmpeg` for
  video recording. `environment.yml` lists them; the human builds or updates the conda environment:
  ```
  conda env update -f environment.yml --prune     # or: conda env create -f environment.yml
  conda activate hri_stretch
  python -c "import mujoco, mink, imageio; print(mujoco.__version__)"      # expect 3.2.6
  ```
- **Status 2026-10-09:** all runs and checks so far used a throwaway uv environment with the same versions,
  because the agent does not touch conda. Building `hri_sim`'s environment in conda and running the checks there
  is still to do ([[open-issues]] OI-8). **The last complete pass of all check scripts was after the gesture
  redesign and before the recording feature and the final tidy-up.** After those, `check_recording.py` passed
  and a recorded demo ran, and every file was syntax checked, but the other scripts were not re-run
  (the scratch environment became unavailable); run all of them once in the conda environment.
- The robot model comes from the git submodule: `git submodule update --init` if `src/stretch_mujoco/` is empty.
- Run scripts from `src`: `python scripts/NAME.py`.

## Demos (viewer window, real time)
| Command | What it does |
|---|---|
| `python scripts/demo.py gesture:blue pick:green` | gesture at blue, then pick green; the simulation stops on the last frame and the window stays open until you close it |
| `python scripts/demo.py pick:blue` | just a pick |
| `python scripts/demo.py gesture:green gesture:blue pick:blue --fraction 0.7` | any sequence, with gesture options |
| `python scripts/demo.py gesture:blue pick:green --record` | the same, and a video in `src/outputs/demo_DATE_TIME.mp4`; `--record my_run` names it `outputs/my_run.mp4` |
| `python scripts/demo_gesture_variants.py` | the viewing session: the gesture at lift fractions 0.25, 0.5 and 1.0 (as low as is safe), both colours, each final pose held 5 s; labels print in the terminal |

Options: `--fast` (no real-time pacing), `--headless` (no window), `--close-after S` (demo.py: close the window by
itself), `--hold S`, `--fraction F`, `--fractions`, `--colors`. Recording options: `--record [NAME]`,
`--video-fps` (30), `--video-size WxH` (1280x720), `--record-tail S` (2 s of the final frame at the end). While
recording, the run is slower than real time (rendering costs about 0.09 s per frame); the video plays at the true
simulation speed. Details in [[codebase/skills-api]].

## Checks (plain scripts, print a pass or fail table, exit code 0 when all pass)
| Script | What it covers | Last result 2026-10-09 |
|---|---|---|
| `check_scene.py` (`--viewer` adds the window) | model and sensors, idle stability, pacing, yaw sweeps (carry pose, and carry height with the arm extended) with no contacts, the contact monitor catching a deliberate collision, viewer open and close | 15 passed after the gesture redesign (the `--viewer` part, 3 more checks, last run before it) |
| `check_pick.py` (`--quick` skips the sweeps) | IK convergence and out-of-reach, nominal picks per colour, 20 seeded offsets per colour, distances 0.44 to 0.64 m | 30 passed, 34 s |
| `check_gesture.py` | pointing error, arm extended to the object, hover over the cylinder, lift halfway, gripper closed during the turn, wrist never moves, order of motions, what the next skill does (other object, same object, pick), lift fractions 0.25, 0.5 and 1.0 | 42 passed, about 10 s |
| `check_sequences.py` | nine gesture and pick combinations from fresh resets | 9 passed, 14 s |
| `check_api.py` (`--viewer` adds window tests) | abort, failure results, episode end, window functions | 10 passed (7 more with `--viewer`, last run before the redesign) |
| `check_recording.py` (`--viewer` adds window camera tests) | recorder frame count, size, content, physics unchanged, `demo.py --record`, bad options | 13 passed headless, 2 more with `--viewer` |

## Measured behaviour (default configuration)
| Quantity | Value |
|---|---|
| IK solve | 1 to 3 iterations, 1.1 to 2.5 ms |
| Physics, headless unpaced | about 33 times real time; paced run: 3 s of sim in 3.00 s of wall time |
| Pick from the carry pose | about 15 s of sim time; cylinder rises 0.138 m; grasp-centre error 4 to 5 mm; base turn error under 0.5 degrees |
| Gesture from the carry pose | about 11.5 s of sim time including the 2 s hold |
| Gesture at the other cylinder | about 11 s |
| Pick right after a gesture at the same cylinder | about 7.4 s; at the other cylinder about 10 to 14 s |
| Gesture result at fraction 0.5 | gripper hangs 2.2 cm above the cylinder top, 4 to 5 mm horizontally off its centre; arm 0.419 m |
| Base creep | 2 to 5 mm per sequence, always toward -x |
| Recording | about 0.09 s per 1280x720 frame with the window open; a 25 s run gave a 27 s video (815 frames) in 53 s of wall time |

## Tuning
All numbers are in `hri_sim/config.py`. Likely candidates: `SkillConfig.gesture_fraction` (after the viewing
session), `MotionConfig.rates` (faster motions), `SceneConfig` (`cylinder_distance`, `table_edge_y`). Re-run
the checks after changing any of them.
