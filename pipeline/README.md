# TAGAD camera pipeline

This worker runs the frozen two-model hierarchy outside Django:

1. YOLO detects head candidates.
2. A temporary geometric tracker confirms stable students.
3. MediaPipe extracts head pose, gaze, and blendshape features.
4. The rich-state SVM predicts the raw classroom state.
5. The temporal attention SVM separates Engaged from Attentive after warm-up.
6. Only aggregate counts are sent to Django; frames, face crops, and track IDs are not stored.

The single-camera command accepts a recorded MP4, webcam number, or RTSP URL.
The offline controller also runs Front, Left, and Right sources as isolated
logical workers. It shares one model bundle behind an inference lock while each
camera keeps its own tracker and temporal history.

## Local setup

The four artifacts belong in `backend/model_artifacts/`. That directory and the
model file extensions are ignored by Git. The worker verifies their byte sizes
and SHA-256 checksums against `pipeline/artifact-manifest.json` before loading
them.

The prepared Python 3.11 environment is stored inside the project at
`pipeline/.venv` and ignored by Git. From the repository root, activate it with:

```powershell
pipeline\.venv\Scripts\Activate.ps1
```

This machine uses the CUDA 12.6 builds of PyTorch 2.14 and Torchvision 0.29 so
YOLO can run on its NVIDIA GPU. Developers recreating the environment should
install `pipeline/requirements.txt`, then replace PyTorch with the appropriate
CUDA build selected at https://pytorch.org/get-started/locally/.

## Safe offline smoke test

Run this from the repository root. It loads the real models and analyzes ten
sampled frames without contacting Django:

```powershell
$env:PYTHONPATH = "$PWD\pipeline"
python -m tagad_pipeline.worker --source "D:\TAGAD\videos\classroom_test.mp4" --dry-run --max-analysis-frames 10
```

Add `--preview` to see the video and counters. Press `Q` to stop.

## Connect it to a live TAGAD session

Set the same long random secret in `backend/.env`:

```env
PIPELINE_API_KEY=replace-with-a-long-random-value
```

Then set the worker-only environment variable in its PowerShell window. Do not
put an RTSP password or the API key in Git:

```powershell
$env:TAGAD_PIPELINE_API_KEY = "replace-with-the-same-long-random-value"
$env:PYTHONPATH = "$PWD\pipeline"
python -m tagad_pipeline.worker --source 0 --session-id 12
```

Replace `0` with a local video path. For an RTSP URL that contains camera
credentials, keep it out of command history and set it in the worker window:

```powershell
$env:TAGAD_CAMERA_SOURCE = "rtsp://camera-user:camera-password@camera-address/stream"
python -m tagad_pipeline.worker --session-id 12
```

Django must be running at `http://127.0.0.1:8000`; use `--backend-url` only if
it runs elsewhere. The worker does not print the source or credential. It
follows the session's current slide automatically and stops when the session
ends.

## Run the offline three-camera controller

Copy `pipeline/camera_sources.example.json` to the ignored
`pipeline/camera_sources.local.json`, then change only the local copy to point
to the camera sources. Set the matching IPv4 address on each camera record in
TAGAD's Classes page. For live RTSP sources, the controller matches that saved
IP to the host in the private RTSP URL, so cameras with the same Front, Left,
or Right position in different classrooms cannot be mixed up. Legacy records
without an IP use position matching only when exactly one source has that
position.

Run Django, start a classroom session in the browser, then open a separate
PowerShell window at the repository root:

```powershell
$env:TAGAD_PIPELINE_API_KEY = "replace-with-the-same-private-value"
$env:PYTHONPATH = "$PWD\pipeline"
pipeline\.venv\Scripts\python.exe -m tagad_pipeline.controller
```

When the repository-level `scripts\tagad.ps1 start` command is used, it starts
this controller automatically and supplies a local stop signal so
`scripts\tagad.ps1 stop` can shut workers down cleanly. API keys, camera source
paths, and RTSP credentials remain outside Git.

