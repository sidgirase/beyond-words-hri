"""StretchSim: owns the MuJoCo model and data, steps physics, drives the passive viewer.

One process, no IPC: object poses, contacts and resets are all directly available. Stepping can be paced to
real time (default, for watching) or run flat out (for checks). The viewer is the stock MuJoCo passive viewer.
"""
import math
import threading
import time

import mujoco
import numpy as np

from .config import MotionConfig, SceneConfig
from .scene import build_model

try:  # the viewer needs glfw / OpenGL; headless runs do not
    import mujoco.viewer as _mj_viewer
except Exception:  # pragma: no cover
    _mj_viewer = None

ARM_JOINTS = ("joint_arm_l0", "joint_arm_l1", "joint_arm_l2", "joint_arm_l3")
FINGER_JOINTS = ("joint_gripper_finger_left_open", "joint_gripper_finger_right_open")
JOINTS = ("joint_lift", *ARM_JOINTS, "joint_wrist_pitch", "joint_gripper_slide", *FINGER_JOINTS)
SHORT_JOINT = {"lift": "joint_lift", "gripper": "joint_gripper_slide"}  # "arm" is the sum of ARM_JOINTS
FINGER_BODIES = ("rubber_tip_left", "rubber_tip_right")

# default viewer camera: looking at the table and the robot from the side
CAMERA = dict(lookat=(0.0, -0.45, 0.6), distance=1.9, azimuth=150.0, elevation=-28.0)


