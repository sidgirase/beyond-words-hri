---
title: Study design and measures
type: concept
sources: [proposal-beyond-words, dogan-2022-follow-up-clarifications, idea-analysis]
updated: 2026-09-29
---

# Study design

## Design (from [[proposal-beyond-words]])
- **Factorial design**; IV = clarification strategy, 4 levels ([[clarification-strategies]]).
- **Between-subjects** preferred; fallback **within-subjects** with counterbalancing if recruitment is low.
  (Dogan et al. used within-subjects, N=63, counterbalanced condition order.)
- **Dependent variables**
  - Objective: task completion time, task success rate, number of clarification turns.
  - Subjective: frustration, trust, perceived intelligence (Likert-scale items), open-ended questions.
- Manipulation check: did people read reach-and-pause as a confirmation request? Asked *after* the
  interaction.
- Validity: same task difficulty, layouts and robot capability across conditions (internal validity);
  controlled setting limits external validity.

## Instruments to consider
- From [[dogan-2022-follow-up-clarifications]]: "The task was easy to perform", "The robot could understand
  my instructions" (7-point), RoSAS Competence factor.
- From [[idea-analysis]]: Mannem et al. 2023 found objective interruption cost small but perceived
  helpfulness dropped sharply → make perception DVs primary.

## Glossary terms used in the proposal
Within-subjects, between-subjects, mixed methods, factorial design, independent / dependent variables,
Likert scale, external validity, internal validity.

## What the sim must log (for the objective DVs)
Per trial: participant/condition ids, scene seed, instruction text, each robot turn (question/gesture) and
human response with timestamps, chosen object, placed-in-bin outcome, total time.
