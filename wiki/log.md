# Wiki log

Append-only. Entries: `## [YYYY-MM-DD] {op} | {title}`, op is one of init, ingest, query, lint, plan, implement.

## [2026-09-29] init | Wiki created
- Schema in `AGENTS.md` (+ `CLAUDE.md` importing it); layout: sources/, concepts/, codebase/, plans/.
- Created overview, index, changelog, codebase/README (no code yet), plans/README.

## [2026-09-29] ingest | Proposal — Beyond Words
- `sources/proposal-beyond-words.md`; new concepts: clarification-strategies, study-design, timeline.
- Flagged proposal inconsistency (VLA / gamified GUI / scoring metric only in timeline & rubric).

## [2026-09-29] ingest | Dogan, Torre & Leite 2022
- `sources/dogan-2022-follow-up-clarifications.md`, incl. object inventory from Fig. 1 & 3.
- New concept: ambiguous-scene-design.

## [2026-09-29] ingest | Idea analysis + course overview
- `sources/idea-analysis.md`, `sources/course-project-overview.md`; new concept: stretch-3-robot
  (Windows-support questions marked unverified).
- `../proposal/howell.pdf` not ingested (only relevant to the rejected Idea 4).

## [2026-09-30] query | Verify environment requirements
- Cloned stretch_mujoco (d107e09, v0.5.0) into scratch and ran it with uv on Windows. Rewrote
  [[stretch-3-robot]] with verified API facts; new page [[dev-environment]].
- Findings: MuJoCo must be 3.2.6 (the model fails on 3.4.0); Python 3.11, not 3.10 (sleep granularity);
  360 lidar rangefinders make stepping about 10 ms (fix: disable sensors); camera rendering starves physics;
  the passive viewer works (RTF 0.61); the managed viewer didn't move joints; the client can't read object poses.
- Grasp tests added to [[ambiguous-scene-design]]: sphere, cup and bottle proxies lifted; low or flat
  objects failed. Round objects roll off without `condim=6` (also reported by the user).

## [2026-09-30] lint | No angle brackets rule
- Added the rule to `AGENTS.md` and `llm-wiki.md`: never use the less-than or greater-than characters in
  wiki markdown (they break Obsidian rendering). Removed them from all pages, replaced callouts with
  bold paragraphs, and replaced placeholders with `{name}`.

## [2026-09-30] query | Conda, MuJoCo primer, open issues
- Switched the project to conda: added `src/environment.yml` (env `hri_stretch`: Python 3.11, pip `mujoco==3.2.6`,
  stretch_mujoco pinned to d107e09). The env isn't built yet (the human creates it). Rule added to `AGENTS.md`:
  the agent never creates or modifies conda envs itself.
- New [[mujoco-primer]]: model vs. data, the body tree, where object poses live, contacts, the "in the bin"
  check, stretch_mujoco's two-process design and why object poses never reach our code; options A/B/C.
  Verified that `get_link_pose` / `get_ee_pose` use URDF kinematics from the joint status, not `MjData`.
- New [[open-issues]] with OI-1 to OI-18.

## [2026-10-09] plan | IK-driven pick-up and gesture PoC
- New draft plan [[plans/ik-pick-and-gesture-poc]]: in-process MuJoCo (option B of [[mujoco-primer]]), table with blue and green cylinders, damped-least-squares IK, pick-up and a base-rotate plus half-arm-extend gesture, exposed as blocking skill functions for scripts and a later GUI.
- Milestones M0 to M6 with pass criteria (per-colour pick, perturbation sweep, gesture accuracy, 7 sequence combinations). 12 assumptions and 9 open questions listed in the plan.
- Model details that could not be checked (no local stretch_mujoco checkout, conda env not built) are marked unverified. No code changed; waiting for approval.

## [2026-10-09] plan | Refined PoC plan from the stretch_mujoco submodule, prototype and IK survey
- Read the submodule (`src/stretch_mujoco`, commit c78d6a1, README-only change after the pinned d107e09): wheel gear 3, arm as one DOF via equality constraints, ctrl-only keyframes, URDF-based `get_ee_pose`. Added a verified-details section and a **Contradiction** (grasp-centre x offset) to [[stretch-3-robot]].
- Throwaway prototype in a scratch uv venv (not project code): MjSpec scene, wheel yaw control, IK, pick, gesture and 9 sequences all worked in MuJoCo 3.2.6; viewer opens in-process on Windows. Findings rewrote [[plans/ik-pick-and-gesture-poc]]: carry pose, velocity-based settling, live object targets, hanging-gripper gesture, 0.52 m layout.
- Background agent surveyed IK libraries; only mink 0.0.13 fits (MuJoCo 3.2.6, Windows, no GPU). It advised keeping the hand-written solver; on the user's instruction the plan now uses mink 0.0.13 (pin required; newer mink needs a newer MuJoCo). I re-checked the mink pins, daqp license and Stretch example on PyPI and GitHub.
- No project code changed; status stays draft.

