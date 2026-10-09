---
title: "Proposal — Beyond Words (team proposal)"
type: source
sources: [src/ProjectProposalTemplate.pdf]
updated: 2026-09-29
---

# Proposal: *Beyond Words: Evaluating Verbal and Gestural Clarification Strategies During Ambiguous Robot Instructions*

Raw file: `src/ProjectProposalTemplate.pdf` (the filled-in proposal, despite the file name).
Authors: Om Shivam Verma, Rena Nakashima, Siddhesh Girase. CS 7633 Fall 2026.

## Summary
People give robots ambiguous instructions; a robot can act on its best guess or ask. Prior work shows
selective clarification beats always/never asking (Whitney et al. 2017) and targeted follow-up questions
raise perceived competence ([[dogan-2022-follow-up-clarifications]]); legible motion helps humans infer
goals (Dragan et al. 2013). VLA work (Ask-to-Clarify, 2025) evaluates success/accuracy/latency but not
workload, frustration or trust. The project compares **verbal, gestural and hybrid clarification** plus a
no-clarification baseline on both performance and perception.

## Key content
- **Conditions (IV, 2×2):** Immediate action / Ask verbally / Arm gesture (lean toward hypothesized
  target and pause; user nudges or corrects) / Hybrid ask-and-gesture. In 2–4 the robot waits for a
  response. Details: [[clarification-strategies]].
- **Simulation first:** Hello Robot `stretch_mujoco` for task scenarios, communication interface,
  clarification logic, arm gestures and data logging. Then transfer to a physical Stretch 2 or 3.
  "Conclusions about physical HRI will be based on the physical study." See [[stretch-3-robot]].
- **Task:** fixed set of tasks; participants get task descriptions or target images and phrase requests
  in their own words, via speech *or* a chat interface (pick one before the study). Participants can
  interrupt and mark success/failure. Completion time measured.
- **Ambiguity:** similar distractors "such as multiple cups and blocks", like [[dogan-2022-follow-up-clarifications]]
  and Whitney 2017. Participants aren't told to be ambiguous; a pilot checks scenes are ambiguous enough
  without causing unrelated perception/grasp failures. See [[ambiguous-scene-design]].
- **Evaluation:** between-subjects (fallback: within-subjects, counterbalanced). DVs: completion time,
  success rate, # clarification turns; frustration, trust, perceived intelligence; post-survey with
  open-ended items; manipulation check on whether reach-and-pause read as a confirmation request.
  See [[study-design]].
- **Timeline / rubric:** see [[timeline]].

## References cited
1. Dogan, Torre, Leite — HRI 2022 → [[dogan-2022-follow-up-clarifications]]
2. Dragan, Lee, Srinivasa — Legibility and predictability of robot motion, HRI 2013 (pre-2021 paper)
3. Hello Robot — `stretch_mujoco` GitHub repo
4. Horter, Markham, Trigoni, Booth — Should Robots Comply with Our Instructions or Intentions? HRI 2026
5. Lin et al. — Ask-to-Clarify, arXiv:2509.15061 (2025)
6. Ren et al. — KnowNo: Robots That Ask For Help, CoRL 2023
7. Whitney, Rosen, MacGlashan, Wong, Tellex — Reducing Errors in Object-Fetching Interactions through Social Feedback, ICRA 2017

## Implications for the code
- The robot's "brain" must be swappable: teleop now, scripted/VLA policy later, with the clarification
  layer sitting between the instruction and the policy.
- The **arm-gesture condition** needs a "reach toward target, pause, wait" primitive — not just
  pick-and-place. Worth designing the action interface so this fits.
- Logging (timestamps, turns, outcome) is an explicit deliverable of the sim stage.

**Warning — internal inconsistency.**
The timeline mentions a "VLA deployment", a "gamified" GUI, a "scoring metric" and "Score Debrief"
surveys, and the rubric mentions "HRI deception methodologies" — none of these appear in the
methodology section. Probably leftovers from an earlier draft; clarify with the team.
