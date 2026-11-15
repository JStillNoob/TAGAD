# TAGAD Engagement Accuracy Improvement Checklist

Last updated: November 9, 2026  
Status: Baseline captured; diagnostics and ground-truth validation pending

This checklist tracks work to improve the validated recognition of Engaged,
Attentive, Confused, Bored, and Disengaged. Check an item only when its stated
evidence or verification gate exists. A higher displayed Engaged percentage is
not, by itself, evidence of better accuracy.

## Objective

Improve per-state recognition on real classroom video by combining facial,
gaze, temporal, and upper-body behavioral evidence while preserving privacy,
three-camera stability, and an explicit Unclassified result for weak evidence.

## Current priority — Engaged and Attentive before the boundary editor

Requested November 9, 2026. Prioritize A1/A3 evidence, A5 offline posture
feasibility, and A6 validated fusion before implementing the A4 boundary editor.
Camera-view and lesson-direction references remain necessary for interpreting
posture; the editor itself is not a prerequisite for an offline feasibility run.

- The live classifier still uses facial/head/gaze evidence. Posture is available
  only in the offline evaluator and is not integrated into official predictions.
- Both final Engaged and Attentive currently require raw Engaged from the state
  model. Attentive additionally requires LowerAttention. Diagnose these stages
  separately rather than changing the label mapping to increase displayed shares.
- Session 44 is the real classroom baseline. Its 1,821 summaries contain no
  stage-level diagnostics, and no corresponding video was recorded. Its low
  prediction shares alone cannot establish the classification error or its cause.
- The user confirmed session 50 was a setup test. Keep it as recording/timing
  evidence; do not treat it as a labeled classroom evaluation set. Its four
  submitted summaries are insufficient for classroom recognition conclusions.
- Next evidence gate is a consented recording with known lesson activities and
  independent labels using A2/A3. Check A1 stage diagnostics, then compare the
  same approved samples with the existing facial baseline and A5 pose candidate.
  Develop and validate A6 only after usable posture and reference labels exist.
- Keep A1 classroom validation, A3 collection/labeling, A5 measured feasibility,
  A6 fusion, and A7 accuracy gates open until their evidence exists. No live
  classification or model artifacts were changed during this prioritization.

## A0 — Current baseline

**Status: Complete**

- [x] Complete a live three-camera classroom session lasting 37 minutes 45 seconds.
- [x] Confirm all three cameras contribute through the end of the session.
- [x] Record 1,821 monitoring windows from the official pipeline.
- [x] Record 77.7% classification coverage and 74.4% average confidence.
- [x] Record the current distribution: Engaged 0.3%, Attentive 0%, Confused
      7.4%, Bored 50.8%, and Disengaged 41.5%.
- [x] Confirm that the earlier three-angle benchmark also produced no Engaged
      or Attentive observations.
- [x] Confirm that the backend aggregates the final labels submitted by the
      pipeline rather than creating the low Engaged result itself.
- [x] Document that the current Data Quality rating measures evidence volume,
      coverage, and confidence—not ground-truth accuracy.

### Baseline interpretation

- [x] Treat 0.3% as the Engaged prediction share, not model accuracy.
- [x] Treat 0% Attentive as a model-diagnostic signal, not proof that no students
      were attentive.
- [x] Keep enrollment, attendance, peak detections, and unique-student counts
      separate.
- [x] Keep repeated observations from different cameras separate from unique
      student identities.

## A1 — Stage-level diagnostics

**Status: Implemented; controlled classroom run pending**

- [x] Record aggregate raw-state counts per camera: Engaged, Confused, Bored, LookingAway, and Drowsy.
- [x] Record aggregate attention counts per camera: HigherAttention,
      LowerAttention, and NotReady.
- [x] Record how many confirmed tracks reach the attention model's minimum history requirement.
- [x] Record state-model probability and attention-model decision margin separately.
- [x] Record track resets or expirations without storing identities.
- [x] Keep diagnostic aggregates out of official analytics until validated.
- [x] Add tests proving diagnostic logging does not change final classifications.

### Verification gate

- [ ] A controlled run identifies whether raw Engaged scarcity, attention
      warm-up, attention output, or final mapping causes the missing states.
- [x] No frame, face crop, name, persistent track identity, or camera credential
      is stored in diagnostics.

### Implementation evidence

