---
title: How MuJoCo and stretch_mujoco work (and why "is the object in the bin?" is hard)
type: concept
sources: [stretch-3-robot, dev-environment, stretch_mujoco source @ d107e09]
updated: 2026-09-30
---

# How MuJoCo and stretch_mujoco work

This page builds up from plain MuJoCo to the specific problem: **our code can't currently see where
the objects are, so it can't tell when one lands in the bin.** Facts about stretch_mujoco come from
reading its source and the tests in [[stretch-3-robot]] and [[dev-environment]].

## 1. MuJoCo in five ideas

### 1.1 Model vs. data
MuJoCo splits a simulation into two objects:

| Object        | What it holds                                                                                                                                                                    | Changes during simulation? |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| **`MjModel`** | The *description* of the world: bodies, their shapes, masses, joints, actuators, sensors, cameras, the timestep. Compiled from an XML file (MJCF).                               | No (constant).             |
| **`MjData`**  | The *state* of the world right now: time, every joint position and velocity, the actuator commands, the world pose of every body, the list of current contacts, sensor readings. | Yes, every step.           |

Everything you'd want to ask ("where is the apple?", "is the gripper touching it?") is answered by
reading `MjData`.

### 1.2 The world is a tree of bodies
```
worldbody
├── floor            (geom only, never moves)
├── table            (body with a box geom, no joint → fixed in place)
├── bin              (body with 5 box geoms: floor + 4 walls, no joint → fixed)
├── apple_1          (body with a free joint → can fly/fall/roll anywhere)
│   └── sphere geom
└── base_link        (the robot: free joint on the base, then a chain of links)
    ├── link_lift        (slide joint "joint_lift")
    │   └── link_arm_l3 … link_arm_l0   (4 telescoping slide joints)
    │       └── wrist yaw → pitch → roll → gripper fingers
    └── link_head_pan → link_head_tilt (cameras)
```
- A **body** is a rigid frame. A **geom** is a shape attached to a body, used for collision and drawing.
- A **joint** gives a body freedom relative to its parent. With no joint, the body is welded to its parent.
  A **free joint** means six degrees of freedom; that's what makes an object "loose" on the table.

### 1.3 Where an object's pose lives
For a body with a free joint, its position and orientation are stored in `MjData`:
- `data.qpos[adr : adr+7]` is x, y, z plus a quaternion (w, x, y, z), where `adr = model.jnt_qposadr[joint_id]`.
- `data.xpos[body_id]` is the body's world position (3 numbers), recomputed every step.
- `data.qvel[...]` is its linear and angular velocity (6 numbers).

So "where is apple_1?" is simply `data.xpos[id_of("apple_1")]`, **if you have the `MjData`**.

### 1.4 How things move: actuators, control and stepping
- An **actuator** drives a joint. Stretch's lift, arm and wrist are *position servos*: you write a target
  into `data.ctrl[actuator_id]` and a built-in spring pulls the joint toward it. The wheels are *velocity* actuators.
- **`mujoco.mj_step(model, data)`** advances physics by one timestep (2 ms for Stretch). It applies
  `ctrl`, detects contacts, solves forces, and updates `qpos`, `qvel`, `xpos` and the contacts.
- A simulation is just a loop: *set ctrl → mj_step → read data → repeat*. Running it at real time means
  500 steps per wall-clock second.

### 1.5 Contacts
After each step, `data.contact[0 … data.ncon-1]` lists every touching pair of geoms (`geom1`, `geom2`,
position, penetration). "Is the gripper touching the apple?" means "is there a contact whose two geoms
belong to a finger body and the apple body?". We used exactly this in the grasp tests.

## 2. What "the object is in the bin" means in MuJoCo terms
Once you can read `MjData`, success is a cheap check done every step (or every ~50 ms):

1. **Inside the bin's box:** the object's `xpos` is within the bin's inner x/y walls, and its z is between
   the bin floor and the top of the walls.
2. **Released:** there's no contact between the object and either gripper finger.
3. **Settled:** the object's speed (`qvel`) is near zero for a short time (e.g. 0.3 s), so a bounce
   that briefly passes through the box doesn't count.

An alternative to rule 1 is contact-based: "the object touches the bin's floor geom". Both are standard;
the box check also works for objects stacked on other objects in the bin.

The same data answers the other things the project needs: *which* object was picked (the one in contact
with both fingers when the lift rose), whether an object fell on the floor (z near 0), and resetting or
randomizing the scene (write new `qpos` values for the objects).

## 3. How stretch_mujoco wraps MuJoCo: two processes
stretch_mujoco doesn't run MuJoCo inside your program. It **spawns a second process** that owns the
`MjModel` and `MjData`, and talks to it through `multiprocessing.Manager` proxies (shared objects copied
across processes):

