# TAGAD Operational Engagement Label Guide

Last updated: November 5, 2026  
Status: Draft definitions complete; independent reviewer validation pending

## Purpose and limits

This guide defines what TAGAD's six outcomes mean for human annotation,
model evaluation, and teacher-facing interpretation. The labels describe
observable classroom behavior during a time window. They do not establish a
student's private thoughts, motivation, personality, academic ability, or
clinical emotional state.

TAGAD retains the five existing analytics labels so the guide matches the
current UI and data contract. `Unclassified` is a separate evidence-quality
outcome and must never be silently counted as `Disengaged`.

The definitions are informed by TAGAD's ACM manuscript, especially Sections
1.3 and 2.3.2, and by Hu et al.'s face-and-upper-body classroom study. The
latter supports using multiple visible cues, but its low/medium/high scheme is
not interchangeable with TAGAD's five labels. In particular, that study lists
confusion as possible high-engagement evidence, while TAGAD reports `Confused`
as its own descriptive state.

## Unit of observation

- Review a complete five-second window, not a single frame.
- Assign one label only when the visible evidence is sustained or repeated
  across the window and fits the current classroom activity.
- Use `Unclassified` when visibility is insufficient, cues conflict, the
  behavior is only momentary, or no state is clearly supported.
- Record the activity context for the window: lecture, reading, note-taking,
  individual task, group work, recitation, or transition.
- Do not record a name, face image, persistent identity, or biometric template.
- Do not combine observations from different cameras as unique students. The
  same student may be visible in more than one camera.

## Operational definitions

### Engaged - active lesson-related involvement

Use `Engaged` when the student visibly performs an active, lesson-related
behavior, such as answering or asking a question, raising a hand, presenting,
participating in assigned group work, or actively completing the current
task. Relevant writing, typing, or handling learning materials can support
this label when the activity context shows active task performance.

Do not use facing forward, smiling, eye contact, or general movement alone.
Those cues do not prove active involvement.

### Attentive - quiet or passive lesson-related attention

Use `Attentive` when the student is quietly following the lesson without an
active participation cue. Evidence may include sustained orientation toward
the teacher, board, presentation, book, notes, assigned device, or speaking
classmate, with behavior consistent with listening, reading, or following.

The student does not have to face the front camera. Looking down while reading
or taking notes can be `Attentive` when it matches the lesson context. Head
orientation or gaze alone is supporting evidence, not a complete label.

### Confused - visible uncertainty or clarification-seeking

Use `Confused` when sustained or repeated visible behavior indicates
uncertainty about the current lesson, such as hesitation followed by checking
multiple lesson sources, a puzzled facial pattern, a confusion gesture, or
seeking clarification. Prefer context-supported combinations of cues over one
facial movement.

Confusion is not automatically negative engagement or disengagement. A
confused student may still be actively trying to learn. Because TAGAD stores
one state per observation, use `Confused` only when visible uncertainty is the
dominant evidence in the window; otherwise use the supported on-task label or
`Unclassified`.

### Bored - observable low-activation pattern

The UI label `Bored` means a sustained low-activation classroom pattern, not a
claim that the system knows the student's emotion. Supporting evidence may
include prolonged inactivity, a low-energy or slumped posture, repeatedly
resting the head on a hand, or a vacant and minimally responsive pattern while
the student remains present.

Do not infer `Bored` from a neutral expression, quiet listening, disability,
fatigue, one posture, or looking down at lesson materials. When low activation
cannot be distinguished from attentive listening, reading, temporary fatigue,
or poor visibility, use `Unclassified`.

### Disengaged - sustained observable off-task behavior

Use `Disengaged` when sustained behavior is visibly unrelated to the current
lesson or the student is no longer participating in it. Examples include
prolonged orientation toward an unrelated activity, clearly unrelated phone
use, a sustained unrelated conversation, or clear sleeping/drowsiness that
prevents participation.

Do not use a brief glance away, following a moving teacher, checking another
lesson source, reading, note-taking, or lesson-related device use. When the
activity's relevance cannot be determined, use `Unclassified`.

### Unclassified - insufficient, conflicting, or unreliable evidence

Use `Unclassified` when TAGAD or a reviewer cannot support one of the five
behavioral labels. Reasons include occlusion, blur, a face or upper body being
too small, missing landmarks, weak model confidence, conflicting cues,
temporary transitions, uncertain activity context, or insufficient visible
time.

