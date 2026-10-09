"""VideoRecorder: records the simulation to an mp4 file by rendering offscreen with the viewer's camera.

Frames are taken every 1/fps of *simulated* time, so the video plays at the true speed of the simulation no
matter how slow rendering makes the run (about 0.1 s per 1280x720 frame on the integrated GPU). If the viewer
window is open its live camera is used, so dragging the camera in the window changes the recording too;
without a window the default camera is used. This renders the scene again offscreen; it is not a screen
capture, so overlays and window decorations are not in the video.

Needs the optional packages imageio and imageio-ffmpeg (pip install imageio imageio-ffmpeg).
"""
from pathlib import Path

import mujoco

from .config import OUTPUTS_DIR
from .sim import CAMERA, StretchSim


def resolve_path(name: str) -> Path:
    """A bare name goes to the outputs folder (with .mp4 added); a path with folders is used as given."""
    p = Path(name)
    if p.suffix.lower() != ".mp4":
        p = p.with_suffix(".mp4")
    return p if p.parent != Path(".") else OUTPUTS_DIR / p.name


class VideoRecorder:
    def __init__(self, sim: StretchSim, path, fps: int = 30, width: int = 1280, height: int = 720):
        try:
            import imageio.v2 as imageio
        except ImportError as e:
            raise RuntimeError("Recording needs imageio and imageio-ffmpeg: pip install imageio imageio-ffmpeg") from e
        if width % 2 or height % 2:
            raise ValueError("video width and height must be even (H.264)")
        self.sim = sim
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self.frames = 0
        vis = sim.model.vis.global_  # the offscreen buffer must be at least as large as the video frame
        vis.offwidth = max(int(vis.offwidth), width)
        vis.offheight = max(int(vis.offheight), height)
        self._renderer = mujoco.Renderer(sim.model, height, width)
        if sim.viewer is not None:
            self._cam = sim.viewer.cam
        else:
            self._cam = mujoco.MjvCamera()
            self._cam.lookat[:] = CAMERA["lookat"]
            self._cam.distance = CAMERA["distance"]
            self._cam.azimuth = CAMERA["azimuth"]
            self._cam.elevation = CAMERA["elevation"]
        self._writer = imageio.get_writer(str(self.path), fps=fps, codec="libx264", quality=8, macro_block_size=1)
        self._next = sim.time
        sim.recorder = self

    def maybe_capture(self):
        """Called by the simulation after every physics step: write a frame when 1/fps of sim time has passed."""
        if self.sim.time >= self._next - 1e-9:
            self._writer.append_data(self._render())
            self.frames += 1
            self._next += 1.0 / self.fps

    def _render(self):
        viewer = self.sim.viewer
        if viewer is not None and viewer.is_running():
            with viewer.lock():
                self._renderer.update_scene(self.sim.data, camera=self._cam)
                return self._renderer.render()
        self._renderer.update_scene(self.sim.data, camera=self._cam)
        return self._renderer.render()

    def add_still(self, seconds: float):
        """Append the current frame for `seconds` (for example the frozen last frame after a pick)."""
        n = int(round(seconds * self.fps))
        if n > 0:
            frame = self._render()
            for _ in range(n):
                self._writer.append_data(frame)
            self.frames += n

    def close(self) -> Path:
        """Finish the file. Safe to call twice."""
        if self._writer is not None:
            self._writer.close()
            self._writer = None
            self._renderer.close()
            self.sim.recorder = None
        return self.path
