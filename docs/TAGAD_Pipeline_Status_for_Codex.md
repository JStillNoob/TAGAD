# TAGAD Pipeline Status for Codex

## Project location

```text
D:\TAGAD
```

## Current status

The core TAGAD AI prototype is **working**, but the full classroom deployment pipeline is **not production-ready yet**.

Working now:

```text
YOLO head detection                     DONE
MediaPipe feature extraction            DONE
Main state SVM                          DONE
Temporal attention SVM                  DONE
Single-person webcam inference          DONE
Multi-person webcam inference           DONE
Recorded classroom video inference      DONE
Temporary per-person tracking           DONE
Per-track temporal attention history    DONE
Final five TAGAD display states         DONE
```

Still needed:

```text
Confirmed-track filtering               TODO
Explicit Unclassified handling          TODO
False-positive rejection cleanup        TODO
CUDA / RTX 4050 verification            TODO
Real classroom pilot validation         TODO
End-to-end five-state accuracy          TODO
RTSP/IP CCTV input                      TODO
Three-camera integration                TODO
Cross-camera duplicate handling         TODO
Backend/API integration                 TODO
SignalR/dashboard integration           TODO
Database/session aggregation            TODO
```

---

# 1. Active models

Use these files:

```text
D:\TAGAD\models\tagad_yolo11_head_v2_best.pt
D:\TAGAD\models\face_landmarker.task
D:\TAGAD\models\dipser_attention_10-feature_diagnostic.joblib
D:\TAGAD\models\tagad_state_svm_rich_threshold1_candidate.joblib
```

Do not use archived/older experimental models unless specifically comparing results.

---

# 2. Current inference architecture

```text
Camera / MP4 / future RTSP CCTV
        |
        v
YOLOv11 Head Detector
        |
        v
Temporary Person Tracking
        |
        v
MediaPipe Face Landmarker
        |
        +------------------------------+
        |                              |
        v                              v
Head/Gaze Geometry               Facial Blendshapes
        |                              |
        +--------------+---------------+
                       |
                       v
                Rich State SVM
                       |
                       v
 Engaged / Confused / Bored / LookingAway / Drowsy
                       |
          +------------+-------------+
          |                          |
          v                          v
 DIPSER Attention SVM          Direct mapping
 for Engaged cases             LookingAway -> Disengaged
          |                    Drowsy -> Disengaged
 HigherAttention /
 LowerAttention
          |
 HigherAttention -> Engaged
 LowerAttention  -> Attentive
          |
          v
Final TAGAD display state:
Engaged / Attentive / Confused / Bored / Disengaged
```

Important: the current implementation is **hierarchical**. It uses two SVMs for different jobs.

---

# 3. YOLOv11 head detector

Training dataset:

```text
SCUT-HEAD Part A + Part B
Train:       2543
Validation:   862
Test:        1000
Total:       4405
```

Base model:

```text
yolo11n.pt
```

Training length:

```text
50 epochs
```

Final test metrics:

```text
Precision:   91.05%
Recall:      87.32%
mAP@50:      91.98%
mAP@50-95:   45.91%
```

Selected model:

```text
D:\TAGAD\models\tagad_yolo11_head_v2_best.pt
```

Known issue: YOLO can occasionally produce false positives. During a live multi-person webcam test, a raised hand was detected as a possible head.

Recommended logic:

```text
YOLO candidate
    |
    v
MediaPipe valid face?
    |
 YES -> continue
 NO  -> reject / Unclassified
```

Do not equate raw YOLO detections with confirmed students.

Current/previous YOLO confidence was around `0.50`. For practical testing, `0.60` is a reasonable next threshold to evaluate, but do not make it so high that distant real students are lost.

---

# 4. MediaPipe feature extraction

Model:

```text
D:\TAGAD\models\face_landmarker.task
```

MediaPipe was not trained by this project.

Geometry features:

```text
pitch
yaw
roll
Gh
Gv
```

Temporal attention also uses:

```text
mean_pitch
mean_yaw
mean_roll
mean_Gh
mean_Gv
std_pitch
std_yaw
std_roll
std_Gh
std_Gv
```

The rich state model uses the 5 geometry features plus 20 MediaPipe blendshapes, for 25 total features.

Blendshapes:

```text
eyeBlinkLeft
eyeBlinkRight
eyeSquintLeft
eyeSquintRight
eyeWideLeft
eyeWideRight
browDownLeft
browDownRight
browInnerUp
browOuterUpLeft
browOuterUpRight
cheekSquintLeft
cheekSquintRight
jawOpen
mouthFrownLeft
mouthFrownRight
mouthSmileLeft
mouthSmileRight
mouthPressLeft
mouthPressRight
```

---

# 5. DAiSEE experiment

DAiSEE was initially used to try a direct five-state SVM based on five geometry features.

Clean rows:

```text
Train:       5199
Validation:  1345
Test:        1746
```

Baseline result:

```text
Validation Accuracy: 24.39%
Macro F1:            21.09%
```

This was rejected as too weak.