- [x] Store validated diagnostic intervals on the camera-attributed engagement
      summary without exposing them through teacher analytics.
- [x] Reset an interval only after the backend accepts it, preserving evidence
      across temporary submission failures.
- [x] Pass 28 pipeline tests and all 258 backend tests on November 5, 2026.
- [x] Audit the Engaged/Attentive path on November 9, 2026 and correct live
      frame sampling in the controller and standalone worker. Live sampling now
      uses elapsed time rather than advertised camera FPS. All 80 pipeline tests
      passed. Thirty-second source-timeline replays from all three session-50
      recordings produced 74 timing-only analyses each at the 2.5 Hz target,
      with original videos unchanged. This is software/sampling evidence,
      not measured classroom throughput or accuracy. See
      [findings and remaining work](ENGAGEMENT_PREDICTION_AUDIT.md).

## A2 — Operational label definitions

**Status: Draft definitions complete; independent reviewer validation pending**

- [x] Define Engaged as observable active, lesson-related involvement.
- [x] Define Attentive as observable quiet or passive lesson-related attention.
- [x] Define Confused as a visible uncertainty signal, not a negative-engagement
      assumption.
- [x] Define Bored using observable low-activation behavior without claiming an
      internal emotional state as fact.
- [x] Define Disengaged using sustained, observable off-task behavior.
- [x] Define Unclassified for missing, conflicting, or low-confidence evidence.
- [x] Include note-taking, reading, quiet listening, phone use, group work,
      occlusion, and teacher movement in the annotation guide.
- [ ] Have at least two reviewers use the same definitions independently.

### Verification gate

- [ ] Reviewers resolve disagreements or retain them as Uncertain.
- [ ] The final definitions match the capstone methodology and UI wording.

### Definition evidence

- [x] Add [`ENGAGEMENT_LABEL_GUIDE.md`](ENGAGEMENT_LABEL_GUIDE.md) with
      observable evidence, exclusions, ambiguous cases, and runtime mapping.
- [x] Reconcile the draft against the current five UI labels and identify the
      remaining ACM methodology corrections without changing runtime behavior.
- [x] Document that no camera, model, or classroom test is part of A2 drafting.

## A3 — Ethical classroom ground truth

**Status: Protocol ready; approved collection and reviewer labeling pending**

- [ ] Obtain the required participant and school permissions before collecting
      training or validation media.
- [ ] Record the anonymous number of students present separately from enrolled
      class size; do not store names or identities.
- [ ] Synchronize camera and processing-computer clocks.
- [ ] Capture synchronized Front, Left, and Right references for camera geometry.
- [ ] Collect timestamped examples of active participation, quiet listening,
      note-taking, reading, confusion, unrelated phone use, group discussion,
      resting, and looking away.
- [ ] Label time windows rather than judging engagement from one still image.
- [ ] Balance the collected examples across all five final states and Uncertain.
- [x] Define retention and deletion rules for temporary calibration media.
- [x] Keep calibration media and derived sensitive data out of Git.

### Verification gate

- [ ] A consented, timestamped ground-truth set exists with documented reviewer
      agreement and no participant identities in model outputs.
- [ ] Training, validation, and test splits are separated by participant or
      classroom session to prevent near-duplicate leakage.

### Preparation evidence

- [x] Add
      [`CLASSROOM_GROUND_TRUTH_PROTOCOL.md`](CLASSROOM_GROUND_TRUTH_PROTOCOL.md)
      with permission gates, anonymous metadata, clock synchronization,
      collection, five-second annotation, reviewer agreement, split, retention,
      deletion, withdrawal, and incident procedures.
- [x] Add a blank
      [`A3_PILOT_RECORD_TEMPLATE.md`](A3_PILOT_RECORD_TEMPLATE.md) for private
      approval, synchronization, annotation, split, privacy, and deletion
      evidence; never fill the tracked copy.
- [x] Add a blank
      [`A3_REVIEWER_WORKSHEET_TEMPLATE.md`](A3_REVIEWER_WORKSHEET_TEMPLATE.md)
      for independent, paired, five-second observation labels without names or
      persistent participant identifiers.
- [x] Protect the designated private pilot and ground-truth directories through
      `.gitignore`; outside-repository encrypted storage remains preferred.
- [x] Document that A3 preparation adds no attendance feature, face recognition,
      participant identity, runtime model change, or classroom test.