The setup page checks each saved camera IP on RTSP port 554 and reports
Checking, Available, Offline, or Not initialized without exposing video or
credentials. The controller discovers prepared and active meetings every two
seconds, follows slide changes, loops simulated files, and stops workers after
the teacher ends the session. The Live Session page displays Preparing, Online,
Reconnecting, Offline, or Stopped for each source. Preparing uses the existing
`starting` API state.

Live camera analysis is scheduled from elapsed monotonic time at the configured
`analysis_hz`, rather than skipping a fixed number of frames using advertised
FPS. Variable delivery rates therefore do not introduce an additional fixed
sampling reduction. Actual processing speed and valid-face availability still
limit attention readiness. Simulated sources retain their existing frame-step
sampling. See the [prediction bottleneck audit](../docs/ENGAGEMENT_PREDICTION_AUDIT.md).

During initial preparation, an independent reporter refreshes the worker's
current status at intervals of up to two seconds plus request time while stream opening, decoding, or
shared inference is busy. Online requires a processed frame. A 60-second
startup deadline reports Offline with retry guidance if that frame has not
completed. A later successful frame restores readiness through Starting and
Online. Cancellation joins the reporter before publishing the final status.
After readiness, regular heartbeats continue to depend on frame processing.

The first decoded frame is processed immediately, followed by the configured
sampling interval. Status and work-discovery requests use a maximum three-second
request timeout and the next regular cycle for retry. Engagement submissions
retain their configured timeout and retry policy. Local controller logs record
initial preparation, stream opening, reading, inference-queue wait, and processing
times so real-camera delays can be measured. Starting a prepared meeting reuses
its workers and streams.

To exercise recovery, add these optional fields to one
camera in the ignored local file:

```json
"simulate_disconnect_after_frames": 30,
"simulate_disconnect_seconds": 2
```

Front, Left, and Right each submit camera-attributed official summaries. Session
analytics combine those observations; overlapping views can still observe the
same student more than once until seating zones are calibrated.

Run the aggregate-only concurrent load smoke test with:

```powershell
$env:PYTHONPATH = "$PWD\pipeline"
pipeline\.venv\Scripts\python.exe -m tagad_pipeline.concurrent_benchmark --duration-seconds 20
```

On the current CPU, the verified three-camera setting is 2.5 analyses/second
per source. The prior 8 Hz single-camera setting is not sustainable for three
sources without faster hardware.

## Current limitations

- This machine's verified PyTorch environment uses CUDA for YOLO. MediaPipe,
  video decoding, tracking, and the SVM stages still use the CPU. A 60-minute
  three-source looped stability test passed, but repeated short clips do not
  replace accuracy testing with a representative continuous classroom recording.
- Tracking IDs are temporary geometric IDs, not student identity or facial
  recognition.
- A confirmed student needs at least 1.2 seconds and five valid face readings.
- A confirmed track whose face cannot currently be classified is reported as
  Unclassified, never silently changed to Disengaged.
- Physical RTSP opening, network recovery, camera placement, and full-session
  stability remain hardware acceptance work.

## Record the approved beta test

Automatic beta recording is enabled by `TAGAD_RECORD_SESSIONS=1` in the private
`backend/.env`. The example configuration defaults to `0` for installations
that have yet to enable approved recording. PyAV `18.1.0` is included in the
pipeline requirements. Start TAGAD with the usual command.

```powershell
.\scripts\tagad.ps1 start
```

The launcher checks recorder readiness and starts a tracked background recorder
in standby. Preparation and countdown keep it idle. After the session starts,
the recorder polls the authenticated backend every two seconds and opens the
selected cameras. Their saved IP addresses and positions must match the live
sources in `pipeline/camera_sources.local.json`. An unmatched assignment is
reported in `.runtime/recorder-*.out.log` and retried. The current local pilot
records one active session at a time.

Ending the session closes its files and returns the recorder to standby for
the next session. Automatic capture follows the session duration. A backend
connection failure closes capture until session activity can be confirmed
again. Recovery creates a fresh recording folder. Use `tagad.ps1 status` to
check that the recorder process is running, and `tagad.ps1 stop` to close it
with the other TAGAD services.