Reason: DAiSEE does not naturally provide the exact five TAGAD states, so the five-state labels had to be derived. Geometry alone also did not separate states such as Engaged vs Attentive and Confused vs Bored well enough.

Do not use the DAiSEE five-state model as the final classifier.

---

# 6. DIPSER temporal attention SVM

DIPSER was used for temporal attention refinement.

Processed scope:

```text
20 subjects
579 windows
```

Selected features:

```text
mean_pitch
mean_yaw
mean_roll
mean_Gh
mean_Gv
std_pitch
std_yaw
std_roll
std_Gh
std_Gv
```

Selected result:

```text
Accuracy: approximately 77.55%
Macro F1: approximately 66.04%
```

Output classes:

```text
HigherAttention
LowerAttention
```

Selected model:

```text
D:\TAGAD\models\dipser_attention_10-feature_diagnostic.joblib
```

Current temporal logic:

```text
history kept: about 10 seconds
minimum useful span: about 7 seconds
minimum samples: about 15
```

This model is not a five-state classifier. It is only used to refine an Engaged prediction into Engaged vs Attentive.

---

# 7. Main rich state SVM

Dataset: Student Concentration / Student Engagement image dataset.

Usable rows:

```text
1624
```

Source-state counts:

```text
Engaged:       347
Confused:      369
Bored:         331
LookingAway:   359
Drowsy:        218
```

`frustrated` was excluded.

An initial random split gave:

```text
Accuracy: 94.67%
Macro F1: 94.53%
```

That result was rejected because duplicate leakage was found.

The dataset had extensive exact/near-duplicate frames. A pHash grouping audit was performed.

Final grouped evaluation used:

```text
pHash Hamming threshold <= 1
StratifiedGroupKFold
zero group overlap
```

Geometry-only SVM:

```text
Accuracy: 89.53%
Macro F1: 89.41%
```

Rich 25-feature SVM:

```text
Accuracy: 95.50%
Macro F1: 95.12%
```

Per-class F1:

```text
Engaged:      98.29%
Confused:     96.39%
Bored:        90.51%
LookingAway:  98.90%
Drowsy:       91.50%
```

Selected model:

```text
D:\TAGAD\models\tagad_state_svm_rich_threshold1_candidate.joblib
```

Correct wording for the result:

> 95.50% accuracy and 95.12% Macro F1 under near-duplicate-grouped cross-validation.

Do not call 95.50% the whole-system classroom accuracy.

---

# 8. Final state mapping

Main state SVM output:

```text
Engaged
Confused
Bored
LookingAway
Drowsy
```

Mapping:

```text
Confused    -> Confused
Bored       -> Bored
LookingAway -> Disengaged
Drowsy      -> Disengaged
```

Engaged refinement:

```text
Engaged + HigherAttention -> Engaged
Engaged + LowerAttention  -> Attentive
```

Final TAGAD display states:

```text
Engaged
Attentive
Confused
Bored
Disengaged
```

---

# 9. Existing scripts

Known working/test scripts:

```text
D:\TAGAD\tagad_live_combined_fixed.py
D:\TAGAD\tagad_multi_person_test.py
D:\TAGAD\tagad_classroom_tracking_test.py
D:\TAGAD\analyze_tagad_tracking_log.py
```

Purpose:

```text
tagad_live_combined_fixed.py
    single-person live webcam full pipeline

tagad_multi_person_test.py
    multi-head webcam detection/classification

tagad_classroom_tracking_test.py
    recorded classroom video
    temporary person tracking
    temporal attention history
    final TAGAD state

analyze_tagad_tracking_log.py
    analyzes tracking continuity and durations
```

Codex should inspect these scripts before rewriting the pipeline from scratch.

---

# 10. Multi-person webcam test

Multi-person detection works.

A real webcam test detected 5 candidate heads simultaneously and classified several visible students.

Known false-positive example:

```text
raised hand -> YOLO candidate -> MediaPipe could not validate face
```

Production UI/analytics should distinguish:

```text
YOLO candidates
valid MediaPipe faces
confirmed student tracks
```

---

# 11. Classroom video tests

First wide classroom video:

```text
Average YOLO heads/frame: 27.14
Maximum heads:            30
YOLO detections:          17,996
Successfully classified: 1,586
Success rate:             8.81%
```

The view was too wide and many faces were too small/angled.

Improved classroom video:

```text
1920x1080
25 FPS
approximately 25.4 seconds
```

Result:

```text
Processed analysis frames:        212
Average YOLO heads/frame:         7.13
Maximum heads:                    9
YOLO detections:                  1511
Successfully classified:          1118
MediaPipe/classification success: 73.99%
```

This proved that camera distance, angle, resolution, face size, lighting, and occlusion matter strongly.

---

# 12. Tracking test

Temporary geometric tracking works without face recognition.

Tracking result:

```text
Temporary Track IDs Created: 17
Logged Observations:          1511
Attention-SVM Warmed Obs.:    848
```

Long tracks:

