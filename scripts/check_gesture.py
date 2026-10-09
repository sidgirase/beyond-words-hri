"""M4: the gesture, each colour, its order of motions, and what the next skill does afterwards.

    python scripts/check_gesture.py

Judging how it looks is a separate step: python scripts/demo_gesture_variants.py
"""
import math
import sys

import _common  # noqa: F401  (puts src on sys.path so hri_sim can be imported)
from _common import Checks

from hri_sim import SceneConfig, Skills, StretchSim


def names(sim):
    return [e["name"] for e in sim.events]


def arm_never_retracted(sim):
    """no logged move sent the arm back toward zero"""
    return all(e.get("targets", {}).get("arm", 1.0) > 0.01 for e in sim.events)


def main() -> int:
    c = Checks("check_gesture (M4)")
    sim = StretchSim(SceneConfig(), headless=True, realtime=False)
    sk = Skills(sim)
    mo = sim.motion
    yaws = {}

    for color in sim.objects:
        sim.reset()
        r = sk.gesture(color)
        i = r.info
        c.check(f"gesture {color}: ok", r.ok, r.reason)
        c.check(f"gesture {color}: arm axis within 3 deg of the cylinder", abs(i["pointing_error_deg"]) <= 3.0,
                f"{i['pointing_error_deg']:.2f} deg")
        c.check(f"gesture {color}: arm extended to the object (grasp extension within 1 cm)",
                abs(i["arm"] - i["arm_pick"]) <= 0.01, f"arm {i['arm']:.3f} m, grasp extension {i['arm_pick']:.3f} m")
        c.check(f"gesture {color}: gripper hangs over the cylinder (within 2 cm horizontally)", i["hover_offset"] <= 0.02,
                f"{i['hover_offset'] * 1000:.1f} mm")
        c.check(f"gesture {color}: lift went halfway down (applied fraction 0.5 within 0.03)",
                abs(i["fraction_applied"] - 0.5) <= 0.03 and abs(i["lift"] - i["lift_goal"]) <= 0.005,
                f"applied {i['fraction_applied']:.2f}, lift {i['lift']:.3f} m, goal {i['lift_goal']:.3f} m")
        c.check(f"gesture {color}: gripper above the cylinder top, not touching (1 to 4 cm)",
                0.01 <= i["height_above_cylinder"] <= 0.04, f"{i['height_above_cylinder'] * 100:.1f} cm")
        c.check(f"gesture {color}: gripper closed", sim.joint("gripper") < 0.005, f"{sim.joint('gripper'):.3f}")
        pitch = float(sim.data.qpos[sim._jq["joint_wrist_pitch"]])
        c.check(f"gesture {color}: wrist stayed pitched down", abs(pitch - mo.wrist_pitch) < 0.02, f"{pitch:.3f} rad")
        c.check(f"gesture {color}: no cylinder moved more than 5 mm", i["max_cylinder_displacement"] < 0.005,
                f"{i['max_cylinder_displacement'] * 1000:.2f} mm")
        c.check(f"gesture {color}: no robot-table or robot-cylinder contact at any step", not sim.contact_violations,
                str(sim.contact_violations))
        c.check(f"gesture {color}: simulation not frozen, episode not over", not sim.frozen and not sim.episode_over)

        ev = sim.events
        c.check(f"gesture {color}: order of motions is turn, extend arm, lower lift", names(sim) == ["turn", "extend_arm", "lower_lift"],
                str(names(sim)))
        if names(sim) == ["turn", "extend_arm", "lower_lift"]:
            c.check(f"gesture {color}: each motion starts after the previous one ended",
                    all(ev[k]["t0"] >= ev[k - 1]["t1"] - 1e-9 for k in range(1, 3)))
            c.check(f"gesture {color}: the gripper closes during the turn", "gripper" in ev[0]["joints"],
                    str(ev[0]["joints"]))
        yaws[color] = math.degrees(sim.yaw)

    d = abs(yaws["blue"] - yaws["green"])
    c.check("yaw of the two gestures differs by 45 to 55 degrees (layout angle is 50)", 45 <= d <= 55,
            f"{d:.1f} deg ({yaws})")

    # gesture, then the other object: lift to carry height and turn with the arm still out
    sim.reset()
    sk.gesture("blue", hold_s=0.2)
    sim.events.clear()
    g2 = sk.gesture("green", hold_s=0.2)
    n = names(sim)
    c.check("gesture at the other object: lifts to carry height, turns, lowers; no retract, no second close",
            g2.ok and n[:2] == ["lift_to_carry", "turn"] and n[-1] == "lower_lift" and arm_never_retracted(sim)
            and sim.events[1]["joints"] == {}, str(n))
    c.check("gesture at the other object: the arm stays extended", sim.joint("arm") > 0.4, f"{sim.joint('arm'):.3f} m")
    c.check("gesture at the other object: no contacts at any step", not sim.contact_violations, str(sim.contact_violations))

    # gesture again at the same object: no turn, no lifting; at most a few-millimetre arm correction
    # (the base creeps a few millimetres per turn, which shifts the IK solution slightly)
    sim.events.clear()
    g3 = sk.gesture("green", hold_s=0.2)
    c.check("a second gesture at the same object does not turn or lift (only a tiny arm correction at most)",
            g3.ok and set(names(sim)) <= {"extend_arm"}, str(names(sim)))

    # gesture then pick the same object: open the gripper and pick, no turn and no lifting first
    sim.reset()
    sk.gesture("blue", hold_s=0.2)
    sim.events.clear()
    p = sk.pick("blue")
    c.check("pick right after a gesture at the same object: open, descend, close, lift up only",
            p.ok and names(sim) == ["open_gripper", "descend", "close_gripper", "lift_up"], f"{p.reason} {names(sim)}")

    # gesture then pick the other object: lift to carry height, turn with the arm out, descend
    sim.reset()
    sk.gesture("blue", hold_s=0.2)
    sim.events.clear()
    p = sk.pick("green")
    n = names(sim)
    c.check("pick at the other object after a gesture: lift to carry height, turn (gripper opens during it), descend",
            p.ok and n[:2] == ["lift_to_carry", "turn"] and arm_never_retracted(sim)
            and "gripper" in sim.events[1]["joints"] and n[-3:] == ["descend", "close_gripper", "lift_up"], str(n))
    c.check("pick after a gesture: no unwanted contacts, including while the gripper opens over the cylinder",
            not sim.contact_violations, str(sim.contact_violations))

    # lift depths: 0.25, 0.5 and 1.0 (clamped just above the cylinder) are all collision free
    for fraction in (0.25, 0.5, 1.0):
        for color in sim.objects:
            sim.reset()
            r = sk.gesture(color, fraction=fraction, hold_s=0.5)
            applied = r.info.get("fraction_applied", 0)
            ok = r.ok and not sim.contact_violations
            if fraction == 1.0:  # cannot go all the way down with a closed gripper: stops 1 cm above the cylinder
                ok = ok and applied < 1.0 and 0.005 <= r.info["height_above_cylinder"] <= 0.015
            c.check(f"lift fraction {fraction} at {color}: ok and collision free", ok,
                    f"{r.reason} applied {applied:.2f}, {r.info.get('height_above_cylinder', 0) * 100:.1f} cm above, "
                    f"{sim.contact_violations}")
    return c.report()


if __name__ == "__main__":
    sys.exit(main())
