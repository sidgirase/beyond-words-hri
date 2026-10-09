---
title: Ambiguous tabletop scene design
type: concept
sources: [dogan-2022-follow-up-clarifications, proposal-beyond-words, stretch-3-robot, dev-environment]
updated: 2026-09-30
---

# Ambiguous tabletop scene design

## Goal
A table where natural requests often match **more than one** object, so the robot has a reason to
clarify — without so much clutter that failures come from perception or grasping instead
([[proposal-beyond-words]], "Creating Ambiguity").

## Reference scene
[[dogan-2022-follow-up-clarifications]] Fig. 1 / Fig. 3: ~25–30 objects on a white table, with several of
each kind and repeated spatial patterns:

| Category   | Objects                                              | Ambiguity lever                              |
| ---------- | ---------------------------------------------------- | -------------------------------------------- |
| Fruit      | bananas ×3–4, red apples ×3+, oranges ×2+, lemons    | same name, same colour                       |
| Vegetables | green peppers, red peppers, artichokes, leafy greens | colour shared across kinds ("the green one") |
| Utensils   | knives, forks, spoons (several each)                 | thin, look alike, same name                  |
| Containers | bottles, cups, dark bowls                            | same name, similar size                      |

The proposal adds "multiple cups and blocks" (Whitney et al. 2017 style).

## Ambiguity levers to reproduce
- **Same type, several instances** (3 bananas) → only spatial language disambiguates.
- **Same colour, different type** (green pepper / artichoke / greens) → colour-only requests ambiguous.
- **Repeated spatial configurations** (banana next to a knife in two places) → even spatial references
  stay ambiguous.
- Mix of objects a detector would know and ones it wouldn't (Dogan's detectable/undetectable split).

## Simulation considerations
- Deterministic, seedable layouts so every participant/condition sees comparable scenes (internal
  validity, [[study-design]]); randomized layouts for policy training/testing.
- A **bin/basket** for placing — mirrors Dogan et al.'s basket.
- Object assets: primitive shapes (spheres/capsules/boxes with colour) are the cheapest start; mesh assets
  (e.g. YCB / Objaverse) look more realistic. Choice to be made in the plan.

## Graspability (verified in sim 2026-09-30)
Test: raw MuJoCo 3.2.6 with the stretch_mujoco model and a naive top-down grasp (wrist pitch −1.57, lower
the lift until the fingertips touch the table or the grasp centre reaches the object, close, lift). The
object was teleported under the gripper on the default table (top z = 0.48). Mass 0.1 kg,
`condim=6`, friction `[1.0, 0.01, 0.002]`.

| Proxy shape                            | Result                               |
| -------------------------------------- | ------------------------------------ |
| apple: sphere r = 3.5 cm               | **lifted ~21 cm** ✔                  |
| cup: cylinder r = 3.5 cm, h = 9 cm     | **lifted ~21 cm** ✔                  |
| bottle: cylinder r = 3.5 cm, h = 20 cm | **lifted ~15 cm** ✔                  |
| banana lying down: capsule r = 1.8 cm  | failed (also with wrist roll 1.57) ✘ |
| block: 4 cm cube                       | failed (also with wrist roll 1.57) ✘ |
| knife lying flat: 18 × 2 × 1 cm box    | failed, knocked off the table ✘      |


- **Why the small ones fail:** the rubber fingertips hit the table while `link_grasp_center` is still
  about 3 cm above the tabletop (minimum reached z ≈ 0.506–0.510), so low objects sit below the closing
  region. Fixing this needs grasp tuning (a different approach pose, wrist pitch slightly off vertical,
  or knowing the fingertip offset). That's an open item, not a blocker.
- Until it's fixed, **pick targets should be at least ~7 cm tall or wide** (apples, oranges, peppers,
  cups, bottles, artichokes). Low, flat objects (utensils, lying bananas, small blocks) should be
  **distractors only**. This keeps the Dogan-style ambiguity while avoiding "unrelated grasping
  failures" ([[proposal-beyond-words]]).

## Rolling objects
**Round objects roll off the table.** A plain sphere (default `condim=3`, no rolling friction) rolled off
the table by itself within about 1 s. The user noticed the same thing in the viewer. Fix: give round objects
`condim=6` with rolling friction (e.g. `friction="1.0 0.01 0.002"`); with that, the sphere stayed put and
was grasped. Apply it to every sphere or capsule, or use slightly flattened shapes (ellipsoid, a
cylinder with a flat base).
