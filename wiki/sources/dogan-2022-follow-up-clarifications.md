---
title: "Dogan, Torre & Leite 2022 — Asking Follow-Up Clarifications"
type: source
sources: [src/Asking_Follow-Up_Clarifications_to_Resolve_Ambiguities_in_Human-Robot_Conversation.pdf]
updated: 2026-09-29
---

# Asking Follow-Up Clarifications to Resolve Ambiguities in Human-Robot Conversation

F. I. Dogan, I. Torre, I. Leite (KTH). HRI 2022, pp. 461–469. DOI 10.1109/HRI53351.2022.9889368.
Code/data: github.com/IrmakDogan/Resolving-Ambiguities. Reference [1] of [[proposal-beyond-words]].

## Summary
When a user's referring expression ("hand me the green vegetable") matches several objects, or names an
object the detector doesn't know, most systems ask the user to repeat. This paper instead asks yes/no
**follow-up clarification questions** built from what the robot *did* understand plus spatial relations
to objects it *can* detect ("Is the green vegetable to the left of the knife?"). A within-subjects study
(N=63, Pepper robot) compared this against asking for a re-description.

## Pipeline (§II)
1. Grad-CAM heatmap of the image conditioned on the expression → K-means → two most active candidate
   regions C.
2. DETR detects known objects O_S; spaCy extracts noun phrases O_E. Candidates are widened by half their
   size to include reference objects; C_f = candidates containing a detected object named in O_E.
3. |C_f| = 1 → unambiguous: detectable target → nearest detection with that name; undetectable → MDETR.
4. |C_f| = 0 or more than 1 → ambiguous: Relation Presence Network finds spatial relations (left, right, in front,
   behind, close to); Relation Informativeness Network picks the most unique one; ask
   "target relation reference?" per candidate.

## Study (§III–IV)
- 2 table setups, same objects, different layouts; 6 target objects each (3 detectable, 3 not).
  Participants stood across the table from the robot, described objects in a given order, and **put each
  described object in a basket** after it was identified.
- Max 2 clarification questions (or 2 re-descriptions) per object, then move on.
- Autonomy (Beer et al. 2014 levels): shared control for speech capture, full automation for questions,
  decision support for picking up — the robot never physically grasped anything.
- **Results:** clarification → more correct IDs (292 vs 164 of 378; χ²(2)=154.25, p under .001), fewer
  attempts, task rated easier (5.89 vs 4.98), higher perceived understanding (5.79 vs 3.86) and RoSAS
  competence (5.58 vs 4.15). Re-descriptions were near-repeats (1-gram BLEU 0.784).
- Limitation: yes/no answers throw away extra info users volunteer after "no".

## The table scene (Fig. 1, Fig. 3) — what "ambiguous objects" means here
White table, ~25–30 objects, deliberately **many duplicates and look-alikes** in similar spatial
arrangements:
- Produce: several **bananas**, red **apples**, **oranges**, **lemons**, green and red **bell peppers**,
  **artichokes**, leafy greens (basil / lettuce), a green cucumber-like vegetable.
- Utensils: multiple **knives**, **forks**, **spoons**.
- Containers: water **bottles**, **cups**, small dark **bowls**.
- Mix of detector-known names (banana, apple, orange, knife, fork, spoon, cup, bottle) and unknown ones
  (artichoke, basil, lemon, pepper) — the "detectable vs. undetectable" split.

This is the reference for [[ambiguous-scene-design]].

## Relevance to this project
- Establishes the "ask" condition's expected advantage and the measures (task ease, perceived
  understanding, RoSAS competence) that [[study-design]] reuses.
- Only compares *verbal* strategies; our project adds gesture and hybrid ([[clarification-strategies]]).
- Their robot never manipulated objects; ours must actually pick-and-place, which is why the sim stack
  ([[stretch-3-robot]]) matters.
