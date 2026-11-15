# Engaged and Attentive prediction audit

November 9, 2026. Prioritize prediction work before the boundary editor.

## Findings

The current facial state model must first predict raw Engaged for either final
Engaged or Attentive to appear. LowerAttention refines raw Engaged into Attentive.
That matches the frozen training handoff and current contract. It does not yet
implement all active/passive behaviors in the human label guide.

The saved setup diagnostics show that the attention model can produce both
outputs. Session 49 contains 437 raw-state observations, only two raw Engaged
observations, and 373 LowerAttention observations. These are repeated camera
observations, not student totals or paired accuracy evidence. Marginal counts
cannot establish which raw states coincided with the attention outputs.

Session 44, the classroom baseline, has 1,821 summaries without stage diagnostics
and no corresponding recordings. Session 50 was confirmed by the user to be a
setup test. Neither establishes the cause of classroom errors or the accuracy
of a replacement model.

The attention readiness contract requires 15 valid facial observations within
ten seconds, spanning at least seven seconds. At one or 1.25 valid observations
per second, it cannot become ready. A synthetic stable track at 2.5 valid
observations per second becomes ready at 7.2 seconds. Occlusion and tracking
resets can still prevent readiness.

## Implemented correction

Both live entry points previously skipped a fixed number of frames using the
advertised stream FPS. The current configuration requests 2.5 analyses/second.
Session-50 media delivered approximately 10 FPS for Front/Right and 16.67 FPS for
Left, versus nominal rates of 15 and 25. Fixed steps of six and ten therefore
limit ideal analysis to approximately 1.67 Hz before inference costs.

`controller.py` and the standalone `worker.py` now schedule live analysis using
monotonic elapsed time. They process the first eligible frame immediately and
schedule the next opportunity from that frame's time, without catch-up bursts.
Simulated/recorded frame-step callers keep their existing behavior. The recorder,
classifier artifacts, final label mapping, readiness thresholds, API contracts,
and session lifecycle were not modified by this correction.

## Verification

- Regression tests failed before the change, demonstrating controller counts of
  17 and 11 analyses over a ten-second 10-FPS source advertising 15 and 25 FPS.
  The fixed controller produced the requested 25 analyses in both cases.
- Coverage includes absent/invalid nominal FPS for live controller input, slow
  processing without catch-up bursts, standalone live scheduling, unchanged
  recorded/simulated sampling, and the attention readiness contract.
- `cd pipeline; .\.venv\Scripts\python.exe -m unittest discover -s tests`
  passed all 80 checks.
- Thirty seconds from each session-50 recording were decoded through the normal
  controller with a source-timeline clock and stubbed inference. Each view
  produced 74 analyses, approximately 2.47 Hz, with source-frame quantization and
  no intervals below the requested 0.4 seconds. Hashes confirmed unchanged media.
- The ignored local replay report is `tmp/engagement-live-sampling-replay.json`.
  This replay is not a measurement of real-time GPU throughput or prediction
  accuracy. It opened no network cameras and submitted no backend results.

## Next prediction work

The raw Engaged scarcity remains a model/domain investigation, not a solved
accuracy issue. Compare known behavior examples with extracted facial evidence,
then evaluate the A5 posture candidate and develop A6 only against independently
reviewed examples. Pose weights are not currently present in the deployed model
artifact directory. Do not alter class shares, invert attention labels, weaken
readiness, or claim gains merely because Engaged/Attentive counts increase.

The Wednesday, November 11 classroom test should capture representative behavior,
camera-view references, stage diagnostics, and reviewer labels. A1 classroom
validation, A3 labeled collection, A5 measured feasibility, A6 fusion, and A7
accuracy validation remain open. Body posture is still offline-only.
