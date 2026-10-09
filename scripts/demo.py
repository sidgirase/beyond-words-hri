"""Viewer demo: run a sequence of skills in real time, then keep the last frame open until you close the window.

    python scripts/demo.py gesture:blue pick:green
    python scripts/demo.py gesture:green gesture:blue pick:blue --fraction 0.7
    python scripts/demo.py pick:blue --fast --headless
    python scripts/demo.py gesture:blue pick:green --record               # video in outputs/demo_DATE_TIME.mp4
    python scripts/demo.py gesture:blue pick:green --record my_run        # video in outputs/my_run.mp4

A successful pick freezes the simulation; the window stays open (drag the camera as you like) until you close it.

--record renders the scene offscreen with the window's own camera every 1/fps of simulated time and writes an mp4
(needs imageio and imageio-ffmpeg). Rendering is slow (about 0.1 s per frame), so the run takes longer than real
time while recording, but the video plays at the true simulation speed. If the window is open, moving its camera
changes the recording too. The folder is outputs/ next to hri_sim/ (src/outputs).
"""
import argparse
import datetime
import sys
import threading

import _common  # noqa: F401  (puts src on sys.path so hri_sim can be imported)

from hri_sim import SceneConfig, Skills, StretchSim, VideoRecorder
from hri_sim.recorder import resolve_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("steps", nargs="+", help="skill:color, e.g. gesture:blue pick:green")
    ap.add_argument("--fraction", type=float, default=None,
                    help="gesture: how far the lift goes down from carry height to the grasp height (default 0.5)")
    ap.add_argument("--hold", type=float, default=None, help="gesture: seconds to hold the pose (default 2)")
    ap.add_argument("--fast", action="store_true", help="do not pace to real time")
    ap.add_argument("--headless", action="store_true", help="no window")
    ap.add_argument("--close-after", type=float, default=None,
                    help="close the window this many seconds after the sequence (default: wait for you)")
    ap.add_argument("--record", nargs="?", const="", default=None, metavar="NAME",
                    help="record a video to outputs/NAME.mp4 (no NAME: outputs/demo_DATE_TIME.mp4)")
    ap.add_argument("--video-fps", type=int, default=30)
    ap.add_argument("--video-size", default="1280x720", metavar="WxH", help="video frame size (default 1280x720)")
    ap.add_argument("--record-tail", type=float, default=2.0,
                    help="seconds of the final frame added at the end of the video (default 2)")
    args = ap.parse_args()

    steps = []
    for s in args.steps:
        skill, _, color = s.partition(":")
        if skill not in ("gesture", "pick") or not color:
            ap.error(f"bad step {s!r}; use gesture:COLOR or pick:COLOR")
        steps.append((skill, color))

    sim = StretchSim(SceneConfig(), headless=args.headless, realtime=not args.fast)
    skills = Skills(sim)
    recorder = None
    if args.record is not None:
        name = args.record or f"demo_{datetime.datetime.now():%Y%m%d_%H%M%S}"
        try:
            width, height = (int(v) for v in args.video_size.lower().split("x"))
        except ValueError:
            ap.error("--video-size must look like 1280x720")
        recorder = VideoRecorder(sim, resolve_path(name), fps=args.video_fps, width=width, height=height)
        print(f"Recording to {recorder.path} (rendering makes the run slower than real time)", flush=True)
    try:
        ok = run(skills, steps, args)
        if recorder is not None:
            recorder.add_still(args.record_tail)
    finally:
        if recorder is not None:  # always finish the file, even after an error
            path = recorder.close()
            print(f"Saved {path} ({recorder.frames} frames, {recorder.frames / recorder.fps:.1f} s)", flush=True)
    if not args.headless and sim.window_open:
        if sim.episode_over:
            print("Pick done: the simulation is stopped on the last frame.", flush=True)
        if args.close_after is not None:
            threading.Timer(args.close_after, skills.close_window).start()
        else:
            print("Close the window to exit.", flush=True)
        skills.hold_final_frame()
    return 0 if ok else 1


def run(skills: Skills, steps, args) -> bool:
    """Run the skills in order; stops early if the window is closed or the run is aborted."""
    ok = True
    for skill, color in steps:
        if skill == "gesture":
            result = skills.gesture(color, fraction=args.fraction, hold_s=args.hold)
        else:
            result = skills.pick(color)
        print(result, flush=True)
        if not result.ok:
            ok = False
            if result.reason in ("window_closed", "aborted"):
                break
    return ok


if __name__ == "__main__":
    sys.exit(main())