## [2026-10-09] plan | PoC plan updated with the user's answers
- [[plans/ik-pick-and-gesture-poc]]: gesture now ends with a straight gripper (swing from hanging to pitch 0 at carry height); fraction stays a share of the grasp extension, default 0.3 because a straight gripper is already 0.415 m out (0.5 would put the tip 8.6 cm past the cylinder); a successful pick freezes the sim, the last frame stays, `close_window()` and `hold_final_frame()` end the demo; release removed.
- Fixed layout, real-time pacing default, table edge moved from 0.32 m to 0.36 m and cylinders to 0.54 m so the base and the start pose clear the table; web GUI planned later, so `status()` and `run_async()` are in the API.
- No old IK solver and no `check_ik.py`; mink 0.0.13 is trusted. Re-ran the scratch prototype on the new layout: 9 sequences passed, gesture then pick 10/10 per colour with 2 cm offsets, picks OK at 0.44 to 0.64 m, no contacts. No project code changed.

## [2026-10-09] plan | PoC plan: viewer session for the gesture, GUI deferred
- [[plans/ik-pick-and-gesture-poc]]: user accepted the mink 0.0.13 pin and a frozen, draggable final frame; web GUI work is out of this plan, so `status()`, `run_async()` and the busy guard were removed.
- Gesture fraction and gripper state are now provisional (0.3, closed) until the user judges them: added `gripper` argument and `scripts/demo_gesture_variants.py` (fractions 0.15, 0.3, 0.5 by closed and open gripper, real time, draggable camera) and made that session part of M4.

## [2026-10-09] plan | PoC plan: new gesture order, no return to carry between skills
- [[plans/ik-pick-and-gesture-poc]]: gesture is now turn, then wrist swing to straight and gripper close together, then lower the lift, then extend the arm. Between skills the arm retracts completely and the base turns with the gripper still straight and closed; a pick after a gesture lifts to carry height and pitches the wrist down only afterwards. `clear_to_rotate` became `prepare_to_turn`.
- Re-ran the scratch prototype with this order and a per-step contact monitor: 9 sequences passed with zero robot-table and robot-cylinder contacts, gesture then pick 10/10 per colour with 2 cm offsets, all 6 fraction and gripper variants clean. No project code changed.

## [2026-10-09] implement | IK-driven pick-up and gesture PoC
- Implemented [[plans/ik-pick-and-gesture-poc]] (approved the same day): package `src/hri_sim/`, scripts in `src/scripts/`, `mink==0.0.13` added to `environment.yml`. Details in [[changelog]] and step by step in [[logs/ik-pick-and-gesture-poc-progress]].
- Verified in a throwaway uv environment: all five check scripts pass (M1 to M6), including the viewer window behaviours; the conda environment is still for the user to update (OI-8).
- Wiki sync: new pages [[codebase/architecture]], [[codebase/ik-and-motion]], [[codebase/skills-api]], [[codebase/how-to-run]] and [[ik-library-survey]]; plan marked `implemented` (kept as design record); open issues OI-1, OI-10, OI-11, OI-13 closed, OI-19 (gesture look) and OI-20 (mink pin) added; `AGENTS.md` got the `logs/` folder.

## [2026-10-09] lint | Wiki sync after the PoC implementation
- Checked every page for stale statements after the first code landed. Fixed: [[mujoco-primer]] (option B now implemented, no longer a pending choice), [[stretch-3-robot]] (object-pose problem marked resolved), [[timeline]] (Check-In 1 has passed; what is still unbuilt), [[open-issues]] (intro, OI-6 and OI-17 wording), [[study-design]] (what `hri_sim` already logs and what is missing).
- No unresolved wikilinks, no orphan pages, no angle-bracket characters; all pages are listed in [[index]]. Codebase pages were compared with the code and the check results (counts, timings, defaults) and agree.
- Left as they are on purpose: the conda environment is still unbuilt (OI-8) and the gesture defaults are provisional (OI-19).

## [2026-10-09] implement | Gesture redesign, code cleanup and video recording
- At the user's request: the gesture now keeps the gripper hanging, turns while closing the gripper, extends over the cylinder and lowers the lift halfway; no retract between skills, a pick at the same object only opens the gripper. Unused code removed; `demo.py --record` saves an mp4 to `src/outputs/`. Details in [[changelog]] and [[logs/ik-pick-and-gesture-poc-progress]].
- Wiki sync: [[codebase/ik-and-motion]], [[codebase/skills-api]], [[codebase/how-to-run]], [[codebase/architecture]], [[codebase/README|codebase]], [[overview]], [[open-issues]] (OI-19 reworded), [[dev-environment]] (imageio); the plan page got a note that its gesture sections are superseded.
- Gap: the scratch test environment became unavailable late in the session, so the full check suite was not re-run after the recording feature and the final tidy-up (only syntax checks, `check_recording` and one recorded demo). Recorded in [[codebase/how-to-run]].
