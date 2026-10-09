"""Builds the MuJoCo model: the Stretch 3 (from the stretch_mujoco submodule) plus floor, table and cylinders."""
import math

import mujoco

from .config import SceneConfig


def cylinder_home_xy(cfg: SceneConfig, color: str) -> tuple:
    """World x, y of a cylinder's default position (distance and azimuth from the rotation centre)."""
    _, side = cfg.cylinders[color]
    az = math.radians(cfg.cylinder_azimuth_deg)
    return side * cfg.cylinder_distance * math.sin(az), -cfg.cylinder_distance * math.cos(az)


def build_model(cfg: SceneConfig) -> mujoco.MjModel:
    """Load stretch.xml with MjSpec, add the world, compile and switch the lidar sensors off."""
    if not cfg.model_path.exists():
        raise FileNotFoundError(
            f"Robot model not found: {cfg.model_path}. Is the stretch_mujoco submodule checked out "
            "(git submodule update --init)?"
        )
    spec = mujoco.MjSpec.from_file(str(cfg.model_path))
    spec.option.timestep = cfg.timestep
    world = spec.worldbody

    floor = world.add_geom()
    floor.name = "floor"
    floor.type = mujoco.mjtGeom.mjGEOM_PLANE
    floor.size = [0, 0, 0.05]
    floor.rgba = list(cfg.floor_rgba)

    light = world.add_light()
    light.pos = [0, 0, 2.0]
    light.dir = [0, 0, -1]

    half = cfg.table_half_size
    table = world.add_body()
    table.name = "table"
    table.pos = [0.0, -(cfg.table_edge_y + half[1]), cfg.table_top_z - half[2]]
    tgeom = table.add_geom()
    tgeom.name = "table_geom"
    tgeom.type = mujoco.mjtGeom.mjGEOM_BOX
    tgeom.size = list(half)
    tgeom.rgba = list(cfg.table_rgba)
    tgeom.friction = list(cfg.table_friction)

    for color, (rgba, _side) in cfg.cylinders.items():
        x, y = cylinder_home_xy(cfg, color)
        body = world.add_body()
        body.name = f"cyl_{color}"
        # a hair above the table so it settles instead of starting in contact
        body.pos = [x, y, cfg.table_top_z + cfg.cylinder_height / 2 + 0.002]
        body.add_freejoint()
        geom = body.add_geom()
        geom.name = f"cyl_{color}_geom"
        geom.type = mujoco.mjtGeom.mjGEOM_CYLINDER
        geom.size = [cfg.cylinder_radius, cfg.cylinder_height / 2, 0]
        geom.mass = cfg.cylinder_mass
        geom.rgba = list(rgba)
        geom.condim = 6
        geom.friction = list(cfg.cylinder_friction)

    model = spec.compile()
    # the 360 lidar rangefinders make mj_step about 10 ms; nothing here uses sensors
    model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_SENSOR
    return model
