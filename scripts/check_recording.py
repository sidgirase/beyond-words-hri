"""Video recording: the recorder and `demo.py --record`.

    python scripts/check_recording.py            headless recording
    python scripts/check_recording.py --viewer   also records with the viewer window open (needs a display)
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import _common  # noqa: F401  (puts src on sys.path so hri_sim can be imported)
from _common import Checks

import imageio.v2 as imageio
import numpy as np

from hri_sim import SceneConfig, Skills, StretchSim, VideoRecorder
from hri_sim.config import OUTPUTS_DIR
from hri_sim.recorder import resolve_path

SCRIPTS = Path(__file__).resolve().parent


def read_frames(path):
    reader = imageio.get_reader(str(path))
    frames = [f for f in reader]
    reader.close()
    return frames


def main() -> int:
    c = Checks("check_recording")
    c.check("a bare name goes to the outputs folder next to hri_sim and gets .mp4",
            resolve_path("my_run") == OUTPUTS_DIR / "my_run.mp4" and OUTPUTS_DIR == Path(__file__).resolve().parents[1] / "outputs",
            str(resolve_path("my_run")))
    c.check("a path with folders is kept", resolve_path("a/b.mp4") == Path("a/b.mp4"))

    with tempfile.TemporaryDirectory() as tmp:
        # headless recording through the API
        path = Path(tmp) / "headless.mp4"
        sim = StretchSim(SceneConfig(), headless=True, realtime=False)
        skills = Skills(sim)
        rec = VideoRecorder(sim, path, fps=30, width=640, height=360)
        r = skills.gesture("blue", hold_s=0.5)
        rec.add_still(1.0)
        rec.close()
        frames = read_frames(path)
        expected = int(r.sim_time * 30) + 30
        c.check("headless: the file exists and is not empty", path.exists() and path.stat().st_size > 10_000,
                f"{path.stat().st_size} bytes")
        c.check("headless: frame count matches simulated time at 30 fps (plus the 1 s still), within 3 frames",
                abs(len(frames) - expected) <= 3, f"{len(frames)} frames, expected about {expected} for {r.sim_time:.1f} s")
        c.check("headless: frames have the requested size", frames[0].shape == (360, 640, 3), str(frames[0].shape))
        c.check("headless: the first and last frames differ (the robot moved)",
                float(np.abs(frames[0].astype(int) - frames[-1].astype(int)).mean()) > 1.0)
        c.check("headless: the video is not black", float(frames[len(frames) // 2].mean()) > 20)
        c.check("closing the recorder detaches it from the simulation", sim.recorder is None)
        c.check("close() twice is harmless", rec.close() == path)

        # a recorded run still behaves the same
        plain = StretchSim(SceneConfig(), headless=True, realtime=False)
        p = Skills(plain).pick("green")
        rec_sim = StretchSim(SceneConfig(), headless=True, realtime=False)
        rec2 = VideoRecorder(rec_sim, Path(tmp) / "pick.mp4", fps=30, width=640, height=360)
        q = Skills(rec_sim).pick("green")
        rec2.close()
        c.check("recording does not change the physics: same pick, same sim time and result",
                q.ok == p.ok and abs(q.sim_time - p.sim_time) < 1e-6, f"{q.sim_time:.3f} s vs {p.sim_time:.3f} s")

        # the demo script
        out = Path(tmp) / "from_demo.mp4"
        run = subprocess.run([sys.executable, str(SCRIPTS / "demo.py"), "pick:green", "--headless", "--fast", "--record", str(out),
                              "--video-size", "640x360", "--record-tail", "1"], capture_output=True, text=True)
        c.check("demo.py --record writes the video and reports it", run.returncode == 0 and out.exists() and "Saved" in run.stdout,
                (run.stdout + run.stderr).strip().splitlines()[-1] if (run.stdout + run.stderr).strip() else "")
        demo_frames = read_frames(out)
        still_diff = float(np.abs(demo_frames[-1].astype(int) - demo_frames[-30].astype(int)).mean())
        c.check("the pick video ends with a still of the frozen last frame (last 30 frames nearly identical)",
                still_diff < 0.5, f"mean pixel change {still_diff:.2f}")
        bad = subprocess.run([sys.executable, str(SCRIPTS / "demo.py"), "pick:green", "--headless", "--record", "x",
                              "--video-size", "huge"], capture_output=True, text=True)
        c.check("a bad --video-size is rejected with a message", bad.returncode != 0 and "1280x720" in bad.stderr,
                bad.stderr.strip().splitlines()[-1] if bad.stderr.strip() else "")

        if "--viewer" in sys.argv:
            v = StretchSim(SceneConfig(), headless=False, realtime=False)
            vrec = VideoRecorder(v, Path(tmp) / "viewer.mp4", fps=30, width=640, height=360)
            v.run_for(1.0)
            v.viewer.cam.azimuth += 90  # the user drags the camera in the window
            v.run_for(1.0)
            vrec.close()
            vf = read_frames(Path(tmp) / "viewer.mp4")
            c.check("viewer: recorded about 2 s at 30 fps", abs(len(vf) - 60) <= 3, f"{len(vf)} frames")
            diff = float(np.abs(vf[5].astype(int) - vf[-5].astype(int)).mean())
            c.check("viewer: moving the window camera changes the recording (the robot was idle)", diff > 3.0, f"mean pixel change {diff:.1f}")
            v.close_window()
    return c.report()


if __name__ == "__main__":
    sys.exit(main())
