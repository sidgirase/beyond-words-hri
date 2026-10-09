"""Viewer session for judging the gesture: the same gesture with different lift depths, in real time.

    python scripts/demo_gesture_variants.py
    python scripts/demo_gesture_variants.py --colors blue --fractions 0.5 1.0 --hold 8

For each variant the scene is reset (the robot starts from the carry pose), the robot makes the gesture, and the
final pose is held for --hold seconds while you look at it (drag the camera to see it from the side or the
front). The label is printed in the terminal. The fraction is how far the lift goes down from carry height to the
grasp height: 0.5 is halfway, 1.0 means as low as is possible without touching the cylinder (the lift stops 1 cm
above its top). Tell me which one reads best; the default in SkillConfig is then changed to it.
"""
import argparse
import sys

import _common  # noqa: F401  (puts src on sys.path so hri_sim can be imported)

from hri_sim import SceneConfig, Skills, StretchSim


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fractions", type=float, nargs="+", default=[0.25, 0.5, 1.0])
    ap.add_argument("--colors", nargs="+", default=["blue", "green"])
    ap.add_argument("--hold", type=float, default=5.0, help="seconds to hold each final pose")
    ap.add_argument("--fast", action="store_true", help="do not pace to real time")
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()

    sim = StretchSim(SceneConfig(), headless=args.headless, realtime=not args.fast)
    skills = Skills(sim)
    variants = [(c, f) for f in args.fractions for c in args.colors]
    for n, (color, fraction) in enumerate(variants, 1):
        print(f"Variant {n}/{len(variants)}: {color}, lift fraction {fraction}", flush=True)
        result = skills.gesture(color, fraction=fraction, hold_s=args.hold)
        i = result.info
        print(f"   {result}  gripper {i.get('height_above_cylinder', 0) * 100:.1f} cm above the cylinder top, "
              f"applied fraction {i.get('fraction_applied', 0):.2f}", flush=True)
        if not result.ok:
            print("   stopping:", result.reason)
            break
        if n < len(variants):
            sim.reset()
            sim.run_for(1.0)  # a moment in the carry pose between variants
    if sim.window_open:
        print("All variants shown. Close the window to exit.", flush=True)
        skills.hold_final_frame()
    return 0


if __name__ == "__main__":
    sys.exit(main())
