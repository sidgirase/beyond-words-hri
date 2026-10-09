---
title: Development environment (verified requirements)
type: concept
sources: [stretch-3-robot, local machine checks 2026-09-30]
updated: 2026-09-30
---

# Development environment

Verified on 2026-09-30 on the team's machine. The verification runs used a throwaway uv venv in a scratch
folder (not part of the repo). **The project itself uses conda**; see the setup section below.

## Machine
| Item          | Value                                                                                                                                                            |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OS            | Windows 11 Home 10.0.26200 (PowerShell + Git Bash)                                                                                                               |
| CPU / RAM     | 1 processor, 32 GB                                                                                                                                               |
| GPU           | **Intel Arc 140T integrated** (driver 32.0.101.8801, OpenGL 4.6). **No NVIDIA/CUDA.**                                                                            |
| System Python | 3.11.8 (has `mujoco 3.4.0`, `numpy 1.26.4`, `opencv 4.11`, `pynput 1.8.1`, `glfw` globally; **don't use it for the project**, since the MuJoCo version is wrong) |
| conda         | **Miniforge, conda 25.3.1** at `C:\ProgramData\miniforge3`, default channel conda-forge. Existing envs include `torch_xpu` (PyTorch on the Intel GPU). |
| uv            | 0.10.10. Used only for the throwaway verification venv; not for the project. |
| git           | 2.51                                                                                                                                                             |
| WSL2          | Ubuntu-24.04 installed (stopped). A fallback only; not needed so far.                                                                                            |

## Requirements for our project
- **Python 3.11** in the conda env. Not 3.10: on Windows, Python 3.10's `time.sleep` has about 15 ms
  granularity (measured `sleep(1.8 ms)` → 12 ms), and stretch_mujoco sleeps once per 2 ms physics
  step, which caps real time at about 0.15×. Python 3.11 uses high-resolution timers (measured 2.3 ms).
- **`mujoco==3.2.6`** (pinned by stretch_mujoco; the model won't load on 3.4.0). See [[stretch-3-robot]].
- `hello-robot-stretch-mujoco` 0.5.0 from GitHub (pulls in `hello-robot-stretch-urdf`, `urchin`,
  `pynput`, `opencv-python`, `matplotlib`, `inputs`, `click`).
- No GPU/CUDA needed for simulation. A future learned policy (VLA) **cannot use a local CUDA GPU**. The
  existing `torch_xpu` conda env suggests PyTorch runs on the Intel Arc GPU (XPU) **(unverified for VLA-size
  models)**. Otherwise plan on CPU-light policies, Colab, or a lab machine for that stage.

## Setting up the conda environment
The environment is defined in `src/environment.yml` (env name `hri_stretch`): Python 3.11, pip, git, and
via pip `mujoco==3.2.6` plus `hello-robot-stretch-mujoco` pinned to commit `d107e09`. MuJoCo comes from
pip rather than conda-forge because conda-forge only carries MuJoCo 3.8 and newer, which is too new.

The human runs these commands (the agent doesn't create environments):

```
conda env create -f environment.yml       # first time, from the src folder
conda activate hri_stretch
python -c "import mujoco, stretch_mujoco; print(mujoco.__version__)"   # expect 3.2.6
conda env update -f environment.yml --prune   # after environment.yml changes
```

**(unverified)** The conda environment itself hasn't been built yet. Everything on this page was measured
in the uv venv with the same Python minor version (3.11) and the same package versions, so it should
behave the same. Confirm with the check command above the first time it's created.

## Performance findings (MuJoCo 3.2.6, Python 3.11)
| Measurement | Result |
|---|---|
| `mj_step`, stock model | **~10 ms/step** (timestep 2 ms → at most 0.2× real time) |
| cause | the **360 lidar rangefinders** raycasting against the ~927k-vertex meshes |
| `mj_step` with sensors disabled (`mjDSBL_SENSOR`) | **0.15–0.3 ms/step** |
| `mj_step` with contacts disabled instead | still 8 ms, so contacts are not the bottleneck |
| offscreen camera render (424×240, Arc iGPU) | ~135 ms/frame; ~73 ms without shadows; ~40 ms without reflections |
| headless, sensors off, **no cameras** | real-time factor **0.73**, joints reach setpoints |
| headless, sensors off, 1 camera at 5 Hz | real-time factor **0.23** (rendering holds the lock the physics thread needs) |
| headless, sensors off, 2 cameras at 30 Hz | real-time factor ~0.01 (physics starved) |
| **passive viewer** (GUI), sensors off, no cameras | real-time factor **0.61**, joints reach setpoints, base drives. **Works on Windows.** |
| managed viewer (`use_passive_viewer=False`) | sim time ran at 1.0× but **commanded joints did not move** within 6 s. Treat as not working until investigated. |
| startup time | 5–7 s (process spawn + model load) |

## Rules that follow
1. Always disable the sensor stage (`model.opt.disableflags |= mjDSBL_SENSOR`) or strip the lidar from
   the model, unless lidar is actually needed.
2. Use **no simulated cameras** during teleop (the viewer window is enough). If a policy needs images,
   render at low rate with shadows and reflections off, or accept slower-than-real-time stepping.
3. Use the **passive viewer** for interactive runs.
4. Keep Python 3.11 and `mujoco==3.2.6` pinned in `environment.yml`.