- [x] Prepare an automatic beta recorder launched by `tagad.ps1 start`, waiting
      for started sessions and closing capture when they end. Include private
      storage, recording manifests, interruption handling, and an offline source
      file for suitable captures. Short C6 test recordings were captured and
      decoded. Classroom collection, camera alignment, and labeling remain pending.
- [x] Correct variable-frame-rate handling on November 9, 2026. The recorder
      preserves source timing and treats interval variation as review metadata.
      Offline evaluation uses decoded presentation timestamps and rejects missing,
      repeated, or truncated timing. All 72 pipeline software checks passed.
      All six saved C6 videos decoded fully with increasing presentation times.
      Timing-only evaluation read five seconds from each with model execution
      stubbed, and video hashes stayed unchanged. Classroom accuracy remains unverified.
- [x] Correct the Right camera's repeated-timestamp recording failure on
      November 9, 2026. Bounded interpolation preserves encoded frames and marks
      estimated timing in manifests and offline reports. All 75 pipeline checks
      passed. A 30-second live three-camera capture produced one complete file per
      camera; Right preserved 269 frames with nine 100 ms corrections. All frames
      decoded, timestamps increased, and timing-only offline replay passed for
      the full common 26.867 seconds. All 21 earlier recording files remained
      unchanged. See [scope, limits, and evidence](RECORDER_TIMESTAMP_FIX.md).

## A4 — Camera geometry and duplicate control

**Status: Calibration plan prepared; implementation and physical validation pending**

- [ ] Configure the teacher/board direction independently for Front, Left, and
      Right cameras.
- [ ] Define student-area regions of interest that exclude the teacher area,
      doors, and irrelevant foreground where practical.
- [ ] Measure how often teachers or visitors are counted as students.
- [ ] Decide between non-overlapping camera zones and another privacy-preserving
      strategy for preventing duplicate multi-camera weighting.
- [ ] Measure face, head, and upper-body visibility separately for each camera.

### Verification gate

- [ ] Facing the camera is never used as a universal proxy for facing the lesson.
- [ ] Multi-camera aggregation does not silently treat overlapping observations
      as additional unique students.

### Preparation evidence

- [x] Inspect source mapping, per-camera inference, analytics aggregation, and
      the displayed detection-count scope.
- [x] Define a proposed per-classroom and per-camera calibration record with
      lesson targets, student polygons, exclusions, and revision/invalidation
      rules in [`CAMERA_CALIBRATION_PLAN.md`](CAMERA_CALIBRATION_PLAN.md).
- [x] Propose physical seating-zone ownership for privacy-preserving duplicate
      control, subject to validation on the three installed camera views.
- [x] Prepare a blank three-camera worksheet and define visibility, false-count,
      overlap, and sampling-rate measurements for the approved test.
- [x] Describe the existing peak count as detections in one camera sample in
      analytics and PDF reports, and append its scope to CSV exports.
- [x] Verify the scope wording with 50 frontend checks, a production build,
      and 15 report/analytics tests. Physical calibration evidence is pending.
- [ ] Implement and verify calibration support through the applicable worker,
      inference, configuration, and reporting entry points.
- [ ] Complete physical calibration and the measurement records at the approved
      classroom setup next week.

## A5 — Upper-body posture feasibility

**Status: Offline evaluator built; target agreement and measured feasibility pending**

- [ ] Benchmark a small multi-person pose model offline using consented classroom
      samples before integrating it into live sessions.
- [ ] Measure visibility and confidence for shoulders, elbows, wrists, and hips.
- [ ] Extract normalized upper-body features such as torso orientation, shoulder
      angle, leaning, arm movement, and posture stability.
- [ ] Evaluate posture over a temporal window rather than one frame.
- [ ] Treat posture as supporting evidence, not a direct label rule.
- [ ] Keep unreliable or occluded poses Unclassified.
- [ ] Measure CUDA memory, processing latency, and per-camera analysis rate with
      pose enabled.

### Verification gate

- [ ] Upper-body keypoints are usable on the actual camera angles often enough
      to justify model complexity.
- [ ] The three-camera pipeline remains stable and meets an agreed processing-rate
      target established before integration.

### Preparation evidence

- [x] Specify `yolo11n-pose.pt` as the initial candidate and document the
      shoulder, elbow, wrist, and hip keypoint contract in
      [`POSTURE_FEASIBILITY_PLAN.md`](POSTURE_FEASIBILITY_PLAN.md).
