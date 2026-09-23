# TAGAD Model Training & Implementation Summary

## 1. Project Goal

TAGAD is a classroom engagement monitoring system that uses:

- **YOLOv11** for student head detection
- **MediaPipe Face Landmarker** for head pose, eye gaze, and facial blendshape features
- **Support Vector Machine (SVM)** models for engagement-related classification
- Temporary tracking IDs for multi-person classroom video processing

The intended final TAGAD output states are:

1. **Engaged**
2. **Attentive**
3. **Confused**
4. **Bored**
5. **Disengaged**

---

## 2. Current Active Model Files

Main working directory:

```text
D:\TAGAD\
```

Active model files:

```text
D:\TAGAD\models\
├── tagad_yolo11_head_v2_best.pt
├── face_landmarker.task
├── dipser_attention_10-feature_diagnostic.joblib
└── tagad_state_svm_rich_threshold1_candidate.joblib
```

Older experimental models were moved to an archive folder and should not be used for final deployment.

---

## 3. YOLOv11 Head Detector Training

### Dataset

YOLOv11 was fine-tuned using **SCUT-HEAD Part A + Part B**.

Final merged dataset:

```text
Train: 2543 images
Validation: 862 images
Test: 1000 images
Total: 4405 images
```

### Training setup

Base model:

```text
yolo11n.pt
```

Training configuration:

```python
model_v2 = YOLO("yolo11n.pt")

results_v2 = model_v2.train(
    data="/content/tagad_head_v2.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    device=0,
    workers=2,
    project="/content/drive/MyDrive/TAGAD/YOLO_HEAD/runs",
    name="tagad_yolo11_head_v2",
    patience=10,
    save=True
)
```

### Final YOLOv11 test metrics

```text
Precision:    0.9105
Recall:       0.8732
mAP@50:       0.9198
mAP@50-95:    0.4591
```

Selected model:

```text
D:\TAGAD\models\tagad_yolo11_head_v2_best.pt
```

An earlier V1 model trained only on SCUT-HEAD Part A had poor generalization to DAiSEE-style foreground faces. V2 fixed this issue much better by training on Part A + Part B.

---

## 4. MediaPipe Feature Extraction

MediaPipe itself was **not trained**. The pretrained model is:

```text
D:\TAGAD\models\face_landmarker.task
```

The implementation uses:

```python
mp.tasks.vision.FaceLandmarker
```

### Original 5 geometric features

```text
mean_pitch
mean_yaw
mean_roll
mean_Gh
mean_Gv
```

Where:

- `pitch` = up/down head rotation
- `yaw` = left/right head rotation
- `roll` = head tilt
- `Gh` = horizontal gaze ratio
- `Gv` = vertical gaze ratio

For temporal attention, these standard deviations are also computed:

```text
std_pitch
std_yaw
std_roll
std_Gh
std_Gv
```

---

## 5. DAiSEE Experiment

DAiSEE was first used to train a five-state TAGAD SVM using the five geometric features.

### DAiSEE custom TAGAD label mapping

```python
def tagad_label_v2(row):
    engagement = row["Engagement"]
    boredom = row["Boredom"]
    confusion = row["Confusion"]

    if engagement <= 1:
        return "Disengaged"
    if confusion >= 2 and boredom >= 2:
        return "Ambiguous"
    if confusion >= 2:
        return "Confused"
    if boredom >= 2:
        return "Bored"
    if engagement == 3:
        return "Engaged"
    return "Attentive"
```

Ambiguous rows were excluded.

Clean DAiSEE samples:

```text
Train:       5199
Validation:  1345
Test:        1746
```

Feature extraction quality was very high:

```text
Train mean valid rate:       99.95%
Validation mean valid rate:  99.84%
Test mean valid rate:        99.70%
```

### Baseline SVM result

```text
Validation Accuracy: 24.39%
Macro F1:            21.09%
```

This model was rejected as too weak.

Main reason: DAiSEE is not naturally labeled for the exact five TAGAD states, and five static geometric features alone were not enough to separate states such as:

