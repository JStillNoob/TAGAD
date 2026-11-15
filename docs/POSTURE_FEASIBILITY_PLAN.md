# A5 Upper-Body Posture Feasibility

Prepared November 5, 2026. Evaluation design is ready. Model execution,
classroom measurements, and feasibility approval await the scheduled test.

## Candidate and evaluation boundary

Start with `yolo11n-pose.pt` at a 640-pixel inference size, batch size 1, on
the pilot laptop. Record its checksum, Ultralytics/PyTorch versions, device,
precision, and input settings before evaluation. This is a candidate selection
subject to the measurements below. YOLO11 provides dedicated pose models.
[Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/)

Run the candidate on full camera frames or calibrated student-area images
that include the body. Preserve the coordinate transform when cropping or
resizing. TAGAD's custom head detector supplies head crops to MediaPipe, so a
pose path needs access to the original frame.

Evaluate posture alongside the current facial pipeline, then use A6 to assess
whether combining their evidence improves human-reviewed classifications.
Use the approved A3 samples and A4 camera/zone references described in the
[ground-truth protocol](CLASSROOM_GROUND_TRUTH_PROTOCOL.md) and
[calibration plan](CAMERA_CALIBRATION_PLAN.md).

## Keypoint contract

The COCO pose schema supplies the following zero-based indices. Measure
left and right joints separately, including both-side coverage. The model
also supplies person boxes. The results API exposes coordinates through `xy`
and per-joint confidence through `conf` when available.
[COCO keypoint schema](https://docs.ultralytics.com/datasets/pose/coco/)
[Results API](https://docs.ultralytics.com/reference/engine/results/)

| Joint group | Left index | Right index | Planned use |
| --- | --- | --- | --- |
| Shoulders | 5 | 6 | Shoulder-line angle, scale, upper-body stability |
| Elbows | 7 | 8 | Arm configuration and elbow angles |
| Wrists | 9 | 10 | Hand-region movement relative to the body |
| Hips | 11 | 12 | Shoulder-to-hip axis and projected torso lean |

## Association and missing evidence

- Match the current head candidate to a person box within the same frame and
  calibrated student zone. Require a unique, spatially consistent pairing.
- Record unmatched and ambiguous pairs separately. Exclude ambiguous pairs
  from combined features while retaining the valid facial evidence.
- Use a proposed initial joint-confidence cutoff of 0.50. Also require finite,
  in-frame coordinates and a valid body scale for the requested feature.
- Require every joint used in a feature to pass its validity checks. Represent
  an unavailable feature as missing with a reason and a validity mask.
- Record occlusion, absent confidence, unmatched person, ambiguous match,
  insufficient history, and invalid scale as separate aggregate reasons.
- Retain unavailable posture as `Unclassified` within posture diagnostics.
  Evaluate how it should combine with facial evidence in A6.

Confidence is a model score. Human review must establish whether predicted
joints correspond to the visible student, including when an occluded joint
receives a high score.

## Proposed temporal features

Use a rolling five-second window for each temporary, camera-local track.
Initially require at least eight valid samples spanning three seconds, with
no gap over one second between consecutive valid samples. Expiration,
ambiguous association, or a large gap invalidates the corresponding window.
Record readiness and missing-feature counts alongside measured values.

Use pixel coordinates for angles and distances, then normalize distances by
the visible shoulder width or valid torso length. Keep left/right body scale
and perspective limitations visible in the evaluation.

| Feature | Required evidence | Interpretation to evaluate |
| --- | --- | --- |
| Shoulder-line angle | Both shoulders | Projected shoulder tilt relative to the calibrated image axes |
| Projected torso orientation/lean | Both shoulders and both hips | Angle of the shoulder-midpoint to hip-midpoint axis |
| Arm configuration | Shoulder, elbow, and wrist on the same side | Elbow angle and wrist position relative to the shoulder |
| Arm movement | Valid same-side arm samples over time | Body-normalized wrist displacement divided by elapsed time |
| Posture stability | Valid shoulder or torso features over time | Temporal spread of angles and normalized positions |

Projected angles depend on the camera view. Compare them with the A4 lesson
targets and manual behavior labels before using them for lesson-facing
estimation. Neutral poses, reading, writing, and following a moving teacher
need separate examples in the review set.

## Proposed engineering acceptance targets

These are starting thresholds selected during preparation, pending agreement
before the first evaluation. Record an accepted revision and date before
viewing candidate results. Future revisions require a fresh held-out review.

| Gate | Proposed target |
| --- | --- |
| Joint cutoff | 0.50, with coordinate and association checks |
| Window readiness | Eight valid samples spanning at least three seconds in a five-second window, maximum one-second gap |
| Feature availability | At least 70% of assigned student windows usable for each feature on each camera intended to supply it |
| Reviewed association correctness | At least 95% of reviewed accepted head/body pairings agree with the visible correspondence |
| Reviewed joint usability | At least 90% of reviewed accepted feature observations have their required joints on the correct visible body parts |
| Three-camera processing rate | At least 2.5 completed analyses per second for every camera over the measured run |
| End-to-end processing latency | P95 at most 1,000 ms per camera including inference-lock wait and posture work |
| Device-memory headroom | Peak total GPU usage at most 80% of device capacity under the recorded workload |
| Stability | Zero worker crashes or out-of-memory errors during an approved continuous class-period run |

Measure all four joint groups even when some features fail the availability
target. State which features and camera views qualify, and leave unsupported
features unavailable. Reviewers must include difficult and occluded cases in
the usability check to expose confident but incorrect predictions.

The 2.5 Hz target follows the existing example controller configuration.
Earlier CUDA results used looped short clips with roughly four to five
confirmed students per view. Classroom-scale performance requires new
measurements at the representative student count.

## Scheduled evaluation procedure

1. Confirm approved samples, camera calibration references, accepted target
   revision, and the anonymous number of visible students per camera.
2. Select representative front/middle/back seating windows and activity
   contexts before inspecting pose output. Record sample counts per view.
3. Run the existing facial pipeline as baseline, then the same workload with
   the pose candidate. Keep device, input size, sampling, and precision fixed.
4. Warm up each run and record model-loading and warm-up time separately.
5. Use source timestamps for posture temporal features on recorded footage.
   Measure performance with wall-clock time. Record playback speed and dropped
   frames so accelerated replay can be interpreted correctly.
6. Review joint visibility, confidence distribution, pairing correctness,
   feature readiness, and unavailable-feature reasons per camera.
7. Measure pose-only latency plus full pipeline latency and completed analyses
   per wall-clock second. Record mean, P95, maximum, and sample count.
8. For isolated CUDA timing, synchronize the device around the timed region.
   Measure actual concurrent throughput separately to account for scheduling
   and lock contention. [PyTorch CUDA synchronization](https://docs.pytorch.org/docs/2.14/generated/torch.cuda.synchronize.html)
9. Measure GPU allocated/reserved peaks, total device usage, process RAM,
   dropped frames, and worker failures for baseline and candidate runs.
10. Compare against the frozen targets and record Pass, Fail, or Insufficient
    evidence for each camera/feature. Use A6 for subsequent classification
    fusion and A7 for accuracy evaluation.

The separate evaluator is `pipeline/tagad_pipeline/posture_benchmark.py`.
It uses the existing facial pipeline and shared inference lock, then adds
head/body association, joint confidence and usability counts, rolling features,
latency, process RAM, and CUDA memory measurements. Its calculations use decoded
presentation timestamps relative to each recording's first frame. Source-time
sampling and temporal windows preserve variable frame intervals. Video duration
comes from media timestamps. Missing or repeated frame timestamps and truncated
input produce failed evaluation results. Manual camera alignment remains part
of the approved private workflow.
Recorder-corrected duplicate timestamps remain estimates. Each evaluator input
includes correction counters and the matching manifest hash when an adjacent
recording manifest is available. Review those corrections before annotating or
comparing recordings; timing replay does not validate engagement accuracy.

## Offline command for the scheduled evaluation

Prepare a separate configuration with existing local video files marked
`simulated`, using the structure in `pipeline/camera_sources.example.json`.
Use one file for each Front, Left, and Right position and the same files for
both modes. The evaluator consumes the common initial duration once, ignoring
the configuration's loop setting. It requires at least five seconds per file.

Run these commands from the repository root at the scheduled evaluation.
Choose fresh output names for each comparison.

```powershell
$env:PYTHONPATH = "$PWD\pipeline"
pipeline\.venv\Scripts\python.exe -m tagad_pipeline.posture_benchmark --config pipeline/camera_sources.example.json --mode baseline --output pipeline/benchmark_results/posture_baseline_a5_01.json
pipeline\.venv\Scripts\python.exe -m tagad_pipeline.posture_benchmark --config pipeline/camera_sources.example.json --mode pose --pose-model backend/model_artifacts/yolo11n-pose.pt --output pipeline/benchmark_results/posture_candidate_a5_01.json
```

The pose checkpoint must already exist locally and be obtained from the
approved source. Checkpoint task validation requires a pose model. Provide
`--target-revision` after the targets are agreed. Defaults are 60 source seconds,
2.5 sampled analyses per source second, and a 0.50 joint-confidence cutoff.
Use `--source-seconds` for the approved class-period duration.

Each report includes model/input checksums, configuration, per-camera results,
and a measured common wall-clock overlap duration. Read failure produces a
failed camera result and a nonzero exit status. Partial runs retain their
failure status for review. Existing output files are protected from overwrite.

These runs process recordings as fast as available hardware permits. Different
completion times can reduce contention near the end. Inspect overlap duration
and use a representative continuous workload when assessing live performance.
Warm-up and model loading are reported separately. Total device-memory peaks
are sampled, while PyTorch allocator peaks come from its memory counters.

The automatic denominator is head-candidate observations. Manual student
visibility, actual occlusion, pairing correctness, A4 zone validation, and
feasibility approval still require the independent review procedure. Feature
statistics describe overlapping rolling windows. The report retains the
unverified feasibility state until reviewed evidence exists.

## GPU measurement record

Reset peak statistics after warm-up for each separately measured mode. Record
`max_memory_allocated` and `max_memory_reserved`, plus total device-memory usage
and capacity from the device monitor. Shared-model measurements describe the
whole process. Record them once per mode alongside per-camera timing results.
[PyTorch allocated memory](https://docs.pytorch.org/docs/2.14/generated/torch.cuda.memory.max_memory_allocated.html)
[PyTorch reserved memory](https://docs.pytorch.org/docs/2.14/generated/torch.cuda.memory.max_memory_reserved.html)

## Blank private evaluation record

Copy the tables to approved private storage before entering sample references.
Record model checksum, target revision, software versions, device, total GPU
capacity, sampling rate, image geometry, workload duration, and raw counts
with each run. Keep frames, crops, keypoints, and temporary tracks within the
approved private workflow. Publish aggregate evidence only.

| Camera | Mode | Reviewed student windows | Shoulder L/R/both usable | Elbow L/R/both usable | Wrist L/R/both usable | Hip L/R/both usable | Unmatched/ambiguous pairs | Ready feature windows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Front | Baseline / with pose | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Left | Baseline / with pose | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Right | Baseline / with pose | Pending | Pending | Pending | Pending | Pending | Pending | Pending |

| Camera and joint/feature | Score samples | Mean/P10 confidence | Usable observations / assigned observations | Reviewer-correct / reviewed accepted observations | Readiness or rejection reason |
| --- | --- | --- | --- | --- | --- |
| Pending | Pending | Pending | Pending | Pending | Pending |

Summarize confidence for all returned joints as well as the accepted subset.
Record association correctness separately from joint correctness.

| Camera | Completed analyses | Duration | Analyses/s | Mean/P95/max latency | Dropped frames | Failures | Target result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Front | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Left | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Right | Pending | Pending | Pending | Pending | Pending | Pending | Pending |

| Shared process mode | Allocated peak | Reserved peak | Total device peak/capacity | Process RAM peak | Run duration | Result |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline | Pending | Pending | Pending | Pending | Pending | Pending |
| With pose | Pending | Pending | Pending | Pending | Pending | Pending |

For each visibility and usability rate, retain numerator, denominator, and
reviewer-agreement information. Use unavailable when the denominator is zero.
Completion requires the measured records and an explicit feasibility decision
for the actual camera views and target laptop.
