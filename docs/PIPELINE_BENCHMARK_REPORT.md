# TAGAD Three-Angle and CUDA Stability Benchmark

CPU benchmark date: September 22, 2026  
CUDA stability date: September 24, 2026  
Pipeline: `hierarchical-1`  
Device: CPU  
Requested sampling rate: 8 analyses/second

## Scope

The three supplied portrait videos were processed independently using one model
load and identical settings. Counts were not combined because the clips have
different durations and may contain overlapping views of the same students.
No frames, face crops, or track identities were saved.

## Source summary

| Camera position | Local file | Resolution | FPS | Duration | Analyzed frames |
| --- | --- | ---: | ---: | ---: | ---: |
| Center | `cneter.mp4` | 368×652 | 30 | 15.70 s | 117 |
| Left | `left.mp4` | 368×652 | 30 | 8.67 s | 65 |
| Right | `right'.mp4` | 576×1024 | 30 | 7.70 s | 57 |

The clips are not treated as synchronized because their durations differ.

## Results

| Metric | Center | Left | Right |
| --- | ---: | ---: | ---: |
| Sampled source rate | 7.45/s | 7.50/s | 7.40/s |
| Processing throughput | 7.83/s | 12.75/s | 8.34/s |
| Mean processing time | 126.35 ms | 77.11 ms | 116.53 ms |
| P95 processing time | 136.56 ms | 95.38 ms | 136.13 ms |
| Mean head candidates | 5.02 | 5.00 | 5.95 |
| Mean valid faces | 3.89 | 2.03 | 2.44 |
| Mean confirmed students | 4.61 | 2.32 | 3.12 |
| Valid-face coverage | 77.51% | 40.62% | 41.00% |
| Classification coverage | 77.18% | 70.20% | 61.80% |
| Mean classification confidence | 74.08% | 65.99% | 80.01% |

The first inference for the Center video took 2.28 seconds while the models warmed up.
Repeated default runs varied with local CPU load: Center processed 7.83–9.36
analyses/second, Left 12.68–12.75, and Right 8.34–10.80. Every view remained
fast enough for its actual 7.4–7.5 sampled frames/second.

## Findings

- The Center camera provides the strongest face and classification coverage.
- The Left and Right cameras lose facial landmarks for roughly 59% of head candidates,
  so camera placement, distance, lighting, or head orientation needs review.
- Center classification coverage dropped after 10 seconds when valid-face
  readings fell, demonstrating why failed landmark extraction must remain
  Unclassified instead of being changed to Disengaged.
- The CPU processed the clips faster than the requested sampling rate after
  model warm-up.
- The observed states were Bored, Confused, and Disengaged. Engaged and
  Attentive did not appear in these short clips. A visual ground-truth review is
  required before interpreting this as model accuracy.
- Memory increased during the first model inference and remained approximately
  stable during the following two clips. The recordings are too short to prove
  full-session memory stability.

## Visual condition review

Representative frames were inspected locally and then discarded. This review
records observable image conditions only; it does not assign emotions or claim
ground-truth engagement labels.

| Camera and time | Observable conditions |
| --- | --- |
| Center, 2 s | Five visible students; mostly frontal view; several heads tilted down |
| Center, 7 s | Five visible students; frontal faces remain clearest of the three views |
| Center, 12 s | Camera motion introduces substantial blur and softer facial detail |
| Left, 2 s and 6 s | Students are smaller and viewed obliquely; several faces point downward |
| Right, 2 s and 6 s | Side profiles, downward gaze, foreground occlusion, and one standing student |

These conditions explain why YOLO continues to find heads while MediaPipe cannot
produce valid facial landmarks for every candidate.

## YOLO confidence comparison

The clips were benchmarked at confidence thresholds 0.25, 0.40, and 0.60.

| Camera | Result of lowering confidence from 0.60 to 0.25 |
| --- | --- |
| Center | Mean candidates increased 5.02→5.18; classification coverage changed 77.18%→77.12% |
| Left | Candidate, valid-face, and classification measurements did not change |
| Right | Mean candidates increased 5.95→6.16; valid faces and classifications did not increase |

The integrated default remains `0.60`. Lower thresholds add candidate noise but
do not solve the side-camera landmark failures.

## Decision

The single-camera software baseline passes the short-video performance smoke
test. It does not yet pass accuracy validation, full-session stability, or
multi-camera aggregation.

## Concurrent offline orchestration smoke test

The three recordings were then looped concurrently for 20 seconds with one
shared model bundle and three independent camera pipelines. The CPU-safe target
was reduced from the single-camera 8 Hz setting to 2.5 Hz per source after an
initial 8 Hz run demonstrated that the current CPU can sustain only about 8.3
analyses/second in total.

| Metric | Front | Left | Right |
| --- | ---: | ---: | ---: |
| Analyzed frames | 55 | 55 | 54 |
| Achieved throughput | 2.727/s | 2.712/s | 2.696/s |
| Mean processing latency | 362.38 ms | 364.15 ms | 359.02 ms |
| P95 processing latency | 366.70 ms | 370.93 ms | 360.75 ms |

Loading the shared models added about 118.42 MB of process RSS. Process RSS
peaked near 723.87 MB and ended near 521.82 MB. All three sources completed and
none starved. Results remained separate and `combined_student_count` was
deliberately recorded as `null`. These measurements validate the short CPU
load test; the longer simulated CUDA stability result is recorded below.

## CUDA validation and 60-minute simulated stability

On September 24, 2026, the same three recordings were looped concurrently for
60 minutes using PyTorch 2.14.0 with CUDA 12.6 on the laptop's NVIDIA GeForce
RTX 4050 GPU. The original recordings were not modified. The shared model
bundle and three independent camera pipelines remained unchanged, and combined
student counts remained disabled.

| Metric | Front | Left | Right |
| --- | ---: | ---: | ---: |
| Analyzed frames | 12,593 | 12,593 | 12,593 |
| Compute throughput | 3.498/s | 3.498/s | 3.498/s |
| Mean processing latency | 281.88 ms | 281.81 ms | 274.77 ms |
| P95 processing latency | 405.91 ms | 406.63 ms | 398.04 ms |
| Final status | Completed | Completed | Completed |

The run completed 37,779 analyses without a camera failure or source starvation.
Process RSS peaked at 1,667.34 MB and ended at 774.97 MB; intermediate checks
from five through twenty-three minutes remained near 1.65–1.67 GB rather than
growing continuously. Mean process CPU use was 121.18%, substantially below the
842.92% measured by the earlier CPU-only 20-second run. Observed GPU memory was
approximately 422–656 MiB and temperature remained between 47–52°C during
manual checkpoints. GPU memory returned to 267 MiB after shutdown.

This passes the 60-minute simulated stability gate for the current computer.
It does not validate classroom accuracy: the source material is still three
short repeated clips, so human ground truth and a representative continuous
classroom recording remain separate requirements.

## Next validation

- [x] Map the three recordings to Center, Left, and Right camera positions.
- [x] Review representative image conditions without retaining face crops.
- [ ] Have a human annotator record expected states by timestamp; image posture
      alone is not reliable emotional ground truth.
- [ ] Obtain a representative 10–30 minute or full-class recording.
- [x] Repeat the benchmark for 60 minutes to test sustained simulated-camera
      memory and processing stability.
- [ ] Validate one live RTSP stream before attempting combined camera counts.

Use [`PIPELINE_GROUND_TRUTH_REVIEW.md`](PIPELINE_GROUND_TRUTH_REVIEW.md) for the
human-labeling step.
