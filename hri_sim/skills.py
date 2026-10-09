"""Skills: the public, blocking functions that express what the robot does (gesture, pick).

Each skill returns a SkillResult and never raises on a task failure. A successful pick ends the episode:
the simulation freezes with the cylinder lifted and the last frame stays in the viewer until
`close_window()` (or the user closes it).

The gripper hangs down (wrist pitch -1.57) at all times. The base turns only with the lift at carry height,
where the hanging gripper clears the table and both cylinders; the arm may stay extended while it turns.
"""
import math
import time
from dataclasses import dataclass, field

import numpy as np

from .config import SkillConfig
from .ik import IKResult, IKSolver
from .robot import Robot, wrap_angle
from .sim import SkillInterrupt, StretchSim


@dataclass
class SkillResult:
    """Outcome of a skill. `reason` is empty when ok, otherwise one of: unknown_target, unreachable, ik_failed,
    no_grasp, collision, timeout, aborted, episode_over, window_closed."""

    ok: bool
    skill: str
    target: str = None
    reason: str = ""
    sim_time: float = 0.0  # simulated seconds the skill took
    wall_time: float = 0.0
    ik: list = field(default_factory=list)  # IKStat of every solve (iterations, residual, ms)
    info: dict = field(default_factory=dict)

    def __str__(self):
        ik_ms = f", IK {sum(s.ms for s in self.ik):.1f} ms in {len(self.ik)} solves" if self.ik else ""
        status = "ok" if self.ok else f"FAILED ({self.reason})"
        return f"{self.skill}({self.target}): {status}, sim {self.sim_time:.1f} s{ik_ms}"