- [x] Define head/body association checks, feature normalization, temporal
      readiness, and unavailable-pose handling for the planned evaluator.
- [x] Draft measurable acceptance targets and private per-camera result tables.
- [x] Inspect the existing benchmark and identify missing posture-quality,
      source-time, and GPU-memory instrumentation.
- [x] Build the separate offline evaluator for local recordings, aggregate
      posture metrics, baseline/pose modes, three-camera contention, and resource
      measurements with source-time temporal windows.
- [x] Use decoded presentation timestamps for variable-frame-rate recordings,
      with duration and sampling checks through the normal evaluator entry point.
- [x] Pass 36 pipeline checks, including synthetic three-camera evaluator runs,
      privacy assertions, failure handling, and a safe command-help check.
- [ ] Agree and freeze the target revision before inspecting evaluation results.
- [ ] Perform the approved classroom-sample and
      three-camera performance runs at the scheduled test.

## A6 — Multimodal temporal model

**Status: Not started**

- [ ] Preserve separate facial, attention, posture, and uncertainty signals.
- [ ] Train a late-fusion model using classroom-specific ground truth.
- [ ] Use posture and hand activity to distinguish active from passive on-task
      behavior where the evidence supports it.
- [ ] Prevent looking down while writing or reading from being automatically
      mapped to Bored or Disengaged.
- [ ] Keep Confused separate from disengagement.
- [ ] Calibrate output probabilities on held-out classroom sessions.
- [ ] Version the new artifacts and update their checksums and feature contracts.

### Verification gate

- [ ] Engaged and Attentive both appear on their corresponding held-out,
      human-labeled examples.
- [ ] Improvements are measured against the face-only baseline using the same
      held-out data.
- [ ] No hard-coded rule exists solely to increase the displayed Engaged value.

## A7 — Accuracy and reliability validation

**Status: Not started**

- [ ] Establish acceptance targets before training or tuning begins.
- [ ] Report per-state precision, recall, and F1.
- [ ] Report the five-state confusion matrix and Unclassified coverage.
- [ ] Report results per camera and for the final aggregation method.
- [ ] Compare face-only, posture-only, and fused models.
- [ ] Review false Engaged, false Attentive, and false Disengaged examples.
- [ ] Confirm that improvements generalize to an unseen classroom session.
- [ ] Run a full three-camera class-period soak test with the selected model.
- [ ] Confirm that temporary camera loss does not corrupt final analytics.

### Verification gate

- [ ] Engaged and Attentive improve against ground truth without an unacceptable
      regression in Confused, Bored, Disengaged, Unclassified, or throughput.
- [ ] No end-to-end accuracy claim is published without paired classroom ground
      truth.

## A8 — Product and capstone integration

**Status: Not started**

- [ ] Decide whether the summary metric should remain Engaged-only or report a
      clearly named Engaged + Attentive positive-attention metric.
- [ ] Explain active engagement, passive attention, confusion, boredom,
      disengagement, and uncertainty in teacher-facing help text.
- [ ] Update the capstone methodology to match the final multimodal pipeline.
- [ ] Update limitations, privacy safeguards, and deployment requirements.
- [ ] Add regression tests for the final mapping and analytics calculations.
- [ ] Record the final model version in reports and exported analytics.

### Final completion gate

- [ ] Teachers can understand what each state means and how reliable it is.
- [ ] The selected model has classroom ground-truth evidence, acceptable
      three-camera performance, and documented limitations.

## Next action

Complete **A1 — Stage-level diagnostics** before adding posture or changing any
classification thresholds. Diagnostics are the smallest safe change that can
show whether the current Engaged/Attentive bottleneck is in the rich-state
model, temporal attention model, track warm-up, or final mapping.

Related evidence and trackers:

- [`PIPELINE_BENCHMARK_REPORT.md`](PIPELINE_BENCHMARK_REPORT.md)
- [`PIPELINE_GROUND_TRUTH_REVIEW.md`](PIPELINE_GROUND_TRUTH_REVIEW.md)
- [`PIPELINE_INTEGRATION_CHECKLIST.md`](PIPELINE_INTEGRATION_CHECKLIST.md)
- [`TAGAD_Pipeline_Status_for_Codex.md`](TAGAD_Pipeline_Status_for_Codex.md)
