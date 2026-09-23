# TAGAD Pipeline Integration Checklist

Last updated: September 22, 2026

This checklist tracks the computer-vision pipeline separately from general
application work. Check an item only after its verification gate passes.

## P0 — Training handoff and artifact freeze

**Status: Complete**

- [x] Identify the final YOLO head detector.
- [x] Identify the final MediaPipe face-landmarker task.
- [x] Identify the rich-state SVM and its exact 25-feature order.
- [x] Identify the DIPSER attention SVM and its exact 10-feature order.
- [x] Record artifact sizes and SHA-256 checksums.
- [x] Copy the four artifacts into ignored `backend/model_artifacts/`.
- [x] Preserve the original training files on `D:`.
- [x] Verify that Git ignores every copied model artifact.

### Verification gate

- [x] All four copied files match the frozen checksums.
- [x] Both SVM models accept the frozen feature order and expected classes.

## P1 — Single-camera inference baseline

**Status: Complete**

- [x] Load YOLO, MediaPipe, and both SVM models once per worker.
- [x] Accept an MP4 path, webcam number, or RTSP source.
- [x] Detect head candidates without counting raw boxes as students.
- [x] Assign temporary geometric track IDs without facial recognition.
- [x] Require track duration and valid-face observations before confirmation.
- [x] Extract pose, gaze, and blendshape features.
- [x] Apply the rich-state classifier.
- [x] Apply the temporal attention classifier after warm-up.
- [x] Map raw outputs to the five official TAGAD engagement states.
- [x] Apply one-second state smoothing.
- [x] Report failed face extraction as Unclassified.
- [x] Avoid storing frames, face crops, and track identities.

### Verification gate

- [x] Real models load successfully in the prepared pipeline environment.
- [x] The recorded-video smoke test reaches confirmed students.
- [x] Pipeline unit and contract tests pass.

## P2 — Django integration

**Status: Complete**

- [x] Add separate configuration for all four artifacts.
- [x] Add a private session-context endpoint for the worker.
- [x] Protect worker endpoints with `X-Pipeline-Key`.
- [x] Follow the current slide event while a session is active.
- [x] Stop the worker after Django reports that the session ended.
- [x] Submit aggregate counts through the existing Stage 1 contract.
- [x] Preserve ingestion IDs across temporary request retries.
- [x] Store unclassified counts separately from engagement states.
- [x] Keep the existing dashboard, alerts, analytics, and reports compatible.

### Verification gate

- [x] Backend pipeline and websocket tests pass.
- [x] Full backend, frontend, build, and browser suites pass.

## P3 — Recording benchmark

**Status: In progress — offline CUDA stability passed; accuracy evidence pending**

- [x] Select the three supplied classroom-angle clips.
- [x] Record source resolution, FPS, duration, and frame count.
- [x] Run every supplied clip with the frozen artifacts and identical settings.
- [x] Measure average and worst processing time per analyzed frame.
- [x] Measure achieved analysis rate against the 5–10 analyses/second target.
- [x] Record candidate, valid-face, confirmed, and unclassified coverage.
- [x] Review state distributions and observable image conditions by time segment.
- [x] Compare YOLO confidence thresholds 0.25, 0.40, and 0.60.
- [x] Retain 0.60 after lower thresholds fail to improve valid-face coverage.
- [ ] Complete `PIPELINE_GROUND_TRUTH_REVIEW.md` and compare predictions with
      human-annotated ground-truth states.
- [x] Confirm memory stabilizes after model warm-up across the short clips.
- [x] Loop all three clips concurrently for 60 minutes with CUDA and confirm
      stable process memory, bounded GPU memory, and clean worker completion.
- [x] Save a benchmark summary without storing student face crops.
- [ ] Obtain and test a representative 10–30 minute or full-class recording.
- [ ] Confirm memory use remains stable during the longer recording.

### Verification gate

- [x] No crash occurs while processing all three supplied clips.
- [x] No continued resource growth occurs during the 60-minute simulated loop.
- [ ] No continued resource growth occurs during a longer recording.
- [ ] Confirmed-student counts are reasonably stable when students remain visible.
- [x] The measured three-camera rate is acceptable at the documented CPU-safe
      target of 2.5 analyses/second per source.
- [x] Known accuracy limitations are written down before hardware testing.

## P4 — Live single-camera pilot

**Status: Waiting for camera hardware**

Offline lifecycle and health preparation is tracked separately in
[`OFFLINE_CAMERA_ORCHESTRATION_CHECKLIST.md`](OFFLINE_CAMERA_ORCHESTRATION_CHECKLIST.md).

- [ ] Select one classroom camera and document its stream format.
- [ ] Keep RTSP credentials outside Git and application logs.
- [ ] Confirm that the worker can open the RTSP stream.
- [x] Add and test generic reconnection after a simulated stream interruption.
- [ ] Confirm session start, slide changes, and session end with live input.
- [ ] Verify live aggregate data appears in the dashboard and analytics.
- [x] Add a safe worker/camera health indicator.
- [ ] Test operation for one complete class period.

### Verification gate

- [ ] A temporary disconnect recovers without creating duplicate summaries.
- [ ] Ending the session releases the stream and worker resources.
- [ ] No camera URL, username, password, or raw image appears in logs.

## P5 — Three-camera classroom processing

**Status: Offline orchestration complete; live acceptance blocked by P4**

- [x] Define Front, Left, and Right simulated positions; physical coverage remains pending.
- [x] Use one isolated logical worker per camera with a safely shared model bundle.
- [x] Keep per-camera health and timing visible in the Live Session page.
- [x] Prevent double-counting by allowing Front alone to publish official analytics.
- [ ] Synchronize aggregate windows from all active cameras.
- [x] Test degraded operation when one camera is unavailable.
- [x] Benchmark CPU, GPU, and memory with all simulated cameras active; live
      network measurement remains pending.

### Verification gate

- [x] The official student count is never the sum of duplicate observations.
- [x] One failed camera does not stop the other camera workers.
- [x] Three-camera offline throughput meets the CPU-safe 2.5 Hz target.

## P6 — Operational readiness

**Status: Not started**

- [x] Discover active sessions and start workers automatically from the controller.
- [x] Add graceful shutdown and restart behavior.
- [ ] Add structured health and failure logs without sensitive data.
- [ ] Document model replacement and checksum-update procedures.
- [x] Document the current local processing-computer setup.
- [x] Add retry and isolation behavior for unavailable models or cameras.
- [ ] Run a teacher acceptance test using the normal application workflow.

### Final completion gate

- [ ] A teacher can start and end a monitored class without using a terminal.
- [ ] Administrators can identify a failed worker or camera safely.
- [ ] Analytics and reports use real pipeline data for a full session.
- [ ] Installation and recovery steps work on a clean machine.

## Immediate next action

Complete **P3 — Recording benchmark** with visual ground-truth review and a
representative continuous classroom recording when one becomes available. The
60-minute looped CUDA stability gate is complete, but repeated short clips do
not prove classroom accuracy. Do not start combined three-camera analytics
until the accuracy review and live-camera pilot pass their verification gates.
Measurements are recorded in
[`PIPELINE_BENCHMARK_REPORT.md`](PIPELINE_BENCHMARK_REPORT.md).
