"""M5: combinations of gesture and pick, each from a fresh reset.

    python scripts/check_sequences.py
"""
import sys

import _common  # noqa: F401  (puts src on sys.path so hri_sim can be imported)
from _common import Checks

import numpy as np

from hri_sim import SceneConfig, Skills, StretchSim

SEQUENCES = [
    [("gesture", "blue"), ("pick", "green")],
    [("gesture", "green"), ("pick", "blue")],
    [("gesture", "blue"), ("pick", "blue")],
    [("gesture", "green"), ("pick", "green")],
    [("gesture", "blue"), ("gesture", "green"), ("pick", "green")],
    [("gesture", "green"), ("gesture", "blue"), ("pick", "blue")],
    [("gesture", "blue"), ("gesture", "blue"), ("pick", "blue")],
    [("pick", "blue")],
    [("pick", "green")],
]


def main() -> int:
    c = Checks("check_sequences (M5)")
    sim = StretchSim(SceneConfig(), headless=True, realtime=False)
    sk = Skills(sim)

    for seq in SEQUENCES:
        name = " -> ".join(f"{a}({t})" for a, t in seq)
        sim.reset()
        base0 = np.array(sim.base_pose()[:2])
        problems = []
        for skill, target in seq:
            before = {k: sim.object_position(k) for k in sim.objects}
            r = getattr(sk, skill)(target)
            if not r.ok:
                problems.append(f"{skill}({target}) failed: {r.reason}")
                break
            for other in sim.objects:
                # the non-target cylinder must stay put, and so must the target during a gesture
                if other != target or skill == "gesture":
                    moved = float(np.linalg.norm(sim.object_position(other) - before[other])) * 1000
                    if moved >= 5.0:
                        problems.append(f"{other} moved {moved:.1f} mm during {skill}({target})")
        creep = float(np.linalg.norm(np.array(sim.base_pose()[:2]) - base0)) * 1000
        if sim.contact_violations:
            problems.append(f"contacts at some step: {sim.contact_violations}")
        if creep >= 30:
            problems.append(f"base crept {creep:.1f} mm")
        if seq[-1][0] == "pick" and not (sim.episode_over and sim.frozen):
            problems.append("episode did not end after the pick")
        later = sk.gesture(seq[-1][1])
        if seq[-1][0] == "pick" and later.reason != "episode_over":
            problems.append(f"a skill after the pick returned {later.reason!r}")
        c.check(name, not problems,
                f"sim {sim.time:.0f} s, base creep {creep:.1f} mm" + ("; " + "; ".join(problems) if problems else ""))
    return c.report()


if __name__ == "__main__":
    sys.exit(main())