```
 ┌──────────── Process 1: OUR program ────────────┐        ┌────── Process 2: "MujocoProcess" ──────┐
 │                                                │        │                                        │
 │  teleop / policy code                          │        │  MjModel + MjData   (the real world)   │
 │     │                                          │        │  physics thread: ctrl → mj_step → …    │
 │     ▼                                          │        │  viewer window (passive viewer)        │
 │  StretchMujocoSimulator  (client object)       │        │  camera renderer, sensor thread        │
 │     move_to / move_by / set_base_velocity  ────┼──cmd──▶│  push_command() → writes data.ctrl     │
 │     pull_status()   ◀──────────────────────────┼─joints─┤  pull_status(): robot joints + time    │
 │     pull_camera_data()  ◀──────────────────────┼─images─┤  camera manager (slow, see env page)   │
 │     pull_sensor_data()  ◀──────────────────────┼─lidar──┤  sensor manager                        │
 │                                                │        │                                        │
 │     ✘ object poses       — never sent          │        │  data.xpos[apple]  exists here only    │
 │     ✘ contacts           — never sent          │        │  data.contact      exists here only    │
 └────────────────────────────────────────────────┘        └────────────────────────────────────────┘
```

- **Commands go in:** `move_to("lift", 0.8)` is packaged into a `StatusCommand`, put on a proxy, and the
  server's `push_command` turns it into `data.ctrl` values each physics step.
- **Status comes out:** every step the server's `pull_status()` builds a `StatusStretchJoints` (lift, arm,
  wrist, gripper, head, base velocities, sim time) and publishes it.
- **What doesn't come out:** anything about the rest of the world. The server has `data.xpos` for the apple
  and the full contact list, **but nothing copies them across the process boundary.** The client-side
  helpers `get_base_pose`, `get_ee_pose` and `get_link_pose` only cover the *robot*; they're computed from
  the joint status using a separate URDF kinematics model, not from `MjData`.

**That's the problem:** the code that knows the task (teleop now, policy later) lives in process 1, and
the information needed to judge the task lives only in process 2. Our program literally can't ask "where is
apple_1?" or "is it in the bin?".

The grasp tests on [[ambiguous-scene-design]] didn't hit this because they ran MuJoCo **directly in one
process** (their own `mj_step` loop), which gave full access to `MjData`.

## 4. Ways to fix it
| Option                                 | How                                                                                                                                                                                                                                                                                                                                                  | Pros                                                                                                                                                                                                                                                   | Cons                                                                                                                                                                                                                                                                |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A. Extend stretch_mujoco's server**  | Subclass the server (e.g. `MujocoServerPassive`) so that every step it also publishes the poses of our tracked objects (and, e.g., finger contacts) into an extra `Manager` dict. Subclass `StretchMujocoSimulator.start` so it launches our server class.                                                                                           | Keeps their viewer, base controller, keyframes, camera pipeline and ROS2 compatibility. Small amount of code.                                                                                                                                          | Depends on private internals of a pinned version. Still two processes: stepping isn't deterministic or controllable from our side (it free-runs at wall-clock time), which is awkward for policy training and exact resets. Every observation is an IPC round trip. |
| **B. Run MuJoCo in-process ourselves** | Load stretch_mujoco's `scene.xml` / `stretch.xml` (just the model files), add our table, objects and bin with `MjSpec`, and run our own loop: `mujoco.viewer.launch_passive` for the window, `mj_step` for physics. Write a small Stretch controller: joint targets into `data.ctrl`, differential-drive wheels for the base, gripper range mapping. | Full `MjData` access: object poses, contacts, reset/seed, exact stepping. Naturally becomes a gym-style `reset()` / `step(action)` environment, which is what a future policy needs. One process, simpler to debug. Already proven by our grasp tests. | We reimplement the pieces stretch_mujoco gives for free (base motion, keyframes, command smoothing, camera helpers). We lose drop-in ROS2 / Web Teleop compatibility (not needed for the study as proposed).                                                        |
| **C. Judge from camera images**        | Detect the object in the bin from rendered frames.                                                                                                                                                                                                                                                                                                   | Closest to what a real robot would do.                                                                                                                                                                                                                 | Rendering starves physics on this machine ([[dev-environment]]); perception errors would contaminate success labels. Not suitable as the ground truth.                                                                                                              |
|                                        |                                                                                                                                                                                                                                                                                                                                                      |                                                                                                                                                                                                                                                        |                                                                                                                                                                                                                                                                     |

Options A and B both give ground-truth success checks. **Decision 2026-10-09: option B is implemented**
([[codebase/architecture]]). The reason: the stated goal is "teleop now, swap in a policy later", and a policy wants a
synchronous `step(action)` with ground-truth reward and resets, which option A can't provide cleanly.

## 5. Glossary
- **MJCF**: MuJoCo's XML model format. **MjSpec**: Python API to load, edit and compile MJCF in code.
- **qpos / qvel**: all joint positions / velocities, concatenated. **ctrl**: actuator commands.
- **xpos / xquat**: world position / orientation of each body (derived, updated each step).
- **condim**: contact dimensionality. 3 means sliding friction only; 6 adds torsional and *rolling*
  friction, which is what stops balls rolling away.
- **Real-time factor (RTF)**: simulated seconds per wall-clock second.
- **Passive viewer**: a MuJoCo window that just displays the `MjData` your own loop is stepping.
