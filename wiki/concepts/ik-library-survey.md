---
title: IK library survey for the Stretch in MuJoCo 3.2.6
type: concept
sources: [dev-environment, stretch-3-robot, "survey agent report 2026-10-09", pypi.org, github.com/kevinzakka/mink]
updated: 2026-10-09
---

# IK library survey

Done 2026-10-09 by a background agent for the PoC, filtered by our constraints: MuJoCo 3.2.6 (pinned, see
[[dev-environment]]), Windows with Python 3.11 wheels (no compiling), no GPU, usable license, maintained.
**Outcome: mink 0.0.13** is used ([[codebase/ik-and-motion]]). The agent itself recommended keeping a small
hand-written solver for the PoC and adopting mink later; the decision to use mink now was the user's.
I re-checked the mink pins, the daqp license and the Stretch example against PyPI and GitHub; everything else
is as the agent reported it.

| Library | Verdict | Why |
|---|---|---|
| mink 0.0.13 | **chosen** | MJCF native; requires MuJoCo 3.1.6 or newer and qpsolvers with daqp 4.3.1 or newer; wheels only on Windows; ran on our model |
| mink 1.0.0 to 1.3.0 | avoid | require MuJoCo 3.3.6 up to 3.10.0; 1.3.0 also ran on 3.2.6 with `--no-deps` (median 0.32 ms) but that combination is unsupported; 1.x adds `DofFreezingTask` and a free-joint velocity limit |
| dm_control IK | skip | newer releases need newer MuJoCo (1.0.26 is the last that accepts 3.2.6); needs a dm_control Physics wrapper; ignores joint limits |
| ikpy 4.1.0 | skip | no MuJoCo dependency, 7 to 50 ms per solve claimed; `Chain.from_mjcf_file` on `stretch.xml` returned only the origin link in the survey's test |
| Pinocchio, pink, placo, RoboPlan | skip | no Windows wheels on PyPI (conda-forge has pinocchio win-64 4.0.0); URDF-oriented |
| PyBullet, Drake | skip | no cp311 Windows wheel; no Windows pip package |
| roboticstoolbox, pytorch_kinematics, mjinx and MJX, mujoco_mpc, ik-geo, curobo | skip | URDF only and heavy, pulls torch, needs `jax[cuda]`, not pip-installable on Windows, license unspecified, or GPU only |
| Hello Robot's own IK | not reusable | stretch_mujoco has no IK (it only uses `urchin` for forward kinematics); Hello Robot's tutorial uses ikpy on the URDF with a virtual base joint and says position IK cannot solve a differential-drive base |

## Things learned about mink on this model
- Reuse: mink ships a Stretch 3 example (`examples/mobile_stretch.py`, `examples/hello_robot_stretch_3`).
- Latency on the 3-DOF task: 0.55 to 1.1 ms in the survey; 1.1 to 2.5 ms measured in the project (includes
  our own state copying).
- An unreachable target does not raise: the solver stops at the joint limit after tens of iterations
  (59 iterations, about 22 ms in the survey; 16 ms in the project) with a large residual, so the residual must
  always be checked.
- A frozen joint that starts outside its range makes the quadratic program infeasible ("failed to find a
  solution"). The wrist pitch limit is -1.57; -1.5708 triggered it.
- The free joint's angular dofs are in the body frame, so dof 5 is pure yaw while the base is upright.
- mink 0.0.13 has no built-in freeze; a 15-line custom limit does it.
- Dependencies pulled in: `qpsolvers` (LGPL-3.0 per its PyPI classifier) and `daqp` (MIT). mink is Apache-2.0
  per its repository and 1.3.0 metadata (the 0.0.13 PyPI metadata has no license field, **unverified for that
  release**).

## Sources
`pypi.org/pypi/mink/json` and per-version JSON for 0.0.13 and 1.3.0; `github.com/kevinzakka/mink` (examples
and CHANGELOG); `pypi.org/pypi/daqp/json`; `pypi.org/pypi/qpsolvers/json`; `pypi.org/pypi/dm-control/json`;
`pypi.org/pypi/ikpy/json`; `pypi.org/pypi/libpinocchio/json`; `pypi.org/pypi/placo/json`;
`drake.mit.edu/installation.html`; `github.com/google-deepmind/mujoco_mpc`; the Hello Robot forum and
`stretch_tutorials` pages on Stretch IK.