```text
Confused vs Bored
Engaged vs Attentive
```

DAiSEE is therefore no longer the primary final state-classification dataset.

---

## 6. DIPSER Attention Model

DIPSER was added mainly for **temporal attention classification**.

### Dataset scope

```text
20 subjects
```

Processed training table:

```text
D:\TAGAD\DIPSER\processed\dipser_tagad_windows.csv
```

Approximate processed size:

```text
579 windows
20 subjects
```

### Attention model comparison

#### 5-feature model

```text
pitch
yaw
roll
Gh
Gv
```

Result:

```text
Accuracy: approximately 78.41%
Macro F1: approximately 64.81%
```

#### 10-feature temporal model

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

Result:

```text
Accuracy: approximately 77.55%
Macro F1: approximately 66.04%
```

The **10-feature model** was selected because it better represents temporal behavior and had the better Macro F1.

Selected model:

```text
D:\TAGAD\models\dipser_attention_10-feature_diagnostic.joblib
```

Output classes:

```text
HigherAttention
LowerAttention
```

The live system uses roughly a **10-second rolling history per tracked student**.

---

## 7. Student Concentration / Engagement Image Dataset

A 2,120-image student engagement dataset was used for the richer state classifier.

Original classes included:

```text
Engaged\
    confused\
    engaged\
    frustrated\

Not engaged\
    Looking Away\
    bored\
    drowsy\
```

TAGAD mapping:

```text
engaged       -> Engaged
confused      -> Confused
bored         -> Bored
Looking Away  -> LookingAway
drowsy        -> Drowsy
frustrated    -> excluded
```

Usable extracted rows:

```text
1624
```

Class distribution:

```text
Confused:      369
LookingAway:   359
Engaged:       347
Bored:         331
Drowsy:        218
```

---

## 8. Rich MediaPipe Features

The original 5 geometry features were expanded using **20 MediaPipe facial blendshape features**.

### Geometry features

```text
mean_pitch
mean_yaw
mean_roll
mean_Gh
mean_Gv
```

### Blendshape features

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

Total rich state-classifier features:

```text
25
```

Feature file:

```text
D:\TAGAD\StudentConcentration\processed\student_concentration_rich_features.csv
```

---

## 9. Duplicate Leakage Audit

An initial random image-level split produced:

```text
Accuracy: 94.67%
Macro F1: 94.53%
```

This result was rejected as unreliable after a duplicate audit found:

```text
Exact duplicate cross-split pairs:       12
Near-duplicate cross-split pairs:     30,668
Unique images affected:                1,599 / 1,624
Near-duplicate affected rate:          98.46%
```

Therefore the original 94.67% random-split result must **not** be used as the trustworthy final performance estimate.

---

## 10. Near-Duplicate Grouping Strategy

Perceptual hashing (pHash) was used to cluster visually similar images.

An initial threshold:

```text
Hamming distance <= 4
```

was too aggressive because transitive chaining merged many images into huge groups.

Example:

```text
LookingAway at threshold 4:
1 group containing all 359 images
```

Threshold diagnostic showed that **threshold 1** preserved reasonable independent groups:

```text
Engaged:      101 groups
Confused:      76 groups
Bored:         73 groups
LookingAway:  109 groups
Drowsy:        45 groups
```

Final grouped evaluation therefore used:

```text
pHash Hamming threshold <= 1
StratifiedGroupKFold
```

with zero train/test group overlap.

---

## 11. Final Rich State SVM

Two SVM configurations were compared.

### Geometry-only SVM

```text
5 geometry features
```

Strict grouped result:

```text
Accuracy: 89.53%
Macro F1: 89.41%
```

### Rich 25-feature SVM

```text
5 geometry features
+
20 MediaPipe blendshape features
```

Strict grouped result:

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

Group overlap in every fold:

```text
0
```

Selected model:

```text
D:\TAGAD\models\tagad_state_svm_rich_threshold1_candidate.joblib
```

### Important limitation