class Skills:
    def __init__(self, sim: StretchSim, config: SkillConfig = None):
        self.sim = sim
        self.cfg = config or SkillConfig()
        self.robot = Robot(sim)
        self.ik = IKSolver(
            sim.scene.model_path, wrist_pitch=sim.motion.wrist_pitch, tolerance=self.cfg.ik_tolerance,
            max_iterations=self.cfg.ik_max_iterations, damping=self.cfg.ik_damping,
            fail_residual=self.cfg.ik_fail_residual,
        )

    # ------------------------------------------------------------------ public skills
    def gesture(self, color: str, fraction: float = None, hold_s: float = None) -> SkillResult:
        """Show which cylinder the robot means to pick: turn toward it while closing the gripper, extend the
        arm until the gripper hangs over it, then lower the lift `fraction` of the way down toward the grasp
        height (0.5 is halfway). The gripper stays closed. Holds the pose for `hold_s` seconds, then returns."""
        cfg = self.cfg
        fraction = cfg.gesture_fraction if fraction is None else fraction
        hold_s = cfg.gesture_hold_s if hold_s is None else hold_s
        return self._run("gesture", color, lambda res: self._gesture(res, color, fraction, hold_s))

    def pick(self, color: str) -> SkillResult:
        """Pick a cylinder up (top-down grasp, lift 0.15 m). On success the simulation freezes."""
        return self._run("pick", color, lambda res: self._pick(res, color))

    def reset(self):
        """Start a new episode."""
        self.sim.reset()

    def hold_final_frame(self):
        """Keep the viewer alive (camera still draggable) until the window is closed. Blocks."""
        self.sim.hold_final_frame()

    def close_window(self):
        """Close the viewer window."""
        self.sim.close_window()

    def abort(self):
        """Ask the running skill to stop (thread-safe)."""
        self.sim.abort()

    # ------------------------------------------------------------------ skill wrapper
    def _run(self, skill: str, target: str, body) -> SkillResult:
        sim = self.sim
        res = SkillResult(False, skill, target)
        if target not in sim.objects:
            res.reason = "unknown_target"
            return res
        if sim.episode_over:
            res.reason = "episode_over"
            return res
        if sim.viewer is not None and not sim.viewer.is_running():
            sim.window_open = False
            res.reason = "window_closed"
            return res
        sim.clear_abort()
        violations_before = dict(sim.contact_violations)
        t_wall, t_sim = time.perf_counter(), sim.time
        try:
            body(res)
        except SkillInterrupt as stop:
            res.ok = False
            res.reason = stop.reason
        finally:
            self.robot.stop_wheels()
            sim.allowed_contact = None
        res.sim_time = sim.time - t_sim
        res.wall_time = time.perf_counter() - t_wall
        new = {k: v - violations_before.get(k, 0) for k, v in sim.contact_violations.items()
               if v > violations_before.get(k, 0)}
        if new:
            res.info["unwanted_contacts"] = new
            if res.ok:
                res.ok = False
                res.reason = "collision"
        return res

    # ------------------------------------------------------------------ shared helpers
    def _solve(self, res: SkillResult, xyz) -> IKResult:
        base, joints = self.sim.ik_state()
        r = self.ik.solve(xyz, base, joints)
        res.ik.append(r.stat)
        return r

    def _grasp_xyz(self, color: str, dz: float = 0.0):
        p = self.sim.object_position(color)
        return [float(p[0]), float(p[1]), self.sim.scene.table_top_z + self.cfg.grasp_dz + dz]

    def _check_reached(self, res: SkillResult, r: IKResult) -> bool:
        if r.reached:
            return True
        res.reason = "unreachable" if r.at_limit else "ik_failed"
        return False

    def _yaw_goal(self, r: IKResult) -> float:
        """The IK yaw, unwrapped to the turn nearest to the current yaw."""
        return self.sim.yaw + wrap_angle(r.yaw - self.sim.yaw)

    def _needs_turn(self, yaw_goal: float) -> bool:
        return abs(wrap_angle(yaw_goal - self.sim.yaw)) > math.radians(self.cfg.no_turn_deg)

    def _turn(self, res: SkillResult, yaw_goal: float, joints: dict):
        """Lift to carry height if needed, then turn the base; `joints` (the gripper) move during the turn.
        Joints already at their command are left alone."""
        rb, sim = self.robot, self.sim
        joints = {k: v for k, v in joints.items() if abs(sim.ctrl(k) - v) > 1e-6}
        if not rb.at_carry_height():
            rb.move({"lift": sim.motion.carry_lift}, name="lift_to_carry")
        rb.turn_to(yaw_goal, joints=joints)
        res.info["turn_error_deg"] = math.degrees(wrap_angle(yaw_goal - sim.yaw))

    # ------------------------------------------------------------------ gesture
    def _gesture(self, res, color, fraction, hold_s):
        sim, rb, mo, cfg = self.sim, self.robot, self.sim.motion, self.cfg
        rest = {c: sim.object_position(c) for c in sim.objects}
        r = self._solve(res, self._grasp_xyz(color))  # the grasp pose: yaw, arm extension and lift of the grasp
        if not self._check_reached(res, r):
            return
        # lift goal: `fraction` of the way down from carry height to the grasp lift, but never lower than
        # `gesture_min_clearance` above the cylinder top (the closed fingertips would touch it)
        grasp_z = self._grasp_xyz(color)[2]
        lift_floor = r.lift + (sim.scene.cylinder_top_z + cfg.gesture_min_clearance - grasp_z)
        lift_goal = max(mo.carry_lift - fraction * (mo.carry_lift - r.lift), lift_floor)

        close = {"gripper": mo.gripper_closed}
        yaw_goal = self._yaw_goal(r)
        if self._needs_turn(yaw_goal):
            self._turn(res, yaw_goal, close)  # the gripper closes while the base turns
        elif abs(sim.ctrl("gripper") - mo.gripper_closed) > 1e-6:
            rb.move(close, trim=(), name="close_gripper")
        if abs(sim.joint("arm") - r.arm) > cfg.arm_match_tol:
            rb.move({"arm": r.arm}, name="extend_arm")
        if abs(sim.joint("lift") - lift_goal) > cfg.lift_match_tol:
            rb.move({"lift": lift_goal}, name="lower_lift")
        sim.run_for(hold_s)

        # how well does it point, and does the gripper hang over the cylinder?
        x, y, yaw = sim.base_pose()
        axis = np.array([math.sin(yaw), -math.cos(yaw)])  # arm direction: the base's -y axis in the world
        cyl, gc = sim.object_position(color), sim.grasp_center()
        lateral = abs(axis[0] * (cyl[1] - gc[1]) - axis[1] * (cyl[0] - gc[0]))
        res.info.update(
            fraction=fraction, fraction_applied=(mo.carry_lift - lift_goal) / (mo.carry_lift - r.lift),
            arm=sim.joint("arm"), arm_pick=r.arm, lift=sim.joint("lift"), lift_goal=lift_goal,
            yaw_deg=math.degrees(yaw),
            pointing_error_deg=math.degrees(math.atan2(lateral, float(np.dot(cyl[:2] - np.array([x, y]), axis)))),
            hover_offset=float(np.linalg.norm(gc[:2] - cyl[:2])),  # horizontal distance, gripper to cylinder
            height_above_cylinder=float(gc[2] - sim.scene.cylinder_top_z),
            max_cylinder_displacement=max(float(np.linalg.norm(sim.object_position(c) - rest[c])) for c in sim.objects),
        )
        res.ok = True

    # ------------------------------------------------------------------ pick
    def _pick(self, res, color):
        sim, rb, mo, cfg = self.sim, self.robot, self.sim.motion, self.cfg
        r_pre = self._solve(res, self._grasp_xyz(color, cfg.pre_grasp_dz))
        r_grasp = self._solve(res, self._grasp_xyz(color))
        if not (self._check_reached(res, r_pre) and self._check_reached(res, r_grasp)):
            return

        open_gripper = {"gripper": mo.gripper_open}
        yaw_goal = self._yaw_goal(r_grasp)
        if self._needs_turn(yaw_goal):  # the start, or the other cylinder: lift to carry height, turn, open
            self._turn(res, yaw_goal, open_gripper)
        elif abs(sim.ctrl("gripper") - mo.gripper_open) > 1e-6:  # already facing it (after a gesture): just open
            rb.move(open_gripper, trim=(), name="open_gripper")
        if abs(sim.joint("arm") - r_pre.arm) > cfg.arm_match_tol:  # bring the arm out without lowering the lift
            rb.move({"lift": max(sim.joint("lift"), r_pre.lift), "arm": r_pre.arm}, name="pre_grasp")

        # the base creeps a few millimetres per turn: solve again from the live pose and the live cylinder
        r_live = self._solve(res, self._grasp_xyz(color))
        if not self._check_reached(res, r_live):
            return
        sim.allowed_contact = color
        rb.move({"lift": r_live.lift, "arm": r_live.arm}, name="descend")
        res.info["grasp_centre_error_mm"] = float(
            np.linalg.norm(sim.grasp_center() - np.array(self._grasp_xyz(color))) * 1000)
        rb.move({"gripper": cfg.squeeze_ctrl}, trim=(), name="close_gripper")
        sim.step(cfg.settle_after_close_steps)
        z_before = float(sim.object_position(color)[2])
        rb.move({"lift": r_live.lift + cfg.lift_after_grasp}, trim=(), name="lift_up")
        sim.step(cfg.settle_after_lift_steps)

        pos = sim.object_position(color)
        rise = float(pos[2]) - z_before
        lateral = float(np.linalg.norm(pos[:2] - sim.grasp_center()[:2]))
        touching = sim.fingers_touching(color)
        res.info.update(rise=rise, fingers_touching=touching, lateral_from_gripper=lateral,
                        yaw_deg=math.degrees(sim.yaw))
        if touching == 2 and rise >= cfg.min_rise and lateral <= cfg.max_lateral_from_gripper:
            res.ok = True
            sim.freeze()
        else:
            res.reason = "no_grasp"