The continuation backend's Save and Finish actions both close the current
meeting. Continuing the lesson prepares a new meeting, then starts a fresh
capture under its new session ID after camera readiness succeeds. Camera
workers request 10-second RTSP open and 5-second read timeouts. A closing
worker retains its source until its thread exits, allowing the next meeting
to open it after closure. Polling and in-flight operations affect the delay.
Physical RTSP behavior is verified during the scheduled hardware acceptance.

The recorder saves separate Front, Left, and Right video-only MP4 files under
`C:\TAGAD_PRIVATE_PILOT\PILOT-<UTC-time>-<random-code>`. Each new session folder
receives access restricted to the current Windows user and SYSTEM.
Existing recordings are preserved in separate session folders.

Allow camera connections to settle after session start, then make a common
visual synchronization cue. Each camera logs `receiving video` in the recorder
output log. Record camera clock offsets using the A3 pilot record.
The manifest stores the TAGAD session ID, host timestamps, packet counts,
failures, and a 30-day
deletion reminder. Review and delete recordings under the approved retention
schedule.

A camera interruption triggers reconnection with backoff for the active
session, saved as separate numbered parts. Other cameras continue. Partial
captures remain marked for review. Fragmented MP4 preserves
written fragments for recovery after an interrupted process, subject to media
validation.

The recorder copies compressed video packets using PyAV's remuxing API.
Camera credentials are read within the process from private configuration.
Reports contain camera positions and file metadata. Raw media remains in the
private session folder.
[PyAV remuxing](https://pyav.org/docs/stable/cookbook/basics.html#remuxing)

For successful single-part captures, the session folder also contains
`offline-sources.json` for the posture evaluator. Review the manifest and
camera alignment before using that file. The evaluator uses decoded frame
presentation timestamps, including variable frame intervals. The legacy
`irregular_timestamp_intervals` counter records differences from nominal camera
FPS for review. That variation alone allows offline input preparation.
For streams without frame reordering, the recorder spaces a group of up to eight
duplicate-timestamp packets between neighboring valid timestamps. It preserves
the encoded frames. Correction spans above one second or below the timestamp
resolution fail capture. If a meeting ends inside a duplicate group, spacing uses
the last observed frame interval, or nominal FPS when no interval is available.
The manifest records corrected-packet counts, tail estimates, maximum adjustment,
and `timing_review_required`. These corrected times are estimates and require
review for evaluation. Offline reports carry the matching manifest hash and
timing counters under each input's `recording_timing` metadata.
Backward decode timestamps still fail capture. Unsupported reordered duplicates,
missing or repeated presentation timestamps in evaluated files, and truncated
video remain failures. Interrupted captures need private preparation before
evaluation. See [timestamp verification evidence](../docs/RECORDER_TIMESTAMP_FIX.md).

The local check requires at least 2 GiB free. Recording stops at a 512 MiB
reserve. Allow space for the whole planned session. At 4 Mbps per camera,
three 60-minute videos occupy approximately 5.4 GB before container overhead.

The standalone `scripts/record-beta.ps1 -Check` remains available for a local
readiness check. Its manual capture mode supports `-Minutes` and `-OutputRoot`
and should be used while the automatic recorder is stopped to avoid duplicate
captures. Physical camera recording and full-session stability verification
are pending the scheduled beta test.

## Three-angle benchmark

For the scheduled offline posture comparison, see
[`POSTURE_FEASIBILITY_PLAN.md`](../docs/POSTURE_FEASIBILITY_PLAN.md).
The separate `tagad_pipeline.posture_benchmark` command compares recorded-video
baseline and pose modes and writes aggregate results with human review pending.

Place local test recordings in the ignored `pipeline/test_video/` directory.
The benchmark processes every video independently with one shared model load;
it does not add the camera counts together.

```powershell
$env:PYTHONPATH = "$PWD\pipeline"
python -m tagad_pipeline.benchmark
```

Aggregate-only results are written to the ignored
`pipeline/benchmark_results/three_angle_benchmark.json`. No frames, crops, or
per-person track records are saved.
