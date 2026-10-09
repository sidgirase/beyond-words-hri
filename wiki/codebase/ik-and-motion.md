---
title: Inverse kinematics and motion execution
type: codebase
sources: [hri_sim/ik.py, hri_sim/robot.py, hri_sim/skills.py, hri_sim/config.py, ik-library-survey]
updated: 2026-10-09
---

# Inverse kinematics and motion execution

## Joints used
| Joint | Role | Range |
|---|---|---|
| Base (two wheels, differential drive) | rotates in place about the wheel-axle midpoint; never translates | continuous |
| Lift | vertical slide on the mast; carries the arm | 0 to 1.1 m, carry height 0.80 |
| Arm | four telescoping sections that always move together (equality constraints); extends toward -y in the robot frame | 0 to 0.52 m |
| Gripper | two fingers closing sideways, across the arm direction | slide -0.02 (closed) to 0.04 (open); fingertip gap 0.002 to 0.206 m |
| Wrist pitch | **fixed at -1.57: the gripper hangs straight down at all times**; set once at reset, never commanded | -1.57 to 0.56 rad |
| Wrist yaw, wrist roll, head | not moved | |

## IK (`ik.py`)
- Library: **mink 0.0.13** (differential IK on the MJCF). Why this one, and why only this version:
  [[ik-library-survey]] and [[dev-environment]].
- `IKSolver(model_path, wrist_pitch, ...)` loads its own copy of `stretch.xml`; the live simulation is
  never touched. `solve(target_xyz, base_qpos, joints)` takes the live base pose (7 numbers) and the live lift
  and arm-section values by MJCF name.
- Task: one `FrameTask` on the body `link_grasp_center`, position cost 1, orientation cost 0.
- Unknowns: base yaw (free-joint dof 5), lift, arm. The four arm sections are tied by an
  `EqualityConstraintTask` (cost 1000) built from the model's own equality constraints; the arm value is the
  sum of the four sections.
- Frozen: free-joint dofs 0 to 4, and every joint except lift and the arm sections, through a small custom
  `Limit` (`_FreezeDofs`, plus or minus 1e-6). The wrist pitch is set to -1.57 for every solve.
- Start state: every limited joint is clamped into its range before solving (an out-of-range frozen joint
  makes mink's quadratic program infeasible; -1.5708 instead of -1.57 was the trap).
- Loop: `solve_ik` with solver `daqp`, `integrate_inplace`, until the position error is under 1 mm or 50
  iterations. An exception inside the loop counts as not reached.
- Output: `IKResult(yaw, lift, arm, reached, at_limit, stat)`. `reached` means residual within 2 mm;
  `at_limit` (a free joint on its limit) turns a miss into `unreachable` rather than `ik_failed`.
  `IKStat(iterations, residual, ms, converged)` is returned with every skill result.
- Measured: 1 to 3 iterations, 1.1 to 2.5 ms per solve (median 1.5 ms); a target 0.95 m away is reported as
  not reached after 16 ms.
- Because the live base x, y go into every solve, the small creep of the base (a few millimetres per turn,
  toward -x) is absorbed; a repeated solve for the same cylinder can differ by a few millimetres of arm
  extension and under a degree of yaw.

## Motion executor (`robot.py`)
- **Joint moves** (`Robot.move`): lift, arm and gripper are position servos. `ctrl` ramps from its current
  value toward the target at a speed limit (lift 0.15 m/s, arm 0.15 m/s, gripper 0.05 m/s), several joints
  together. The move ends when all moved joints have been slower than 0.003 for 10 consecutive ticks (a tick
  is 5 physics steps). Lift and arm then get up to 3 trims that add the remaining position error to `ctrl`,
  because the lift servo settles 4 to 10 mm short under load. Never reaching a calm state within 12 s raises
  `SkillInterrupt('timeout')`. Each move is logged in `sim.events` under its name.
- **Base yaw** (`Robot.turn_to(yaw, joints=None)`): wheel velocity ctrl is `clip(12 x yaw error, plus or minus
  6)`, with a floor of 0.7 so the wheels do not stall, a 0.4 degree dead band, opposite signs on the two wheels.
  The wheel actuators have gear 3, so the control value is three times the wheel speed; the loop does not need
  the wheel radius or track width. A 25 degree turn takes about 3.5 to 4.3 s, peak 0.76 rad/s. **`joints`
  (the gripper) are ramped during the turn**, so the gripper closes or opens while the base rotates; they get
  time to settle afterwards. The turn is logged as `turn` with the joints it moved.
- **Why velocity, not position, decides "settled":** the gripper holding a cylinder never reaches its
  commanded value, and the lift always lags; joint speed near zero is the reliable signal.

## The one safety rule
The base turns only with the **lift at carry height** (at least 0.78 m). The hanging gripper is then about
8 cm above the cylinder tops (closed) and still clear of them with the gripper open, and well above the table.
**The arm may stay extended while turning**: it sweeps over the table and over the other cylinder at that
height, which is what makes "gesture at the other object" and "pick the other object" continuous motions.
`Skills._turn` lifts to carry height first whenever the lift is lower, then turns. There is no wrist swing
any more, so nothing else restricts motion, and a robot left in any pose (for example after an abort) gets
back to a safe state by lifting.
Skills also skip moves that would change almost nothing: no turn under 1 degree, no arm move under 3 mm, no
lift move under 3 mm, no gripper command that is already set.

## Geometry used (measured from the MJCF, base at the origin, yaw 0, wrist down)
- Grasp centre: x = -0.0215, y = -(0.1207 + arm), z = lift - 0.131.
- The arm axis is 0.0215 m off the rotation centre, so the yaw that points the arm at a cylinder differs
  slightly from the direction to it (blue about -22.3 degrees, green about +26.9 degrees); the IK handles
  this.
- Reach: top-down grasp radius runs from 0.12 m (arm in) to 0.64 m (arm out).
- With the arm out, the closed gripper's fingertips touch a cylinder top when the grasp centre is 6 mm below
  that top (measured by lowering the lift; lift 0.706 from carry height 0.794). The gesture stops 1 cm above
  the top at the lowest.
- Opening the gripper while it hovers about 2 cm above the cylinder top (the state after a gesture at
  fraction 0.5) does not touch the cylinder (checked by the contact monitor).
