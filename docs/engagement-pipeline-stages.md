# TAGAD Engagement Pipeline Implementation Stages

## Purpose

This document divides the TAGAD computer-vision pipeline into independently
testable stages. It is based on the ACM project document and the current TAGAD
Django, Vue, and PostgreSQL implementation.

The intended production flow is:

```text
Three camera feeds
  -> YOLOv11 head detection
  -> temporary tracking
  -> MediaPipe Face Mesh feature extraction
  -> [pitch, yaw, roll, horizontal gaze, vertical gaze]
  -> scaler and RBF SVM classification
  -> temporal smoothing and class aggregation
  -> active-slide synchronization
  -> PostgreSQL summaries and alerts
  -> WebSocket updates
  -> Vue live dashboard, analytics, and reports
```

## Fixed project requirements

- Support front, left, and right classroom camera positions.
- Detect student heads using YOLOv11.
- Process detections above the configured confidence threshold; the ACM's
  initial threshold is `0.5`.
- Extract pitch, yaw, roll, horizontal gaze, and vertical gaze with MediaPipe.
- Classify Engaged, Attentive, Confused, Bored, or Disengaged using an RBF SVM.
- Associate every stored summary with the active presentation slide.
- Alert the teacher when slide-level disengagement exceeds 50%.
- Store aggregated results rather than individual student identities.
- Never store raw camera frames, face crops, or facial images.
- Target no more than two seconds of processing latency.
- Eventually support up to 40 visible students across three feeds.

## Scope decision required

The ACM contains conflicting descriptions of body posture. One section mentions
posture analysis, while the formal scope states that TAGAD only measures head
pose and eye gaze and does not use body posture. Until the ACM is formally
revised, implementation should use only the five specified facial-geometry
features. Body-pose estimation is out of scope.

## Stage 1 — Pipeline contract and simulator

**Status: Implemented and verified on September 8, 2026.**

### Objective

Complete and test the application-side real-time workflow before cameras and
trained model files are available.

### Tasks

- [x] Define a versioned engagement-result payload.
- [x] Include session, slide event, capture time, five state counts, total
      detected, unclassified count, average confidence, and pipeline version.
- [x] Validate the backend-only worker credential and active session/slide.
- [x] Build a simulator that emits realistic engagement distributions.
- [x] Associate simulated summaries with the currently active `SlideEvent`.
- [x] Store only aggregated data in `EngagementSummary`.
- [x] Generate an alert only after disengagement remains above 50% for a
      configured number of consecutive windows.
- [x] Send live summaries and alerts to the correct session dashboard.
- [x] Update analytics and report generation to accept simulated summaries.
- [x] Add permission, validation, synchronization, and alert tests.

### Suggested payload

```json
{
  "schema_version": 1,
  "session_id": 15,
  "slide_event_id": 42,
  "captured_at": "2026-09-08T19:20:00+08:00",
  "counts": {
    "engaged": 18,
    "attentive": 10,
    "confused": 3,
    "bored": 2,
    "disengaged": 2
  },
  "total_detected": 35,
  "unclassified": 3,
  "average_confidence": 0.86,
  "pipeline_version": "simulator-1"
}
```

### Verification gate

- [x] A session can receive simulated results without a physical camera.
- [x] Changing slides sends subsequent summaries to the new slide.
- [x] Other users and organizations cannot operate or subscribe to the session.
- [x] The dashboard updates without refreshing through a scoped WebSocket.
- [x] Alerts do not trigger from a single bad sample.
- [x] Completed-session analytics and reports use the stored summaries.

## Stage 2 — Offline single-video computer vision

### Objective

Produce validated feature vectors from a saved classroom video without Django
or live-camera complexity.

### Tasks

- [ ] Collect or prepare an annotated classroom-head dataset.
- [ ] Train or obtain YOLOv11 weights containing an actual head class.
- [ ] Load one recorded classroom video.
- [ ] Sample frames at a configurable rate instead of processing unnecessarily.
- [ ] Detect heads and retain confidence scores.
- [ ] Add temporary track IDs using ByteTrack or YOLO tracking.
- [ ] Expand and normalize each valid head crop for MediaPipe.
- [ ] Extract facial landmarks and calculate the five geometric features.
- [ ] Mark failed or obstructed detections as unclassified.
- [ ] Immediately release frames and crops after inference.
- [ ] Export numerical features and diagnostic metrics only.
- [ ] Measure detection rate, feature-extraction success, latency, and memory.

### Verification gate

- [ ] Head detections are visually validated using temporary debug output only.
- [ ] MediaPipe failures do not become Disengaged classifications.
- [ ] Track IDs are temporary and are not stored as student identities.
- [ ] No raw images or face crops remain after the process exits.
- [ ] The single-video pipeline stays within the latency target.

## Stage 3 — SVM dataset and training

### Objective

Create a reproducible, independently evaluated engagement classifier.

### Tasks

- [ ] Produce labeled rows containing pitch, yaw, roll, horizontal gaze,
      vertical gaze, and engagement label.
