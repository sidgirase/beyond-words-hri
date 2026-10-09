"""M1: scene, sim loop, viewer, contact monitor.

    python scripts/check_scene.py            headless checks only
    python scripts/check_scene.py --viewer   also opens the viewer window for a few seconds (real-time pacing)
"""
import math
import sys
import time

import _common  # noqa: F401  (puts src on sys.path so hri_sim can be imported)
from _common import Checks

import mujoco
import numpy as np

from hri_sim import SceneConfig, Skills, StretchSim
from hri_sim.robot import Robot


def main() -> int:
    c = Checks("check_scene (M1)")
    cfg = SceneConfig()

    sim = StretchSim(cfg, headless=True, realtime=False)
    m = sim.model
    c.check("robot model loaded from the submodule path", cfg.model_path.exists(), str(cfg.model_path.name))
    c.check("lidar and other sensors disabled", bool(m.opt.disableflags & mujoco.mjtDisableBit.mjDSBL_SENSOR))
    c.check("both cylinders exist", set(sim.objects) == {"blue", "green"})
    arm = [sim.data.qpos[sim._jq[j]] for j in ("joint_arm_l0", "joint_arm_l1", "joint_arm_l2", "joint_arm_l3")]
    c.check("arm sections stay equal", np.ptp(arm) < 1e-4, f"spread {np.ptp(arm):.1e}")

    # idle stability, 10 s of sim time
    p0 = {k: sim.object_position(k) for k in sim.objects}
    b0 = np.array(sim.base_pose()[:2])
    t = time.perf_counter()
    sim.step(5000)
    wall = time.perf_counter() - t
    drift = max(float(np.linalg.norm(sim.object_position(k) - p0[k])) for k in sim.objects) * 1000
    base_drift = float(np.linalg.norm(np.array(sim.base_pose()[:2]) - b0)) * 1000
    c.check("idle 10 s: cylinders move under 2 mm", drift < 2, f"{drift:.3f} mm")
    c.check("idle 10 s: base moves under 5 mm", base_drift < 5, f"{base_drift:.3f} mm")
    c.check("no unwanted contacts while idle", not sim.contact_violations, str(sim.contact_violations))
    c.check("headless unpaced speed at least 5x real time", 10 / wall >= 5, f"{10 / wall:.0f}x")

    # real-time pacing without a viewer: 3 s of sim should take about 3 s of wall time
    paced = StretchSim(cfg, headless=True, realtime=True)
    t = time.perf_counter()
    paced.run_for(3.0)
    wall = time.perf_counter() - t
    c.check("real-time pacing: 3 s of sim in 2.9 to 3.4 s of wall time", 2.9 <= wall <= 3.4, f"{wall:.2f} s")

    # yaw sweep in the carry pose: no robot-table contact at any step
    rb = Robot(sim)
    sim.reset()
    for deg in (40, -40, 0):
        rb.turn_to(math.radians(deg))
    c.check("yaw sweep +-40 deg in the carry pose: no contacts at any step", not sim.contact_violations,
            str(sim.contact_violations))
    c.check("yaw sweep ends within 1 deg of 0", abs(math.degrees(sim.yaw)) < 1.0, f"{math.degrees(sim.yaw):.2f} deg")

    # yaw sweep with the arm extended over the table: the base may turn at carry height with the arm out
    sim.reset()
    sk = Skills(sim)
    g = sk.gesture("blue", hold_s=0.2)
    c.check("gesture used for the extended-arm sweep succeeded", g.ok, g.reason)
    sk.robot.move({"lift": sim.motion.carry_lift})
    c.check("arm is still extended for the sweep", sim.joint("arm") > 0.3, f"{sim.joint('arm'):.3f} m")
    for deg in (40, -40, 0):
        sk.robot.turn_to(math.radians(deg))
    c.check("yaw sweep +-40 deg at carry height with the arm extended: no contacts at any step",
            not sim.contact_violations, str(sim.contact_violations))

    # the monitor must see a real collision: swing the extended hanging gripper down into the table
    bad = StretchSim(cfg, headless=True, realtime=False)
    brb = Robot(bad)
    brb.move({"arm": 0.45})
    try:
        brb.move({"lift": 0.35})
    except Exception:
        pass
    c.check("contact monitor flags a deliberate gripper-table collision", any("|table" in k for k in bad.contact_violations),
            str(bad.contact_violations))

    if "--viewer" in sys.argv:
        v = StretchSim(cfg, headless=False, realtime=True)
        c.check("viewer window opened", v.window_open and v.viewer.is_running())
        t = time.perf_counter()
        v.run_for(3.0)
        wall = time.perf_counter() - t
        c.check("viewer paced at real time (3 s sim in 2.9 to 3.5 s wall)", 2.9 <= wall <= 3.5, f"{wall:.2f} s")
        v.close_window()
        c.check("close_window closes the viewer", not v.viewer.is_running())

    return c.report()


if __name__ == "__main__":
    sys.exit(main())