The Student Concentration dataset does not provide reliable subject IDs.

The 95.50% accuracy should therefore be described as:

> **95.50% accuracy and 95.12% Macro F1 under near-duplicate-grouped cross-validation.**

It should not be described as guaranteed subject-independent classroom accuracy.

---

## 12. Final TAGAD Decision Logic

The rich state SVM predicts:

```text
Engaged
Confused
Bored
LookingAway
Drowsy
```

Mapping:

```text
LookingAway -> Disengaged
Drowsy      -> Disengaged
```

For `Engaged`, the DIPSER attention model refines the final output:

```text
Rich State SVM = Engaged
        |
        +-- HigherAttention -> Engaged
        |
        +-- LowerAttention  -> Attentive
```

Direct mappings:

```text
Confused -> Confused
Bored -> Bored
LookingAway -> Disengaged
Drowsy -> Disengaged
```

Final displayed TAGAD states:

```text
Engaged
Attentive
Confused
Bored
Disengaged
```

---

## 13. Live Single-Person Test

The complete live pipeline was tested successfully:

```text
Camera
-> YOLO
-> MediaPipe
-> Rich State SVM
-> DIPSER Attention SVM
-> Final TAGAD state
```

Example output:

```text
TAGAD: Confused
State SVM: Confused
Confidence: 99.3%
Attention SVM: LowerAttention
Pitch / Yaw / Roll
Gh / Gv
```

Important: SVM confidence is model confidence, not guaranteed real-world correctness.

---

## 14. Multi-Person Webcam Test

The code was expanded from:

```text
largest detected head only
```

to:

```text
process all detected YOLO heads
```

Example result:

```text
Heads: 2
Disengaged: 2
```

This confirmed simultaneous multi-person classification.

---

## 15. Classroom Video Testing

### First wide classroom video

```text
Average YOLO heads/frame: 27.14
Maximum heads: 30
YOLO detections: 17,996
Successfully classified: 1,586
MediaPipe/classification success: 8.81%
```

Conclusion: the video was too wide, with many faces too small or angled for MediaPipe.

### Improved 1080p classroom video

```text
Processed analysis frames: 212
Average YOLO heads/frame: 7.13
Maximum heads: 9
YOLO detections: 1511
Successfully classified: 1118
MediaPipe/classification success: 73.99%
```

This showed that camera angle, distance, resolution, and face size strongly affect real-world performance.

---

## 16. Temporary Student Tracking

A privacy-preserving geometric tracker was added.

It does **not** use facial recognition.

Temporary IDs:

```text
T1
T2
T3
...
```

Each track keeps:

```text
bounding box
pitch history
yaw history
roll history
Gh history
Gv history
state history
attention history
```

This allows separate 10-second attention histories for each tracked student.

---

## 17. Classroom Tracking Results

For the improved classroom video:

```text
Temporary Track IDs Created: 17
Logged Observations: 1511
Attention-SVM Warmed Observations: 848
```

Long stable tracks included:

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

Short fragmented tracks also occurred:

```text
0.00 to 0.84 sec
```

Planned production improvement:

```text
New detection
-> Tentative track
-> Must survive approximately 1-2 seconds
-> Confirmed student track
```

Heads that YOLO detects but MediaPipe cannot reliably process should be marked:

```text
Unclassified
```

instead of forcing an engagement label.

---

## 18. Current End-to-End Architecture

```text
Camera / Recorded Video / CCTV
        |
        v
YOLOv11 Head Detection
        |
        v
Temporary Student Tracking
        |
        v
MediaPipe Face Landmarker
        |
        +------------------------------+
        |                              |
        v                              v
5 Geometry Features              20 Blendshapes
        |                              |
        +--------------+---------------+
                       |
                       v
              Rich State SVM
                       |
                       v
 Engaged / Confused / Bored /
   LookingAway / Drowsy
                       |
          +------------+------------+
          |                         |
          v                         v
 DIPSER Attention SVM        Direct State Mapping
 10-second history           LookingAway -> Disengaged
          |                  Drowsy -> Disengaged
 Higher / Lower
   Attention
          |
          v
     Final TAGAD Output
          |
          v
Engaged / Attentive / Confused / Bored / Disengaged
```