class SkillInterrupt(Exception):
    """Raised inside a skill to stop it early. `reason` is one of aborted, window_closed, timeout."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class StretchSim:
    def __init__(
        self,
        scene: SceneConfig = None,
        motion: MotionConfig = None,
        headless: bool = False,
        realtime: bool = True,
    ):
        self.scene = scene or SceneConfig()
        self.motion = motion or MotionConfig()
        self.headless = headless
        self.realtime = realtime  # pace to wall-clock time (headless runs can be paced too)

        self.model = build_model(self.scene)
        self.data = mujoco.MjData(self.model)
        m = self.model

        def jid(name):
            return mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, name)

        def bid(name):
            return mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, name)

        self._jq = {n: int(m.jnt_qposadr[jid(n)]) for n in JOINTS}
        self._jv = {n: int(m.jnt_dofadr[jid(n)]) for n in JOINTS}
        self.act = {
            n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n)
            for n in ("left_wheel_vel", "right_wheel_vel", "lift", "arm", "wrist_pitch", "gripper")
        }
        self.base_body = bid("base_link")
        # the robot's free joint is the first joint, so qpos[0:7] is the base pose (x, y, z, quaternion w x y z)
        assert m.jnt_type[0] == mujoco.mjtJoint.mjJNT_FREE and m.jnt_bodyid[0] == self.base_body
        self.grasp_body = bid("link_grasp_center")
        self.finger_bodies = tuple(bid(n) for n in FINGER_BODIES)

        self.objects = list(self.scene.cylinders)
        self._obj_body = {c: bid(f"cyl_{c}") for c in self.objects}
        self._obj_qadr = {c: int(m.jnt_qposadr[m.body_jntadr[self._obj_body[c]]]) for c in self.objects}
        self._obj_vadr = {c: int(m.jnt_dofadr[m.body_jntadr[self._obj_body[c]]]) for c in self.objects}
        self._obj_geom = {c: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"cyl_{c}_geom") for c in self.objects}

        # contact classification: 0 other (floor), 1 robot, 2 table, 3 + i the i-th cylinder
        table_body = bid("table")
        kind = np.zeros(m.ngeom, dtype=int)
        for g in range(m.ngeom):
            b = int(m.geom_bodyid[g])
            if m.body_rootid[b] == self.base_body:
                kind[g] = 1
            elif b == table_body:
                kind[g] = 2
            else:
                for i, c in enumerate(self.objects):
                    if b == self._obj_body[c]:
                        kind[g] = 3 + i
        self._geom_kind = kind
        self.allowed_contact = None  # cylinder name the robot may touch right now (during a grasp)
        self.contact_violations = {}

        self.frozen = False
        self.episode_over = False
        self.window_open = False
        self._close_requested = False
        self._abort = threading.Event()
        self.events = []
        self.rest_positions = {}
        self._nstep = 0
        self._anchor_wall = time.perf_counter()
        self._anchor_sim = 0.0

        self.recorder = None  # a VideoRecorder, when one is attached
        self.viewer = None
        if not headless:
            if _mj_viewer is None:
                raise RuntimeError("mujoco.viewer is not available; use headless=True")
            self.viewer = _mj_viewer.launch_passive(
                self.model, self.data, show_left_ui=False, show_right_ui=False
            )
            self.window_open = True
            cam = self.viewer.cam
            cam.lookat[:] = CAMERA["lookat"]
            cam.distance = CAMERA["distance"]
            cam.azimuth = CAMERA["azimuth"]
            cam.elevation = CAMERA["elevation"]

        self.reset()

    # ------------------------------------------------------------------ setup helpers
    def reset(self):
        """Start a new episode: carry pose, cylinders back at their default positions, physics settled."""
        if self.headless is False and self.viewer is not None and not self.viewer.is_running():
            self.window_open = False
            raise RuntimeError("The viewer window is closed; create a new StretchSim to get a window again.")
        m, d, mo = self.model, self.data, self.motion
        mujoco.mj_resetData(m, d)
        d.qpos[self._jq["joint_lift"]] = mo.carry_lift
        d.qpos[self._jq["joint_wrist_pitch"]] = mo.wrist_pitch
        d.qpos[self._jq["joint_gripper_slide"]] = mo.gripper_open
        # the finger joints follow the gripper slide through an equality constraint (factor 10)
        d.qpos[self._jq[FINGER_JOINTS[0]]] = 10 * mo.gripper_open
        d.qpos[self._jq[FINGER_JOINTS[1]]] = 10 * mo.gripper_open
        d.ctrl[self.act["lift"]] = mo.carry_lift
        d.ctrl[self.act["arm"]] = 0.0
        d.ctrl[self.act["wrist_pitch"]] = mo.wrist_pitch
        d.ctrl[self.act["gripper"]] = mo.gripper_open
        mujoco.mj_forward(m, d)
        for _ in range(500):  # 1 s of sim time to settle, not paced
            mujoco.mj_step(m, d)
        self.frozen = False
        self.episode_over = False
        self.allowed_contact = None
        self.contact_violations = {}
        self.events = []
        self._abort.clear()
        self.rest_positions = {c: self.object_position(c) for c in self.objects}
        self._anchor_wall, self._anchor_sim = time.perf_counter(), d.time
        self._sync(raise_if_closed=False)

    # ------------------------------------------------------------------ stepping
    def step(self, n: int = 1):
        """Advance physics by n steps (no-op after freeze). Raises SkillInterrupt on abort or window close."""
        if self.frozen:
            return
        sync_every = self.motion.viewer_sync_steps
        for _ in range(n):
            if self._abort.is_set():
                raise SkillInterrupt("aborted")
            mujoco.mj_step(self.model, self.data)
            self._monitor_contacts()
            if self.recorder is not None:
                self.recorder.maybe_capture()
            self._nstep += 1
            if self.viewer is not None and self._nstep % sync_every == 0:
                self._sync()
        self._pace()

    def run_for(self, seconds: float):
        """Step for a given amount of simulated time, in control-tick sized chunks."""
        tick = self.motion.ctrl_tick_steps
        n = int(round(seconds / self.model.opt.timestep))
        while n > 0:
            k = min(tick, n)
            self.step(k)
            n -= k

    def _pace(self):
        if not self.realtime:
            return
        target = self._anchor_wall + (self.data.time - self._anchor_sim)
        delay = target - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        elif delay < -self.motion.realtime_resync_s:  # fell behind (a pause, a slow frame): do not run fast to catch up
            self._anchor_wall, self._anchor_sim = time.perf_counter(), self.data.time

    def _sync(self, raise_if_closed: bool = True):
        if self.viewer is None:
            return
        if not self.viewer.is_running():
            self.window_open = False
            if raise_if_closed:
                raise SkillInterrupt("window_closed")
            return
        self.viewer.sync()

    # ------------------------------------------------------------------ contact monitor
    def _monitor_contacts(self):
        d = self.data
        n = d.ncon
        if n == 0:
            return
        g1 = d.contact.geom1
        g2 = d.contact.geom2
        k1 = self._geom_kind[g1]
        k2 = self._geom_kind[g2]
        # only pairs that involve the robot and the table or a cylinder can be violations
        robot_hit = ((k1 == 1) & (k2 >= 2)) | ((k2 == 1) & (k1 >= 2))
        if not robot_hit.any():
            return
        for i in np.nonzero(robot_hit)[0]:
            a, b = (int(g1[i]), int(g2[i])) if k1[i] == 1 else (int(g2[i]), int(g1[i]))
            other_kind = int(self._geom_kind[b])
            if other_kind >= 3 and self.objects[other_kind - 3] == self.allowed_contact:
                continue
            robot_body = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, int(self.model.geom_bodyid[a]))
            other = "table" if other_kind == 2 else f"cyl_{self.objects[other_kind - 3]}"
            key = f"{robot_body}|{other}"
            self.contact_violations[key] = self.contact_violations.get(key, 0) + 1

    # ------------------------------------------------------------------ queries
    @property
    def time(self) -> float:
        return float(self.data.time)

    def object_position(self, color: str) -> np.ndarray:
        return self.data.xpos[self._obj_body[color]].copy()

    def set_object_position(self, color: str, x: float, y: float):
        """Teleport a cylinder upright at (x, y) on the table and let it settle (used by checks)."""
        a, v = self._obj_qadr[color], self._obj_vadr[color]
        z = self.scene.table_top_z + self.scene.cylinder_height / 2 + 0.002
        self.data.qpos[a:a + 7] = [x, y, z, 1, 0, 0, 0]
        self.data.qvel[v:v + 6] = 0
        mujoco.mj_forward(self.model, self.data)
        for _ in range(300):
            mujoco.mj_step(self.model, self.data)
        self.rest_positions[color] = self.object_position(color)

    def base_pose(self):
        """(x, y, yaw) of the base in the world."""
        x, y = self.data.xpos[self.base_body][:2]
        R = self.data.xmat[self.base_body].reshape(3, 3)
        return float(x), float(y), float(math.atan2(R[1, 0], R[0, 0]))

    @property
    def yaw(self) -> float:
        return self.base_pose()[2]

    def grasp_center(self) -> np.ndarray:
        return self.data.xpos[self.grasp_body].copy()

    def joint(self, name: str) -> float:
        """Joint value by short name: lift, arm (sum of the four sections) or gripper (slide)."""
        if name == "arm":
            return float(sum(self.data.qpos[self._jq[j]] for j in ARM_JOINTS))
        return float(self.data.qpos[self._jq[SHORT_JOINT[name]]])

    def joint_speed(self, name: str) -> float:
        if name == "arm":
            return float(self.data.qvel[self._jv["joint_arm_l0"]] * 4)
        return float(self.data.qvel[self._jv[SHORT_JOINT[name]]])

    def ctrl(self, name: str) -> float:
        return float(self.data.ctrl[self.act[name]])

    def set_ctrl(self, name: str, value: float):
        self.data.ctrl[self.act[name]] = value

    def yaw_rate(self) -> float:
        """Base angular velocity about z (the free joint's angular dofs are in the body frame)."""
        return float(self.data.qvel[5])

    def fingers_touching(self, color: str) -> int:
        """How many of the two rubber fingertips touch the cylinder right now."""
        gid = self._obj_geom[color]
        hit = set()
        d = self.data
        for i in range(d.ncon):
            c = d.contact[i]
            other = c.geom2 if c.geom1 == gid else (c.geom1 if c.geom2 == gid else None)
            if other is not None:
                b = int(self.model.geom_bodyid[other])
                if b in self.finger_bodies:
                    hit.add(b)
        return len(hit)

    def ik_state(self):
        """Live base pose (7 values) and the lift and arm joint values by MJCF name: the input of IKSolver.solve."""
        base = self.data.qpos[:7].copy()
        joints = {n: float(self.data.qpos[self._jq[n]]) for n in ("joint_lift", *ARM_JOINTS)}
        return base, joints

    def log_event(self, name: str, t0: float, t1: float, **info):
        self.events.append({"name": name, "t0": t0, "t1": t1, **info})

    # ------------------------------------------------------------------ episode end and window
    def freeze(self):
        """Stop the simulation: no more stepping, the last frame stays in the viewer."""
        self.frozen = True
        self.episode_over = True
        self._sync(raise_if_closed=False)

    def abort(self):
        """Ask the running skill to stop (thread-safe)."""
        self._abort.set()

    def clear_abort(self):
        self._abort.clear()

    def hold_final_frame(self):
        """Block, keeping the viewer responsive (camera can be moved), until the window is closed."""
        if self.viewer is None:
            return
        while not self._close_requested and self.viewer.is_running():
            self.viewer.sync()
            time.sleep(0.02)
        self.window_open = False

    def close_window(self):
        """Close the viewer window (safe to call from another thread)."""
        self._close_requested = True
        if self.viewer is not None:
            try:
                self.viewer.close()
            except Exception:  # already closed
                pass
        self.window_open = False
