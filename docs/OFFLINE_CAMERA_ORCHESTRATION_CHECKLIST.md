# TAGAD Offline Camera Orchestration Checklist

Last updated: September 23, 2026

**Implementation status: Complete.** The remaining long-duration and RTSP
items are follow-up hardware acceptance work, not blockers for this offline
orchestration goal.

## Goal

Use the Center, Left, and Right recordings as repeatable camera simulators to
finish session orchestration, isolation, health reporting, recovery, and load
testing before physical RTSP cameras are available.

## Non-negotiable rules

- Never add Center, Left, and Right student counts together. The same student
  appears in multiple views.
- Never treat temporary tracking IDs as student identities.
- Never persist frames, face crops, or facial landmarks.
- Keep video paths, future RTSP URLs, and credentials out of Git and API output.
- A camera failure must not end the classroom session or another camera worker.
- Simulator behavior must be visibly identified as simulated data.
- Existing single-camera analytics must remain correct while orchestration is
  developed.

## O0 — Contract and architecture

**Status: Complete**

- [x] Map the supplied recordings to Center, Left, and Right views.
- [x] Keep recordings and raw benchmark output ignored by Git.
- [x] Verify that each source works with the frozen inference pipeline.
- [x] Define an ignored local camera-source configuration format.
- [x] Map each configured source to a real TAGAD `Camera` record and position.
- [x] Define the controller's active-session discovery contract.
- [x] Define the worker heartbeat payload and state transitions.
- [x] Decide the temporary official-analytics rule before multi-camera fusion.
- [x] Document process/thread ownership and model-loading strategy.
- [x] Define shutdown, timeout, and retry timing.

### Recommended interim analytics rule

Use Center as the only source allowed to publish official engagement summaries.
Run Left and Right for health, coverage, and performance diagnostics only. This
prevents double-counting without inventing an unreliable fusion algorithm.

### Verification gate

- [x] Every schema-v2 request and stored row is attributed to one camera source.
- [x] No code path can sum unfused source counts into an official total.
- [x] The controller can discover work without exposing camera credentials.

## O1 — Backend orchestration API

**Status: Complete**

- [x] Add a pipeline-only endpoint listing active sessions and assigned cameras.
- [x] Scope the endpoint to the private pipeline credential.
- [x] Return current slide event, session state, camera ID, name, and position.
- [x] Add a validated heartbeat endpoint.
- [x] Store only operational health data.
- [x] Mark stale heartbeats Offline after a documented timeout.
- [x] Keep camera source paths and credentials out of backend responses.
- [x] Add permissions, invalid-session, stale-heartbeat, and isolation tests.

### Verification gate

- [x] A valid controller discovers only active configured work.
- [x] Missing or incorrect credentials fail closed.
- [x] Ending a session removes it from discoverable work.
- [x] A stale worker becomes Offline without affecting the session.

## O2 — Local simulated-camera configuration

**Status: Complete**

- [x] Add a committed example configuration containing no private paths.
- [x] Add an ignored local configuration for Center, Left, and Right.
- [x] Validate duplicate positions, missing files, unknown positions, and bad
      options before workers start.
- [x] Make recorded files loop while their classroom session remains active.
- [x] Label file-backed sources as Simulated in health data.
- [x] Verify that configuration errors identify the camera but hide secrets.

### Verification gate

- [x] A clean checkout explains how to create the local configuration.
- [x] `git add .` cannot include the private configuration or recordings.
- [x] One invalid source does not prevent valid sources from starting.

## O3 — Controller and worker lifecycle

**Status: Complete**

- [x] Start one isolated logical worker per assigned camera.
- [x] Reuse model artifacts safely without mixing tracker histories.
- [x] Transition each camera through Starting, Online, Reconnecting, Offline,
      and Stopped.
- [x] Follow the session's current slide event.
- [x] Stop and release sources after the teacher ends the session.
- [x] Prevent duplicate workers for the same session and camera.
- [x] Handle controller shutdown with clean worker and model cleanup.
- [x] Ensure one blocked or failed source does not stop other workers.