```text
T1:  25.32 sec
T2:  25.32 sec
T3:  25.32 sec
T4:  25.32 sec
T6:  25.32 sec
T7:  25.32 sec
T5:  15.12 sec
T12: 10.92 sec
```

There were also short fragmented tracks lasting roughly 0.00-0.84 sec.

Next improvement:

```text
new detection
-> tentative track
-> survives ~1-2 sec
-> confirmed student
```

Only confirmed tracks should count in classroom analytics.

---

# 13. Unclassified handling needed

If YOLO sees a possible head but MediaPipe cannot produce valid facial landmarks/features, do not force an engagement state.

Use:

```text
Unclassified
```

This is especially important for false positives, severe occlusion, profiles, tiny distant faces, or poor lighting.

---

# 14. Current processing interval

Classroom tracking test used:

```text
PROCESS_EVERY_N_FRAMES = 3
```

At 25 FPS:

```text
approximately 8.3 analyses/sec
approximately one analysis every 0.12 sec
```

Recommended current target:

```text
Camera capture:       25-30 FPS
AI analysis:          ~5-10 times/sec/camera
State smoothing:      recent ~1 sec of predictions
Attention history:    ~10 sec rolling window
Dashboard refresh:    ~1/sec
Database summary:     every ~2-5 sec
```

Do not store every 0.12-second raw prediction in the database.

---

# 15. Hardware status

Development laptop:

```text
MSI Thin 15 B12VE
Intel Core i5-12450H
8 cores / 12 logical processors
NVIDIA GeForce RTX 4050 Laptop GPU
Intel UHD Graphics
Windows 11
```

Important: the RTX 4050 exists, but PyTorch CUDA support has not yet been confirmed in the TAGAD virtual environment.

Earlier scripts were showing CPU use.

Verify with:

```bat
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('CUDA version:', torch.version.cuda); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

If CUDA is available, YOLO should preferably run on the RTX 4050.

---

# 16. Readiness assessment

## AI prototype readiness

```text
READY
```

The core models and end-to-end prototype already work.

## Real classroom integrated pipeline

```text
PARTIALLY READY
```

Needs robustness work, real-pilot validation, and CCTV integration.

## Production/deployment readiness

```text
NOT READY YET
```

Main blockers:

```text
confirmed-track filtering
Unclassified handling
real classroom validation
true end-to-end accuracy measurement
RTSP CCTV
3-camera support
cross-camera duplicate handling
backend/dashboard/database integration
```

---

# 17. What Codex should implement next

Priority order:

```text
1. Inspect and preserve the existing working scripts.

2. Add confirmed-track filtering.
   - tentative track first
   - require ~1-2 sec survival
   - ignore short fragments

3. Add explicit Unclassified handling.
   - YOLO candidate + MediaPipe failure -> Unclassified/reject

4. Separate these counters:
   - YOLO candidates
   - valid faces
   - confirmed students

5. Preserve exact SVM feature names and feature order.

6. Verify CUDA.
   - if available, run YOLO on RTX 4050

7. Add state smoothing to prevent rapid label flicker.

8. Make processing rate configurable.
   - target ~5-10 analyses/sec/camera

9. Add RTSP/IP-camera input while preserving webcam and MP4 support.

10. After single-camera RTSP is stable, add camera 2 and camera 3.

11. Add structured output/API for backend/dashboard integration.
```

---

# 18. Rules Codex should not break

Do not:

```text
replace selected models without reason
use archived weak models as final models
count every raw YOLO box as a real student
use face recognition
assign permanent identity from tracking
force a state when MediaPipe fails
average 95.50% and 77.55% into a fake combined accuracy
claim 95.50% as the complete TAGAD classroom accuracy
write every raw frame prediction into the database
```

Temporary IDs should remain privacy-preserving and session-based.

---

# 19. Accuracy interpretation

Main state model:

```text
95.50% accuracy
95.12% Macro F1
```

This is near-duplicate-grouped cross-validation on the Student Engagement dataset.

Attention model:

```text
77.55% accuracy
66.04% Macro F1
```

This is HigherAttention vs LowerAttention using DIPSER temporal features.

There is currently **no valid single combined end-to-end five-state accuracy**.

That must be measured on one labeled classroom pilot with final ground-truth labels:

```text
Engaged
Attentive
Confused
Bored
Disengaged
```

---

# 20. Paper vs actual implementation

Original paper design was approximately:

```text
YOLO
-> MediaPipe
-> 5 geometry features
-> one five-state SVM
```

Actual implementation evolved into:

```text
YOLO
-> MediaPipe
-> 25-feature rich state SVM
-> 10-feature temporal attention SVM
-> hierarchical final-state mapping
```

If this remains the final implementation, the methodology section of the paper must be updated to match the actual pipeline.

---

# Bottom line

The core TAGAD AI pipeline is already functional and suitable for continuing system development.

The next phase should focus on:

```text
robustness
confirmed tracking
false-positive filtering
Unclassified handling
GPU acceleration
real classroom validation
RTSP CCTV
three-camera processing
backend/dashboard integration
```

Treat the current models as mostly frozen until a real classroom pilot gives a clear reason to retrain them.
