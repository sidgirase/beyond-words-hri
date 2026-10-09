"""M2 and M3: inverse kinematics and picking.

    python scripts/check_pick.py            full run (about 2 minutes headless)
    python scripts/check_pick.py --quick    nominal picks only
"""
import math
import sys

import _common  # noqa: F401  (puts src on sys.path so hri_sim can be imported)
from _common import Checks

import numpy as np

from hri_sim import SceneConfig, Skills, StretchSim
from hri_sim.scene import cylinder_home_xy


def trial(sim, sk, color, x=None, y=None):
    sim.reset()
    if x is not None:
        sim.set_object_position(color, x, y)
    return sk.pick(color)


def main() -> int:
    quick = "--quick" in sys.argv
    c = Checks("check_pick (M2, M3)")
    cfg = SceneConfig()
    sim = StretchSim(cfg, headless=True, realtime=False)
    sk = Skills(sim)

    # ---------------- M2: IK ----------------
    base, joints = sim.ik_state()
    times = []
    for color in sim.objects:
        p = sim.object_position(color)
        for dz in (0.0, sk.cfg.pre_grasp_dz):
            r = sk.ik.solve([p[0], p[1], cfg.table_top_z + sk.cfg.grasp_dz + dz], base, joints)
            times.append(r.stat.ms)
            c.check(f"IK {color} dz={dz:.2f}: converged under 1 mm", r.stat.converged and r.stat.residual < 1e-3,
                    f"residual {r.stat.residual * 1000:.3f} mm, {r.stat.iterations} iterations, {r.stat.ms:.2f} ms")
    far = sk.ik.solve([0.0, -0.95, cfg.table_top_z + 0.06], base, joints)
    c.check("IK for a target 0.95 m away is reported as not reached", not far.reached,
            f"residual {far.stat.residual * 1000:.0f} mm, {far.stat.ms:.1f} ms")
    c.check("IK median time under 5 ms", float(np.median(times)) < 5.0, f"median {np.median(times):.2f} ms")

    # ---------------- M3: nominal picks, each colour in its own run ----------------
    for color in sim.objects:
        sim.reset()
        r = sk.pick(color)
        c.check(f"pick {color}: ok", r.ok, r.reason)
        i = r.info
        c.check(f"pick {color}: both fingers touching, rise at least 0.10 m",
                i.get("fingers_touching") == 2 and i.get("rise", 0) >= 0.10,
                f"fingers {i.get('fingers_touching')}, rise {i.get('rise', 0):.3f} m")
        c.check(f"pick {color}: base turned to within 0.5 deg", abs(i.get("turn_error_deg", 99)) <= 0.5,
                f"{i.get('turn_error_deg', 99):.2f} deg")
        c.check(f"pick {color}: grasp centre within 6 mm of the target", i.get("grasp_centre_error_mm", 99) <= 6.0,
                f"{i.get('grasp_centre_error_mm', 99):.1f} mm")
        c.check(f"pick {color}: simulation frozen, episode over", sim.frozen and sim.episode_over)
        r2 = sk.gesture(color)
        c.check(f"pick {color}: a later skill returns episode_over", (not r2.ok) and r2.reason == "episode_over", r2.reason)
        c.check(f"pick {color}: no unwanted contacts", not sim.contact_violations, str(sim.contact_violations))
        other = [o for o in sim.objects if o != color][0]
        moved = float(np.linalg.norm(sim.object_position(other) - sim.rest_positions[other])) * 1000
        c.check(f"pick {color}: the other cylinder did not move (under 5 mm)", moved < 5, f"{moved:.2f} mm")

    if quick:
        return c.report()

    # ---------------- M3: robustness ----------------
    rng = np.random.default_rng(0)
    for color in sim.objects:
        ok = 0
        fails = []
        hx, hy = cylinder_home_xy(cfg, color)
        for k in range(20):
            dx, dy = rng.uniform(-0.02, 0.02, 2)
            r = trial(sim, sk, color, hx + dx, hy + dy)
            ok += r.ok
            if not r.ok:
                fails.append((round(dx * 1000), round(dy * 1000), r.reason))
        c.check(f"pick {color} with seeded +-2 cm offsets: at least 90 % of 20", ok >= 18, f"{ok}/20 {fails}")

    az = math.radians(cfg.cylinder_azimuth_deg)
    for dist in (0.44, 0.48, 0.52, 0.56, 0.60, 0.64):
        row = []
        for color in sim.objects:
            side = cfg.cylinders[color][1]
            r = trial(sim, sk, color, side * dist * math.sin(az), -dist * math.cos(az))
            row.append((color, r.ok, r.reason))
        c.check(f"pick at {dist:.2f} m from the rotation centre, both colours",
                all(x[1] for x in row), ", ".join(f"{a}:{'ok' if b else w}" for a, b, w in row))
    return c.report()


if __name__ == "__main__":
    sys.exit(main())
