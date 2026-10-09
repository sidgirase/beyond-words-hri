"""M6: the API behaviours around the skills: abort, failures, episode end and the window.

    python scripts/check_api.py            headless
    python scripts/check_api.py --viewer   also opens a window to test hold_final_frame and close_window
"""
import sys
import threading
import time

import _common  # noqa: F401  (puts src on sys.path so hri_sim can be imported)
from _common import Checks


from hri_sim import SceneConfig, Skills, StretchSim


def main() -> int:
    c = Checks("check_api (M6)")
    cfg = SceneConfig()
    sim = StretchSim(cfg, headless=True, realtime=False)
    sk = Skills(sim)

    # abort from another thread stops a motion mid-way and leaves the robot usable
    t = threading.Timer(0.15, sk.abort)
    t.start()
    r = sk.pick("blue")
    t.join()
    c.check("abort() stops a pick from another thread", (not r.ok) and r.reason == "aborted",
            f"{r.reason} after {r.sim_time:.1f} s of sim (a full pick takes about 15 s)")
    c.check("wheels are stopped after an abort", sim.ctrl("left_wheel_vel") == 0 and sim.ctrl("right_wheel_vel") == 0)
    c.check("an aborted pick does not end the episode", not sim.episode_over and not sim.frozen)
    r = sk.gesture("green", hold_s=0.2)
    c.check("a gesture right after the abort works (it returns to a safe pose first)", r.ok and not sim.contact_violations,
            f"{r.reason} {sim.contact_violations}")

    # failures return a result instead of raising
    r = sk.pick("purple")
    c.check("unknown colour returns unknown_target", (not r.ok) and r.reason == "unknown_target", r.reason)
    sim.reset()
    sim.set_object_position("blue", 0.0, -0.95)
    r = sk.pick("blue")
    c.check("a cylinder out of reach returns unreachable or ik_failed without moving",
            (not r.ok) and r.reason in ("unreachable", "ik_failed") and r.sim_time == 0.0,
            f"{r.reason}, sim {r.sim_time:.1f} s")
    c.check("an unreachable result still reports the IK solve", len(r.ik) >= 1 and not r.ik[0].converged)

    # results carry timing information
    sim.reset()
    r = sk.pick("green")
    c.check("a successful pick reports sim time, wall time and IK stats",
            r.ok and r.sim_time > 5 and r.wall_time > 0 and len(r.ik) == 3 and all(s.ms > 0 for s in r.ik),
            f"sim {r.sim_time:.1f} s, wall {r.wall_time:.2f} s, IK {[round(s.ms, 2) for s in r.ik]} ms")
    c.check("episode_over after the pick; reset() starts a new episode", sim.episode_over)
    sk.reset()
    c.check("after reset the robot can pick again", sk.pick("blue").ok)

    if "--viewer" in sys.argv:
        v = StretchSim(cfg, headless=False, realtime=False)
        vs = Skills(v)
        r = vs.pick("green")
        c.check("viewer: pick ok and simulation frozen", r.ok and v.frozen)
        before = v.time
        v.step(100)
        c.check("viewer: stepping after the pick does nothing", v.time == before)
        done = {}

        def hold():
            vs.hold_final_frame()
            done["t"] = time.perf_counter()

        th = threading.Thread(target=hold)
        th.start()
        time.sleep(1.0)
        c.check("viewer: hold_final_frame keeps blocking while the window is open", th.is_alive())
        t0 = time.perf_counter()
        vs.close_window()
        th.join(timeout=3)
        c.check("viewer: close_window from another thread ends hold_final_frame within 3 s", not th.is_alive(),
                f"{time.perf_counter() - t0:.2f} s")
        r = vs.gesture("blue")
        c.check("viewer: skills after the window is closed return episode_over or window_closed",
                (not r.ok) and r.reason in ("episode_over", "window_closed"), r.reason)

        w = StretchSim(cfg, headless=False, realtime=True)
        ws = Skills(w)
        timer = threading.Timer(1.0, ws.close_window)
        timer.start()
        r = ws.gesture("blue")
        timer.join()
        c.check("viewer: closing the window during a skill stops it with window_closed", (not r.ok) and r.reason == "window_closed",
                f"{r.reason}")
        c.check("viewer: the next skill returns window_closed", ws.pick("blue").reason == "window_closed")
    return c.report()


if __name__ == "__main__":
    sys.exit(main())
