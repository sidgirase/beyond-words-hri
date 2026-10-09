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
