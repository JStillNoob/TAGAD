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
to the three recordings. Positions must be `front`, `left`, and `right` and
must match the camera records assigned to the active classroom session.

Run Django, start a classroom session in the browser, then open a separate
PowerShell window at the repository root:

```powershell
$env:TAGAD_PIPELINE_API_KEY = "replace-with-the-same-private-value"
$env:PYTHONPATH = "$PWD\pipeline"
pipeline\.venv\Scripts\python.exe -m tagad_pipeline.controller
```

The controller discovers active work every two seconds, follows slide changes,
loops simulated files, and stops workers after the teacher ends the session.
The Live Session page displays Starting, Online, Reconnecting, Offline, or
Stopped for each source. To exercise recovery, add these optional fields to one
camera in the ignored local file:

```json
"simulate_disconnect_after_frames": 30,
"simulate_disconnect_seconds": 2
```

The Front source alone submits official summaries. Left and Right counts stay
source-specific diagnostics; they are never added together.

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

## Three-angle benchmark

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
