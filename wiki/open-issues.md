---
title: Open issues (what is still missing)
type: overview
sources: [overview, dev-environment, stretch-3-robot, mujoco-primer, ambiguous-scene-design, proposal-beyond-words]
updated: 2026-09-30
---

# Open issues

A living list of what must be resolved before or during the first plan (sim scene + teleop pick-and-place
+ swappable policy + "pick this object"). Remove an item when it's resolved, and note the resolution in [[log]].
IDs are stable, so plans can refer to them (e.g. "resolves OI-1").

## Decisions needed from the team
| ID | Question | Options / current leaning | Why it matters |
|---|---|---|---|
| OI-1 | **Simulation architecture:** how does our code get object poses and contacts? | A: extend stretch_mujoco's server; **B: run MuJoCo in-process with our own controller (leaning)**. See [[mujoco-primer]] §4. | Success detection ("in the bin"), resets, seeding, and a policy-friendly `step(action)` all depend on it. Blocks the plan. |
| OI-2 | **Teleop input device** | Keyboard (pynput, like stretch_mujoco's example), gamepad, or on-screen GUI buttons. | Defines the teleop module and later the participant-facing interface. |
| OI-3 | **Object assets** | Coloured primitive shapes (fast, reliable) vs. meshes (YCB/Objaverse, realistic but slower and harder to grasp). | Affects realism of the ambiguity and physics speed. |
| OI-4 | **Scene layout:** where are the table, bin and robot relative to each other? | E.g. bin on the table's side, or on the floor next to the robot. The arm extends toward −y; reaching the bin may need base rotation. | Determines whether pick-to-bin needs base motion (more teleop steps, more to learn). |
| OI-5 | **How is "the object to pick" specified later?** | Object id/name from a list, click in the viewer, typed description, or a spoken or chat request resolved by a separate module. | Defines the policy's goal input (goal-conditioned policy). |
| OI-6 | **Proposal inconsistencies:** "VLA deployment", "gamified GUI", "scoring metric", "deception methodologies" | Confirm in or out of scope. See [[proposal-beyond-words]]. | Check-In 1 (2026-10-08) expectations. |
| OI-7 | Which physical robot (Stretch 2 or 3) will be available, and when? | Stretch 2 has a yaw-only wrist; Stretch 3 has a dexterous wrist. | Gestures and grasps designed in sim must transfer. |

## Technical unknowns to resolve
| ID | Issue | What we know | Next step |
|---|---|---|---|
| OI-8 | **Conda environment not built or verified** | `environment.yml` is written; all tests ran in a uv venv with the same versions ([[dev-environment]]). | The human runs `conda env create -f environment.yml` and the check command. |
| OI-9 | **Low or flat objects can't be grasped** | Objects under ~5 cm (lying banana, 4 cm block, flat knife) fail: fingertips hit the table with the grasp centre still ~3 cm up ([[ambiguous-scene-design]]). | Tune approach (pitch slightly off vertical, lower offset) or keep such objects as distractors only. |
| OI-10 | **Placing into the bin is untested** | Only grasp and lift were tested; release and drop into a bin, with the base moving while holding, weren't. | Include in the plan's first milestone test. |
| OI-11 | **Base motion untested in an in-process setup** | stretch_mujoco's base controller (translate/rotate by distance) lives in its server. Option B needs our own diff-drive controller for the wheel velocity actuators. | Prototype early if OI-1 is B. |
| OI-12 | **Managed viewer doesn't move joints** | Sim time advanced at 1.0× but commanded joints stayed put. | Only matters for option A; use the passive viewer. |
| OI-13 | **Below real time** | Passive viewer 0.61×, headless 0.73× (Windows sleep overshoot plus IPC). In-process (option B) should do better. | Measure again in the chosen architecture; acceptable for teleop if above ~0.5×. |
| OI-14 | **Camera images are too slow for an image-based policy** | ~40–135 ms per frame on the Intel iGPU, and it blocks physics in stretch_mujoco. | Decide the policy's observation: ground-truth state first, images later (low resolution, no shadows or reflections, render every N steps). |
| OI-15 | **Policy interface not defined** | Needs an observation (joint states, object poses, target id), an action (joint targets / deltas, base velocity, gripper) and a success signal. | Define in the plan so teleop and policy are two implementations of the same interface. |
| OI-16 | **Keyboard capture on Windows** | pynput hooks the keyboard globally (keys pressed in other windows also count) **(unverified on this machine)**. | Test, or use the viewer window's own key callback instead. |
| OI-17 | **Study logging format** | [[study-design]] lists what to log; no format chosen. | Not needed for the first plan, but the episode loop should expose these events. |
| OI-18 | **Hardware for a future learned policy** | No CUDA. A `torch_xpu` conda env exists (PyTorch on the Intel GPU), untested for this. | Revisit when choosing a policy (scripted vs. learned vs. VLA). |

## Sources not yet ingested
Cited in the proposal but not in the wiki: Dragan et al. 2013 (legibility), Whitney et al. 2017,
Ren et al. 2023 (KnowNo), Lin et al. 2025 (Ask-to-Clarify), Horter et al. 2026. Only needed for the
report and the clarification design, not for the simulation plan.
