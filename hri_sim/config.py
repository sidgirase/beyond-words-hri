"""Configuration dataclasses for the simulation, the motion executor and the skills.

All numbers are starting values measured in the prototype (see wiki/plans/ik-pick-and-gesture-poc.md);
they are meant to be tuned here, not in the code that uses them.
"""
from dataclasses import dataclass, field
from pathlib import Path

# src/hri_sim/config.py -> src/
SRC_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = SRC_DIR / "stretch_mujoco" / "stretch_mujoco" / "models" / "stretch.xml"
OUTPUTS_DIR = SRC_DIR / "outputs"  # videos from scripts/demo.py --record


@dataclass
class SceneConfig:
    """World layout. Frame: robot rotation centre at the origin, facing +x, arm toward -y."""

    model_path: Path = DEFAULT_MODEL_PATH
    timestep: float = 0.002

    # table (box). Its near edge is `table_edge_y` metres from the rotation centre, along -y.
    table_top_z: float = 0.48
    table_half_size: tuple = (0.6, 0.5, 0.24)
    table_edge_y: float = 0.36
    table_rgba: tuple = (0.72, 0.55, 0.35, 1.0)
    table_friction: tuple = (1.0, 0.01, 0.002)

    # cylinders (free bodies). Rolling friction (condim 6) keeps them from drifting.
    cylinder_radius: float = 0.035
    cylinder_height: float = 0.10
    cylinder_mass: float = 0.1
    cylinder_friction: tuple = (1.0, 0.01, 0.002)
    cylinder_distance: float = 0.54  # from the rotation centre
    cylinder_azimuth_deg: float = 25.0  # from the -y axis
    # name -> (rgba, side); side -1 puts the cylinder on the -x side, +1 on the +x side
    cylinders: dict = field(
        default_factory=lambda: {
            "blue": ((0.1, 0.2, 1.0, 1.0), -1),
            "green": ((0.1, 0.75, 0.2, 1.0), +1),
        }
    )

    floor_rgba: tuple = (0.55, 0.55, 0.58, 1.0)

    @property
    def cylinder_top_z(self) -> float:
        return self.table_top_z + self.cylinder_height


@dataclass
class MotionConfig:
    """Motion executor settings."""

    # carry pose: the start pose and the height from which the base turns
    carry_lift: float = 0.80
    wrist_pitch: float = -1.57  # gripper hangs down; never changes. Inside the joint range [-1.57, 0.56],
    # which matters: mink's problem is infeasible if a frozen joint starts outside its range
    gripper_open: float = 0.04
    gripper_closed: float = -0.02

    # per-joint speed limits for ctrl ramps (m/s)
    rates: dict = field(default_factory=lambda: {"lift": 0.15, "arm": 0.15, "gripper": 0.05})
    ctrl_tick_steps: int = 5  # physics steps per control tick

    # "settled" test: all moved joints slower than this for `settle_ticks` consecutive ticks
    settle_speed: float = 0.003
    settle_ticks: int = 10
    # trim: add the remaining position error to ctrl (for servos with steady-state lag)
    trim_tolerance: float = 0.002
    trim_max: int = 3
    move_timeout_s: float = 12.0

    # base yaw (wheel) controller: ctrl = clip(gain * error, +-max); wheel ctrl is 3x wheel speed (gear 3)
    yaw_gain: float = 12.0
    yaw_ctrl_max: float = 6.0
    yaw_ctrl_min: float = 0.7  # floor so the wheels do not stall on friction
    yaw_tolerance_deg: float = 0.4
    yaw_timeout_s: float = 15.0

    # real-time pacing and viewer sync
    viewer_sync_steps: int = 8  # sync the viewer every N physics steps (16 ms of sim time)
    realtime_resync_s: float = 0.1  # if wall time falls behind by this much, re-anchor the pacing clock


@dataclass
class SkillConfig:
    """Skill parameters."""

    # pick
    grasp_dz: float = 0.06  # grasp centre height above the table top
    pre_grasp_dz: float = 0.12  # pre-grasp height above the grasp height
    squeeze_ctrl: float = -0.005  # gripper ctrl while closing on the cylinder
    lift_after_grasp: float = 0.15
    min_rise: float = 0.10  # cylinder must rise at least this much for a successful pick
    max_lateral_from_gripper: float = 0.05
    settle_after_close_steps: int = 150
    settle_after_lift_steps: int = 250

    # gesture: the lift goes down this fraction of the way from carry height to the grasp height, with the
    # closed gripper hanging over the cylinder. Never lower than `gesture_min_clearance` above the cylinder top.
    gesture_fraction: float = 0.5
    gesture_min_clearance: float = 0.01  # grasp centre above the cylinder top (the closed fingertips reach about
    # 5 mm below the grasp centre, so touching starts at about -0.005)
    gesture_hold_s: float = 2.0

    # "already in place" tests: skip a turn, an arm move or a lift move that would change almost nothing
    no_turn_deg: float = 1.0
    arm_match_tol: float = 0.003
    lift_match_tol: float = 0.003

    # inverse kinematics
    ik_tolerance: float = 1e-3
    ik_max_iterations: int = 50
    ik_damping: float = 1e-3
    ik_fail_residual: float = 2e-3  # residual above this means the target was not reached