Human review worksheets may write `Uncertain`; for comparison with TAGAD,
`Uncertain` maps to the system outcome `Unclassified`. This is a valid result,
not a negative state and not an error to hide.

## Common classroom cases

| Situation | Label guidance |
| --- | --- |
| Quiet listening | `Attentive` when sustained and consistent with the lesson. |
| Reading assigned material | Usually `Attentive`; `Engaged` only with clear active task performance. |
| Taking notes | `Attentive` for quiet following; `Engaged` when visibly performing an active assigned response. |
| Raising a hand, answering, presenting | `Engaged` when related to the lesson. |
| Group work | `Engaged` when contributing; `Attentive` when visibly following; do not require front-facing orientation. |
| Looking down | Use lesson context; never map automatically to `Bored` or `Disengaged`. |
| Phone or device use | `Disengaged` only when clearly unrelated and sustained; otherwise use the supported on-task label or `Unclassified`. |
| Puzzled expression | `Confused` only when sustained or supported by another uncertainty cue. |
| Head resting on a hand | Insufficient alone; combine with the time window and other visible evidence. |
| Teacher moves across the room | Following the teacher can remain `Attentive`; camera-facing direction is not the lesson target. |
| Occlusion, side profile, blur, or blocked face | `Unclassified` unless other validated evidence clearly supports a state. |
| Transition between activities | `Unclassified` if no dominant classroom state is observable. |

## Annotation decision sequence

1. Confirm the observation belongs to a student area, not the teacher or a
   visitor.
2. Confirm enough of the student is visible for the full-window judgment.
3. Read the recorded classroom activity and lesson target for that window.
4. Look for active lesson-related behavior (`Engaged`).
5. Otherwise, look for quiet lesson-following behavior (`Attentive`).
6. If visible uncertainty dominates, use `Confused` without treating it as
   disengagement.
7. Use `Bored` only for a sustained low-activation pattern and `Disengaged`
   only for sustained observable off-task behavior.
8. If the evidence is weak, brief, conflicting, or context-dependent, use
   `Unclassified`.

The sequence is a review aid, not a rule for forcing a label. Conflicting
evidence ends in `Unclassified`.

## Relationship to the current runtime

This guide does not change the deployed classifier. The current runtime mapping
remains:

| Current model evidence | Current final output |
| --- | --- |
| Raw `Engaged` + `HigherAttention` | `Engaged` |
| Raw `Engaged` + `LowerAttention` | `Attentive` |
| Raw `Engaged` before attention is ready | `Engaged` |
| Raw `Confused` | `Confused` |
| Raw `Bored` | `Bored` |
| Raw `LookingAway` or `Drowsy` | `Disengaged` |
| Missing or unreliable classification | `Unclassified` |

The runtime currently uses head pose, gaze, and facial blendshapes. It does not
yet observe all behaviors listed in this human annotation guide. Upper-body
posture remains an A5 feasibility task, and multimodal fusion remains A6.

## Capstone reconciliation notes

The ACM manuscript already defines TAGAD as a behavioral engagement system
with the same five UI labels, but the following points must be corrected before
the A2 methodology-alignment gate can close:

- Table 6's head-pose and gaze ranges are training-label assumptions, not
  complete operational definitions or proof of a student's internal state.
- Confused, Bored, and Disengaged must remain separate reported states. The
  manuscript's Equation 2 currently groups all three into a value named
  `disengagement rate`, while the implemented analytics do not.
- The methodology must add `Unclassified` for insufficient evidence.
- Engaged must mean active lesson-related behavior, while Attentive means quiet
  or passive lesson-following behavior.
- Future posture evidence may support these labels only after A5 and A6
  validation; facing the camera must never be the universal attention rule.

## Reviewer validation still required

Before these definitions become final ground truth, at least two reviewers
must independently label the same consented windows. They must compare their
decisions, document disagreements, and either agree on a supported state or
retain `Uncertain`/`Unclassified`. No classroom review is scheduled or executed
as part of A2 documentation work.

## Research basis

- M. Hu et al., "Bimodal Learning Engagement Recognition from Videos in the
  Classroom," *Sensors*, vol. 22, no. 16, 5932, 2022.
  <https://doi.org/10.3390/s22165932>
- TAGAD ACM manuscript, Sections 1.3, 2.3.2, and Table 6, October 2026.
