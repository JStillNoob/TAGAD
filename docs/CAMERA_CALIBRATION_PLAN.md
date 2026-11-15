# A4 Camera Geometry and Duplicate Control

Prepared November 5, 2026. Physical calibration and measurements are pending
the approved classroom setup next week.

## Current implementation

| Entry point | Observed behavior | A4 work required |
| --- | --- | --- |
| `pipeline/tagad_pipeline/configuration.py` | Sources are matched by saved camera IP, with a legacy position fallback. Calibration fields are absent and unknown configuration keys are rejected. | Bind calibration to the classroom and physical camera record, including the worker's network context. |
| `pipeline/tagad_pipeline/controller.py` | Each worker constructs its own `CameraPipeline` and tracking history. | Pass the matching camera calibration into each worker. |
| `pipeline/tagad_pipeline/inference.py` | Head detections cover the full frame. Head pose and gaze feed the frozen models directly. | Apply calibrated student zones and exclusions before tracking. Record lesson targets separately for evaluation. |
| `backend/core/analytics.py` | Counts from every submitted camera summary contribute to the distribution. `students_detected` is the maximum `total_detected` of an individual summary. | Preserve camera and timing attribution when reviewing overlap and sampling bias. |
| `frontend/src/views/AnalyticsView.vue` and `backend/core/report_generation.py` | The UI and PDF label the peak as detections from one camera sample. CSV exports append a Detection Scope column. | Check scope wording alongside calibration evidence during acceptance review. |

Camera position names describe mounting locations. The lesson target can be
the board, a moving teacher, a book, or another student during assigned work.
The same lesson target produces different head directions in different views.

## Proposed configuration record

The following fields describe the planned calibration record. Record actual
values in the approved private pilot folder. Software support is pending.

| Field | Meaning |
| --- | --- |
| Classroom and camera reference | Organization, classroom, and physical camera record within the worker's network context. |
| Calibration revision | Version and date that connect measurements to the configured geometry. |
| Image geometry | Width, height, orientation, crop, zoom, and camera mounting position used during calibration. |
| Student polygons | Image regions belonging to the physical seating zones assigned to this camera. |
| Exclusion polygons | Teacher area, door, aisle, foreground, or other irrelevant regions where practical. |
| Lesson targets | Board and teacher-area locations plus activity-specific target notes for this view. |
| Direction references | Observed head/gaze ranges while volunteers look at known lesson targets under the approved procedure. |
| Zone ownership | Exactly one camera owner for each physical seating zone. |
| Calibration state | Draft, measured, reviewed, or invalidated, with the supporting private evidence reference. |

Use normalized image coordinates from 0 to 1, with the origin at the upper-left
corner. Apply them against the declared image geometry. Camera movement, crop,
rotation, lens/zoom changes, or a new seating layout requires review and may
invalidate the calibration.

Direction references are evaluation evidence. Any adjustment of trained-model
features requires a separate model-validation decision in A6. Arbitrary yaw
offsets could move inputs outside the training distribution.

## Proposed zone ownership

Use fixed physical seating zones with one camera owner per zone. Choose the
owner from measured visibility, regardless of its Front, Left, or Right name.

1. Draw a seating-area plan using anonymous zone codes such as Z1, Z2, and Z3.
2. Select one owner camera for each zone based on the clearest sustained view.
3. Project each owned zone into that camera's image. Account for perspective
   and the range of student head positions when seated or leaning.
4. Filter head-box centers against the owned student polygons before tracking.
   Exclusion polygons take precedence. Shared polygon edges require one
   deterministic owner.
5. Inspect the other cameras for the same physical zone. Their official
   counting regions must exclude it.
6. Record boundary ambiguity, occlusion, gaps, and student movement. Count only
   regions whose ownership can be verified during the calibration exercise.

Separate polygons in different images do not prove that the physical zones
are separate. Verify correspondence using the seating plan and synchronized
views. Image thirds alone are insufficient because perspective differs.

This is a proposed method awaiting physical validation and implementation.
Movement between zones, overlapping head projections, and independent camera
sampling can still create repeated observations. A calibrated zone scheme
supports coverage control. Unique-person totals require further evidence.