### Verification gate

- [x] Starting one session starts exactly its configured simulated cameras.
- [x] Repeated discovery does not create duplicate active workers.
- [x] Ending the session stops every related worker within the polling timeout.
- [x] Tracker and temporal histories never cross camera boundaries.

## O4 — Recovery and fault simulation

**Status: Complete**

- [x] Add deterministic test hooks for open failure and mid-stream disconnect.
- [x] Retry with bounded backoff and documented limits.
- [x] Transition Reconnecting to Online after recovery.
- [x] Transition Reconnecting to Offline after retry exhaustion.
- [x] Preserve idempotent backend submissions during temporary network errors.
- [x] Stop retrying immediately when the session ends.
- [x] Test unavailable/open-failed sources, interrupted reads, backend retry, and
      guarded worker failure behavior.

### Verification gate

- [x] Center failure leaves Left and Right running.
- [x] Recovered submissions retain one idempotency key across HTTP retries.
- [x] Controller errors contain camera IDs and error types but no source credentials.

## O5 — Live Session health interface

**Status: Complete**

- [x] Display each assigned camera independently.
- [x] Show camera position, Simulated badge, state, and last heartbeat.
- [x] Distinguish configured cameras from connected workers.
- [x] Show a useful message for Reconnecting and Offline states.
- [x] Keep engagement counts source-specific in diagnostic displays.
- [x] Do not claim combined classroom totals from overlapping views.
- [x] Preserve light/dark desktop readability.
- [x] Add loading, empty, unavailable, and stale states.

### Verification gate

- [x] A teacher can identify which simulated camera failed.
- [x] Health updates do not interrupt slides or session controls.
- [x] The interface never exposes local file paths or future RTSP credentials.

## O6 — Concurrent load benchmark

**Status: Complete for offline simulated sources; classroom accuracy is a follow-up**

- [x] Run Center, Left, and Right concurrently with independent trackers.
- [x] Measure total CPU, memory, throughput, and per-camera latency.
- [x] Record model-loading memory for the chosen ownership strategy.
- [x] Verify each source maintains the CPU-safe 2.5 Hz requested analysis rate.
- [x] Run repeated looping playback longer than the original short clips.
- [x] Confirm memory remains stable through a 60-minute simulated class-period
      loop; a representative continuous recording is still needed for accuracy.
- [x] Confirm orchestration remains responsive during one source failure.
- [x] Save aggregate-only benchmark results.

### Verification gate

- [x] All three workers remain isolated and responsive in the short load test.
- [x] No source starvation or continued memory growth was observed in the
      60-minute CUDA run.
- [x] Results clearly state that this is a simulated CUDA benchmark using
      repeated short recordings.

## O7 — Regression and handoff

**Status: Complete**

- [x] Add backend API and lifecycle tests.
- [x] Add controller, state-machine, retry, and isolation tests.
- [x] Add frontend unit and browser tests for health states.
- [x] Run the complete backend suite.
- [x] Run the complete frontend suite and production build.
- [x] Run real-browser end-to-end workflows.
- [x] Run migration and diff checks.
- [x] Update pipeline, operations, and troubleshooting documentation.

### Completion gate

- [x] The three recordings behave like isolated simulated cameras.
- [x] Session start/end and slide changes control workers automatically.
- [x] Failure and recovery are visible and do not cascade.
- [x] No cross-camera double-counting reaches official analytics.
- [x] Automated real-browser acceptance covers the health panel and normal
      teacher workflow.
- [x] Remaining hardware-only work is explicitly listed under P4/P5.

## Immediate next action

Run the manual acceptance flow with Django, Vite, and the controller together
if it has not yet been recorded. The next model-quality evidence is a human
ground-truth review and a representative continuous classroom recording; the
60-minute offline memory-stability gate is complete. Physical RTSP validation
remains deferred until hardware arrives.