---

## 19. Active Models Codex Should Use

Use only:

```text
D:\TAGAD\models\tagad_yolo11_head_v2_best.pt
D:\TAGAD\models\face_landmarker.task
D:\TAGAD\models\dipser_attention_10-feature_diagnostic.joblib
D:\TAGAD\models\tagad_state_svm_rich_threshold1_candidate.joblib
```

Do not use archived experimental models unless needed for comparison.

---

## 20. Important Integration Requirements for Codex

1. Detect **all visible heads**, not only the largest head.
2. Use temporary tracking IDs, not facial recognition.
3. Each tracked student must maintain an independent geometry buffer.
4. The DIPSER attention model uses roughly the latest 10 seconds of:
   - pitch
   - yaw
   - roll
   - Gh
   - Gv
5. Compute both mean and standard deviation for those 5 features.
6. Preserve the exact state-model feature-column order saved with the model.
7. If invoking the scikit-learn models directly, pass named Pandas columns because the pipelines were fitted with named columns.
8. Map:
   ```text
   LookingAway -> Disengaged
   Drowsy -> Disengaged
   ```
9. Refine Engaged with the DIPSER model:
   ```text
   Engaged + HigherAttention -> Engaged
   Engaged + LowerAttention  -> Attentive
   ```
10. If YOLO detects a head but MediaPipe fails, return:
    ```text
    Unclassified
    ```
11. Ignore very short temporary tracks in classroom analytics.
12. Recommended confirmed-track minimum duration:
    ```text
    approximately 1-2 seconds
    ```
13. Do not store face images for identity purposes.
14. Temporary IDs should exist only during the active session.
15. Classroom statistics should use confirmed tracks, not raw YOLO boxes.
16. Treat SVM confidence as model confidence only.
17. No face recognition is currently part of TAGAD.

---

## 21. Current Development Status

```text
YOLO head detector training                    DONE
YOLO SCUT-HEAD A+B evaluation                  DONE
MediaPipe head pose extraction                 DONE
MediaPipe eye-gaze extraction                  DONE
DAiSEE feature extraction                      DONE
DAiSEE baseline SVM                            DONE / rejected as weak
DIPSER processing                              DONE
DIPSER temporal attention SVM                  DONE
Student Concentration feature extraction       DONE
MediaPipe blendshape extraction                DONE
Duplicate leakage audit                        DONE
Strict grouped rich SVM evaluation             DONE
Final rich state SVM selected                  DONE
Single-person webcam inference                 DONE
Multi-person webcam inference                  DONE
Classroom MP4 inference                        DONE
Temporary per-person tracking                  DONE
Per-track 10-second attention buffers          DONE

Confirmed-track filtering                      TODO
Unclassified handling refinement               TODO
Real classroom pilot validation                TODO
IP CCTV / RTSP input                           TODO
Three-camera support                           TODO
Cross-camera duplicate handling                TODO
ASP.NET backend integration                    TODO
SignalR live dashboard integration             TODO
Database/session analytics                     TODO
Final real-world classification evaluation     TODO
```

---

## 22. Recommended Next Step

The AI models should mostly be considered **frozen for now**.

Do not immediately add another public dataset.

Recommended next work:

```text
1. Add confirmed-track filtering.
2. Add explicit Unclassified handling.
3. Run a realistic classroom pilot recording.
4. Compare predictions against known ground-truth behavior.
5. Retrain only if real-world tests show consistent mistakes.
6. Replace MP4 input with IP CCTV / RTSP streaming.
7. Integrate predictions into the TAGAD backend and dashboard.
```

The biggest remaining question is no longer whether the models can run.

The main question is:

> How accurately and reliably does the complete TAGAD pipeline perform under the real camera distance, angle, lighting, occlusion, and classroom conditions planned for deployment?
