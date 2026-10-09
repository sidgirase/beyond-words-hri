"""Motion executor: turns joint targets into rate-limited servo commands and wheel velocities.

Joints are position servos (lift, arm, gripper), so a move ramps `ctrl` toward the target at a speed limit
and waits until the moved joints have stopped; the lift and arm then get a small trim because those servos
settle a few millimetres short under load. The base turns in place with wheel velocities and a feedback loop
on the measured yaw; joints can move during the turn (the gripper closes or opens while the base rotates).
"""
import math

import numpy as np

from .sim import SkillInterrupt, StretchSim


def wrap_angle(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


class Robot:
    def __init__(self, sim: StretchSim):
        self.sim = sim
        self.cfg = sim.motion
        m = sim.model
        self._ctrl_range = {
            n: (float(m.actuator_ctrlrange[a][0]), float(m.actuator_ctrlrange[a][1]))
            for n, a in sim.act.items()
        }

    def at_carry_height(self) -> bool:
        """The hanging gripper clears the table and both cylinders, so the base may turn."""
        return self.sim.joint("lift") >= self.cfg.carry_lift - 0.02

    # ------------------------------------------------------------------ joint moves
    def move(self, targets: dict, trim=("lift", "arm"), name: str = "move") -> float:
        """Move joints (lift, arm, gripper) together to the given values.

        Returns the elapsed sim time. Raises SkillInterrupt('timeout') if the joints never settle.
        The move is logged in `sim.events` under `name`, or not at all when `name` is None.
        """
        sim, cfg = self.sim, self.cfg
        t0 = sim.time
        goal = {k: self._clip(k, v) for k, v in targets.items()}
        cur = {k: sim.ctrl(k) for k in goal}
        calm = 0
        trims = 0
        while sim.time - t0 < cfg.move_timeout_s:
            self._ramp(cur, goal)
            sim.step(cfg.ctrl_tick_steps)
            if all(abs(cur[k] - goal[k]) < 1e-9 for k in goal):
                if all(abs(sim.joint_speed(k)) < cfg.settle_speed for k in goal):
                    calm += 1
                else:
                    calm = 0
                if calm >= cfg.settle_ticks:
                    bad = [k for k in goal if k in trim and abs(sim.joint(k) - targets[k]) > cfg.trim_tolerance]
                    if not bad or trims >= cfg.trim_max:
                        if name is not None:
                            sim.log_event(name, t0, sim.time, targets=dict(targets))
                        return sim.time - t0
                    for k in bad:
                        goal[k] = self._clip(k, goal[k] + (targets[k] - sim.joint(k)))
                    trims += 1
                    calm = 0
        raise SkillInterrupt("timeout")

    def _ramp(self, cur: dict, goal: dict):
        """One control tick of the speed-limited ramp of ctrl values toward their goals."""
        dt = self.sim.model.opt.timestep * self.cfg.ctrl_tick_steps
        for k, v in goal.items():
            step = self.cfg.rates[k] * dt
            cur[k] += float(np.clip(v - cur[k], -step, step))
            self.sim.set_ctrl(k, cur[k])

    def _clip(self, name: str, value: float) -> float:
        lo, hi = self._ctrl_range[name]
        return float(min(max(value, lo), hi))

    # ------------------------------------------------------------------ base rotation
    def turn_to(self, yaw: float, joints: dict = None) -> float:
        """Rotate the base in place to a world yaw using the wheels and feedback on the measured yaw.

        `joints` (for example the gripper) move at the same time; they are given time to settle afterwards.
        """
        sim, cfg = self.sim, self.cfg
        t0 = sim.time
        tol = math.radians(cfg.yaw_tolerance_deg)
        goal = {k: self._clip(k, v) for k, v in (joints or {}).items()}
        cur = {k: sim.ctrl(k) for k in goal}
        still_since = None
        try:
            while sim.time - t0 < cfg.yaw_timeout_s:
                err = wrap_angle(yaw - sim.yaw)
                if abs(err) < tol:
                    u = 0.0
                else:
                    u = float(np.clip(cfg.yaw_gain * err, -cfg.yaw_ctrl_max, cfg.yaw_ctrl_max))
                    if abs(u) < cfg.yaw_ctrl_min:
                        u = math.copysign(cfg.yaw_ctrl_min, err)
                # positive ctrl on both wheels drives forward; opposite signs turn in place (left wheel
                # backward, right wheel forward turns counter-clockwise, i.e. positive yaw)
                sim.set_ctrl("left_wheel_vel", -u)
                sim.set_ctrl("right_wheel_vel", u)
                self._ramp(cur, goal)
                sim.step(cfg.ctrl_tick_steps)
                if u == 0.0 and abs(sim.yaw_rate()) < 0.01:
                    still_since = still_since if still_since is not None else sim.time
                    if sim.time - still_since > 0.1:
                        break
                else:
                    still_since = None
            else:
                raise SkillInterrupt("timeout")
        finally:
            self.stop_wheels()
            if not sim.frozen:
                try:
                    sim.step(100)  # let the wheels stop
                except SkillInterrupt:
                    pass
        if goal:
            self.move(joints, trim=(), name=None)  # settle the joints that moved during the turn
        sim.log_event("turn", t0, sim.time, target_yaw=yaw, joints=dict(joints or {}))
        return sim.time - t0

    def stop_wheels(self):
        self.sim.set_ctrl("left_wheel_vel", 0.0)
        self.sim.set_ctrl("right_wheel_vel", 0.0)