- [ ] Document how human reviewers assign ground-truth labels.
- [ ] Treat the ACM angle thresholds as initial labeling guidance, not final
      proof of a student's cognitive or emotional state.
- [ ] Remove invalid and incomplete MediaPipe samples.
- [ ] Split training, validation, and test data by student or recording session.
- [ ] Prevent adjacent frames from the same person appearing across splits.
- [ ] Train `StandardScaler` and `SVC(kernel="rbf")` in one sklearn pipeline.
- [ ] Tune `C` and `gamma` using validation data only.
- [ ] Measure accuracy, per-class precision, recall, F1, and confusion matrix.
- [ ] Review confusion between Confused, Bored, and Disengaged carefully.
- [ ] Save the scaler and SVM as one versioned model artifact.
- [ ] Save feature order, label mapping, library versions, metrics, and model
      checksum as metadata.

### Verification gate

- [ ] Re-running training with the same seed gives reproducible results.
- [ ] Evaluation uses unseen students or unseen recording sessions.
- [ ] Every predicted class maps to one official TAGAD state.
- [ ] Loading incompatible features or model metadata fails safely.
- [ ] Reported metrics include results for every class, not accuracy alone.

## Stage 4 — Real inference integration

### Objective

Replace simulated classifications with the real single-camera pipeline while
keeping the same result contract.

### Tasks

- [x] Add a dedicated background pipeline worker; do not process video inside a
      normal Django request.
- [x] Load YOLO, MediaPipe, and both SVM pipelines once when the worker starts.
- [ ] Start and stop processing from the classroom-session lifecycle.
- [x] Read one USB camera index, RTSP URL, or recorded test source.
- [x] Apply temporal smoothing over a documented time window.
- [x] Aggregate confirmed-track predictions into class-level counts.
- [x] Submit the existing Stage 1 payload to Django.
- [x] Retry temporary backend/network failures with an idempotent payload.
- [ ] Reopen the camera source after a temporary stream failure.
- [ ] Display pipeline health without exposing camera credentials.
- [ ] Compare real-model results with simulator results and stored summaries.

### Verification gate

- [ ] Starting a session starts one worker job.
- [x] Ending a session releases the camera and model job when the worker next polls.
- [x] Slide changes remain synchronized during processing.
- [ ] Restarting the worker does not create duplicate summaries.
- [ ] The live dashboard, alerts, analytics, and reports work unchanged.

## Stage 5 — Three-camera processing and performance

### Objective

Expand the validated single-camera implementation to the final classroom setup.

### Tasks

- [ ] Configure front, left, and right sources without exposing RTSP passwords.
- [ ] Assign non-overlapping seating zones to avoid counting one student from
      multiple cameras.
- [ ] Process streams concurrently with bounded queues and backpressure.
- [ ] Drop stale frames instead of allowing delay to grow continuously.
- [ ] Aggregate results from all zones into one class distribution.
- [ ] Test 20, 30, and 40 visible students.
- [ ] Test normal lighting, glare, partial obstruction, and different seating.
- [ ] Measure end-to-end latency, inference time, frame sampling rate, CPU/GPU,
      RAM, landmark success rate, and dropped frames.
- [ ] Confirm the dashboard remains responsive during processing.
- [ ] Document the supported hardware and actual tested capacity.

### Verification gate

- [ ] Students are not double-counted across camera zones.
- [ ] Results arrive within two seconds under the validated load.
- [ ] Camera failure is visible to the teacher and does not crash the session.
- [ ] No raw facial data is written to logs, media storage, or the database.
- [ ] Performance claims match measured results rather than assumptions.

## Stage 6 — Pilot evaluation and release readiness

### Objective

Validate accuracy, privacy, usability, and operational reliability in a
controlled classroom pilot.

### Tasks

- [ ] Obtain required institutional, teacher, student, and privacy approvals.
- [ ] Publish a clear notice describing what is and is not measured.
- [ ] Run functional testing for complete teacher workflows.
- [ ] Compare predictions with independently annotated pilot recordings.
- [ ] Produce final accuracy, precision, recall, F1, and confusion matrix.
- [ ] Perform performance, stability, usability, and user-acceptance testing.
- [ ] Verify role permissions and organization isolation.
- [ ] Verify retention and deletion procedures for aggregated data.
- [ ] Complete deployment, recovery, and operator documentation.

### Verification gate

- [ ] Stakeholders accept the measured accuracy and documented limitations.
- [ ] Privacy controls match the ACM and Philippine Data Privacy Act direction.
- [ ] Teachers can start, monitor, finish, and report a session without
      technical assistance.
- [ ] The release passes automated tests and a complete classroom rehearsal.

## Recommended implementation order

Do not build all stages simultaneously. Complete each verification gate before
starting the next stage:

1. Pipeline contract and simulator
2. Offline single-video feature extraction
3. Dataset preparation and SVM training
4. Real single-camera integration
5. Three-camera and performance validation
6. Controlled pilot and release readiness

The immediate next programming task is Stage 1. It allows the existing session,
slide, alert, analytics, and reporting functionality to be validated before the
camera hardware and trained model artifacts are available.