If an owner camera goes offline, record the zone as unavailable. Transferring
ownership requires a separately reviewed configuration that keeps one owner
per zone throughout the transition.

## On-site calibration sequence

Use the permission, storage, and synchronization procedure in
[`CLASSROOM_GROUND_TRUTH_PROTOCOL.md`](CLASSROOM_GROUND_TRUTH_PROTOCOL.md).
Keep completed records and reference images in private pilot storage.

1. Verify that each configured Front, Left, and Right source matches its
   physical camera and classroom. Record image geometry and clock offsets.
2. Identify student seating, teacher/board targets, doors, aisles, and
   foreground separately in each view.
3. Observe representative front, middle, and back seating areas. Compare head,
   face, and upper-body visibility independently.
4. Assign physical zone owners and record their image polygons and exclusions.
5. Under the approved procedure, observe lesson-facing directions, including
   looking at the board, following a moving teacher, reading, and group work.
6. Check teacher/visitor movement and student zone boundaries using synchronized
   views. Document any false student counts and repeated contributions.
7. Review the measurements, revise the geometry where needed, and repeat the
   affected checks during the approved test.
8. Close checklist gates only after measured evidence and software behavior
   agree. Record the calibration revision used for the evaluated session.

## Blank per-camera calibration worksheet

Copy this worksheet to private storage before entering classroom details.

| Camera | Image geometry | Lesson targets and direction references | Owned physical zones | Student polygon references | Exclusion polygon references | Revision and review state |
| --- | --- | --- | --- | --- | --- | --- |
| Front | Pending | Pending | Pending | Pending | Pending | Draft |
| Left | Pending | Pending | Pending | Pending | Pending | Draft |
| Right | Pending | Pending | Pending | Pending | Pending | Draft |

## Measurement definitions

Use the same corrected five-second windows for all cameras. Record camera,
window, activity, and calibration revision with each aggregate measurement.

| Measurement | Numerator | Denominator and interpretation |
| --- | --- | --- |
| Head visibility | Student observations with a sufficiently visible head | All manually located student observations in the assigned zone. |
| Face visibility | Student observations with usable facial detail | The same manually located observations. Record blur, distance, side profile, and occlusion. |
| Upper-body visibility | Student observations with visible shoulders, elbows, and wrists | The same manually located observations. Record each joint group separately for A5. |
| Head-detection coverage | Visible student heads matched to detector candidates | Manually visible heads in the assigned zone. |
| Teacher/visitor false-count rate | Teacher/visitor observations emitted as confirmed student predictions | Manually visible teacher/visitor observations in the evaluated windows. Record the raw numerator and denominator. |
| Repeated zone contributions | Student observations contributing from multiple cameras in the same evaluation window | Manually compared observations with adequate synchronized views. Record ambiguous cases separately. |

Record a zero denominator as unavailable. Head, face, and body visibility are
separate measurements. Body visibility can be reviewed manually while the pose
model work remains in A5. A1's raw-state counts cannot establish these rates
because they contain neither spatial evidence nor person correspondence.

Also record analyzed frames and accepted summaries per camera. Different
sampling rates can weight one view more heavily even after zones are assigned.

## Verification record

- [ ] Each camera reference matches the intended physical classroom camera.
- [ ] Lesson direction is documented separately for each view and activity.
- [ ] Student regions and teacher/door/foreground exclusions match actual views.
- [ ] Every covered physical seating zone has exactly one reviewed owner.
- [ ] Controlled boundary observations contribute from one owner only.
- [ ] Head, face, and upper-body visibility have measured counts per camera.
- [ ] Teacher/visitor false counts have measured numerators and denominators.
- [ ] Boundary movement, gaps, owner-camera loss, and uncertainty are recorded.
- [ ] UI, API, and exports describe observation counts with their actual scope.
- [ ] Applicable software entry points enforce the reviewed calibration.

Physical observations, implementation checks, and remaining limitations must
be attached to the checklist before A4 can be marked complete.
