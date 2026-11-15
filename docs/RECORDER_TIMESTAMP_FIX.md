# Recorder duplicate-timestamp correction

Completed November 9, 2026. Long classroom recording and engagement accuracy
remain separate acceptance work.

## Cause

Session 49 recorded Front and Left continuously, but Right produced ten one-frame
parts. Direct RTSP inspection confirmed repeated decode and presentation times
from Right, including the keyframe and its following frame. The recorder treated
equal times as a clock discontinuity and reconnected into the same pattern.
The live analytics controller uses its local clock and has a separate lifecycle.

## Change and limits

- Buffer one timestamp group, preserving compressed video packets without
  re-encoding or dropping frames from accepted groups.
- For a stream without frame reordering, distribute up to eight duplicate-time
  packets between the group's first timestamp and the next valid timestamp.
  Source times outside that group remain unchanged.
- Reject backwards decode times, unsupported reordered duplicates, groups above
  the packet limit, and correction spans above one second or below clock resolution.
- At normal stop or EOF, a trailing duplicate group uses the previous observed
  spacing. If no interval exists, use nominal FPS. These tail estimates are
  separately counted and remain subject to the same correction bounds.
- Manifest fields disclose corrected packets, tail estimates, maximum adjustment,
  and whether timing review is required. Offline report inputs include these
  counters and the source manifest hash. Older manifests default missing counters
  to zero; input videos without manifests have null recording-timing metadata.
- Genuine stream interruptions still produce partial recordings and separate
  numbered parts. Session start/stop behavior, camera settings, and live analytics
  code are unchanged.

Correction recovers usable ordering, not the original acquisition time. A 100 ms
correction is an estimate. Review camera alignment and these estimates before
human annotation, temporal comparisons, or accuracy claims.

## Verification

- Reproduced the former failure before applying the fix using generated H.264
  packets with repeated times after keyframes, at the beginning, and at the tail.
- Corrected fixtures preserve every encoded packet byte and decode to all 90
  original frames with increasing presentation times and bounded duration error.
- Checks cover EOF and teacher stop, unsupported reordered timing, excessive
  repeats, wide gaps, insufficient clock resolution, backwards times, metadata
  propagation/validation, recording interruptions, and existing lifecycle callers.
- `cd pipeline; .\.venv\Scripts\python.exe -m unittest discover -s tests`
  passed all 75 tests.
- A manual 30-second capture through the normal shared recorder used the three
  real cameras while TAGAD was idle. Private folder
  `C:\TAGAD_PRIVATE_PILOT\PILOT-20261109T010708Z-bbea8f1d` contains one completed
  MP4 per camera and `offline-sources.json`. RTSP startup and keyframe wait leave
  about 26.9 seconds of stored video.

| Camera | Decoded frames | Media duration | Corrected packets | Largest adjustment |
| --- | ---: | ---: | ---: | ---: |
| Front | 269 | 26.867 s | 0 | 0 |
| Left | 448 | 26.890 s | 0 | 0 |
| Right | 269 | 26.867 s | 9 | 0.100 s |

All three decode completely with increasing presentation times, no audio, and
decoded frame counts matching muxed packet counts. Right has no reconnection
parts or tail estimates. The manifest correctly requires timing review.

The normal offline evaluator read the entire common 26.867 seconds, sampling 68
frames per camera. Models were stubbed to isolate timing; no predictions or
accuracy measurements were produced. The ignored local timing report is
`tmp/duplicate-timestamp-live-timing-only.json`.

SHA-256 comparisons confirmed that all 21 pre-existing private recording files
and manifests remained unchanged. Missing Right footage from session 49 cannot
be recovered. The live rehearsal covers a short capture, not an hour-long class.

## Follow-up automatic session

The user completed session 50 on November 9, 2026, from 09:12:29 to 09:18:06
local time and chose Finish Lesson. The automatic recorder followed that meeting
and closed all three files. Its manifest is completed, with one part per camera,
no camera errors, and offline inputs ready. Files remain private under
`C:\TAGAD_PRIVATE_PILOT\PILOT-20261109T011230Z-c02b6794`.

| Camera | Decoded frames | Media duration | Corrected packets |
| --- | ---: | ---: | ---: |
| Front | 3,351 | 335.017 s | 0 |
| Left | 5,585 | 335.040 s | 0 |
| Right | 3,350 | 334.967 s | 115 |

Every muxed frame decoded, with increasing presentation times, no missing frame
timestamps, and no audio. Right needed no recording reconnects or tail estimates;
its largest timestamp adjustment remained 100 ms. Timing review remains required.
The approximately two-second difference from meeting duration is consistent with
initial RTSP/keyframe wait and the recorder's end polling.

Timing-only evaluation passed the full common 334.967 seconds, sampling 838 frames
per camera. The correction counts and manifest hash propagated to the report.
Models were stubbed, and SHA-256 checks confirmed all files in this recording
folder remained unchanged. The ignored report is
`tmp/session-50-recording-timing-c0dd767ad3b0496593c2c5ba93a3873b.json`.
This verifies an automatic five-minute meeting. Hour-long recording endurance
and engagement accuracy remain unverified.
