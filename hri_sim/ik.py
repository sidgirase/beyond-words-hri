"""Inverse kinematics with mink (differential IK on the MJCF).

Task: put `link_grasp_center` at a 3D position with the wrist held at a fixed pitch (gripper hanging down).
Free variables: base yaw, lift and the arm (four telescoping joints held equal by the model's equality
constraints). Everything else is frozen. The solver works on its own private copy of the robot model, never
on the live simulation data.
"""
import math
import time
from dataclasses import dataclass
from pathlib import Path

import mink
import mujoco
import numpy as np
from mink.limits.limit import Constraint, Limit

ARM_JOINTS = ("joint_arm_l0", "joint_arm_l1", "joint_arm_l2", "joint_arm_l3")
FREE_JOINTS = ("joint_lift", *ARM_JOINTS)  # plus the base yaw (free-joint dof 5)
FREEZE_SLACK = 1e-6


@dataclass
class IKStat:
    """Timing and quality of one solve; skills return these so the IK latency is a measured number."""

    iterations: int
    residual: float  # metres, grasp centre to target
    ms: float
    converged: bool


@dataclass
class IKResult:
    yaw: float  # world yaw of the base, radians, in (-pi, pi]; unwrap against the current yaw before use
    lift: float
    arm: float  # total telescope extension (sum of the four sections)
    reached: bool  # residual within the failure threshold
    at_limit: bool  # a free joint ended on its limit (a hint that the target is out of reach)
    stat: IKStat


class _FreezeDofs(Limit):
    """Clamps the listed dofs to (almost) zero velocity. mink 0.0.13 has no built-in freeze."""

    def __init__(self, nv: int, dofs):
        eye = np.eye(nv)[list(dofs)]
        self._G = np.vstack([eye, -eye])
        self._h = np.full(2 * len(dofs), FREEZE_SLACK)

    def compute_qp_inequalities(self, configuration, dt):
        return Constraint(G=self._G, h=self._h)


class IKSolver:
    def __init__(self, model_path: Path, wrist_pitch: float, tolerance: float = 1e-3,
                 max_iterations: int = 50, damping: float = 1e-3, fail_residual: float = 2e-3):
        self.model = mujoco.MjModel.from_xml_path(str(model_path))
        m = self.model
        self.wrist_pitch = wrist_pitch
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.damping = damping
        self.fail_residual = fail_residual

        self._jid = {m.joint(i).name: i for i in range(m.njnt)}
        self._qa = {n: int(m.jnt_qposadr[i]) for n, i in self._jid.items()}
        self._free_base = next(i for i in range(m.njnt) if m.jnt_type[i] == mujoco.mjtJoint.mjJNT_FREE)

        # frozen dofs: base x, y, z, roll, pitch (free-joint dofs 0..4) and every joint that is not lift or arm
        frozen = [0, 1, 2, 3, 4]
        for i in range(m.njnt):
            if i != self._free_base and m.joint(i).name not in FREE_JOINTS:
                frozen.append(int(m.jnt_dofadr[i]))  # every other joint is a hinge or slide: one dof

        arm_ids = {self._jid[n] for n in ARM_JOINTS}
        eqs = [e for e in range(m.neq)
               if m.eq_type[e] == mujoco.mjtEq.mjEQ_JOINT
               and int(m.eq_obj1id[e]) in arm_ids and int(m.eq_obj2id[e]) in arm_ids]
        if len(eqs) != 3:
            raise RuntimeError(f"expected 3 arm equality constraints, found {len(eqs)}")

        self._cfg = mink.Configuration(m)
        self._task = mink.FrameTask("link_grasp_center", "body", position_cost=1.0, orientation_cost=0.0)
        self._eq_task = mink.EqualityConstraintTask(m, cost=1000.0, equalities=eqs)
        self._limits = [mink.ConfigurationLimit(m), _FreezeDofs(m.nv, frozen)]
        self._lift_range = tuple(m.jnt_range[self._jid["joint_lift"]])
        self._arm_max = sum(float(m.jnt_range[self._jid[n]][1]) for n in ARM_JOINTS)

    def _start_q(self, base_qpos, joints: dict) -> np.ndarray:
        m = self.model
        q = m.qpos0.copy()
        q[:7] = base_qpos
        for name, value in joints.items():
            q[self._qa[name]] = value
        q[self._qa["joint_wrist_pitch"]] = self.wrist_pitch
        # mink's joint limits make the problem infeasible if any frozen joint starts outside its range
        for name, i in self._jid.items():
            if i != self._free_base and m.jnt_limited[i]:
                lo, hi = m.jnt_range[i]
                a = self._qa[name]
                q[a] = min(max(q[a], lo), hi)
        return q

    def solve(self, target, base_qpos, joints: dict) -> IKResult:
        """Solve for yaw, lift and arm that put the grasp centre at `target` (world xyz).

        base_qpos: the 7 free-joint values of the live base (x, y, z, quaternion w x y z).
        joints: live lift and arm-section values by MJCF name.
        """
        t0 = time.perf_counter()
        cfg, task = self._cfg, self._task
        cfg.update(self._start_q(base_qpos, joints))
        task.set_target(mink.SE3.from_translation(np.asarray(target, dtype=float)))
        iterations = 0
        error = np.inf
        try:
            for iterations in range(self.max_iterations + 1):
                error = float(np.linalg.norm(task.compute_error(cfg)[:3]))
                if error < self.tolerance or iterations == self.max_iterations:
                    break
                v = mink.solve_ik(cfg, [task, self._eq_task], 1.0, "daqp", damping=self.damping,
                                  limits=self._limits)
                cfg.integrate_inplace(v, 1.0)
        except Exception:  # infeasible QP and the like: report as not reached
            error = float("inf")
        q = cfg.q
        w, x, y, z = q[3:7]
        yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
        lift = float(q[self._qa["joint_lift"]])
        arm = float(sum(q[self._qa[n]] for n in ARM_JOINTS))
        eps = 1e-3
        at_limit = (arm >= self._arm_max - eps or arm <= eps
                    or lift >= self._lift_range[1] - eps or lift <= self._lift_range[0] + eps)
        stat = IKStat(iterations=iterations, residual=error, ms=(time.perf_counter() - t0) * 1e3,
                      converged=error < self.tolerance)
        return IKResult(yaw=yaw, lift=lift, arm=arm, reached=error <= self.fail_residual,
                        at_limit=bool(at_limit), stat=stat)
