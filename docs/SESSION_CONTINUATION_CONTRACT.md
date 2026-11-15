# C1 Session Continuation Contract

Revision 1, November 7, 2026.

**Status — C1–C6 complete. Software implementation verified and C6 physical acceptance reported passed by the user on November 9, 2026.**

This contract defines saved lessons and their class meetings. The checklist
tracks implementation in `SESSION_CONTINUATION_CHECKLIST.md`.

## Existing behavior and integration points

| Source | Observed behavior | Required integration |
| --- | --- | --- |
| `backend/core/models.py` | `ClassroomSession` has start/end timestamps and a partial unique constraint allowing one unfinished meeting per user. | Add the lesson link and explicit meeting outcome while preserving that constraint. |
| `backend/core/session_serializers.py` | Direct creation can start a meeting immediately and creates its first slide event. | Create lesson progress atomically through the shared start operation. |
| `backend/core/session_views.py` | Prepared start selects slide 1; end sets `ended_at`; slide navigation creates events. | Restore the saved slide for continuation and commit each lifecycle change atomically. |
| `backend/core/session_preparation.py` | Unstarted preparations expire after 30 minutes and are deleted. | Serialize continuation expiry with start and cancellation, and preserve the lesson. |
| `backend/core/session_access.py` | Teacher history is owner scoped; org-admin history is organization scoped. | Preserve history access and require lesson ownership for continuation mutations. |
| `backend/core/analytics.py` | Meeting duration is end minus start; slide durations end at the next event or meeting end. | Give each continuation a fresh meeting and fresh slide events. |
| `backend/core/engagement_pipeline.py` | Ingestion validates session/event association and rejects new submissions to ended meetings. | Preserve association checks and idempotent acknowledgements of already accepted ingestion. |
| `frontend/src/sessionReliability.js` | Start recovery accepts an own active meeting; end recovery accepts the requested ended meeting. | Resolve the exact lesson, meeting, and terminal action after uncertain responses. |
| `pipeline/tagad_pipeline/recording_controller.py` | Recording follows started session IDs and stops when a meeting leaves work discovery. | Use the continuation's new session ID and preserve earlier media. |

## Data contract

### LessonProgress

| Field | Required meaning |
| --- | --- |
| `id` | Stable lesson identity across all its meetings. |
| `organization` | Organization fixed when the lesson first starts. |
| `owner` | User who teaches and controls the lesson. |
| `subject` | Original subject reference. |
| `classroom` | Original classroom reference, retained if subject assignment later changes. |
| `presentation` | Original uploaded presentation reference. |
| `last_slide` | Last server-accepted slide from that presentation. |
| `state` | `active`, `saved`, or `completed`. |
| `revision` | Positive integer changed by accepted state, preparation, or slide changes. |
| `created_at`, `updated_at` | Server timestamps for history and recovery. |

Use protected foreign keys for these durable references. Availability and
access are revalidated on mutations. The saved organization, classroom,
subject, presentation, and owner establish the lesson's identity. Presentation
edits or subject reassignment cannot silently redirect it to another class.

### ClassroomSession additions

| Field | Required meaning |
| --- | --- |
| `lesson` | Nullable protected FK to `LessonProgress`, including a prepared continuation. |
| `continued_from` | Nullable protected self-reference to the preceding closed meeting. |
| `continuation_request_id` | Nullable UUID used to recover repeated continuation preparation requests. |
| `end_action` | Empty for an open or legacy meeting; `save` or `finish` after a new tracked meeting closes. |

Enforce uniqueness of `(user, continuation_request_id)` for populated keys,
one successor for a populated `continued_from`, and one unfinished meeting
per populated `lesson`. Retain `one_active_session_per_user`. A cancelled or
expired preparation is deleted and releases its reservations.

Enforce row-local outcome/timestamp checks at the database boundary. Validate
cross-row relationships inside the lifecycle transaction. The owner, subject,
presentation, and classroom of a linked meeting must match its lesson. Its
predecessor must be the latest closed meeting of that same lesson.

## State invariants

1. `active` has exactly one started, unfinished meeting. `last_slide` matches
   its latest accepted event, ordered by `entered_at` and primary key.
2. `saved` has zero ongoing meetings and at most one prepared continuation.
   Its last confirmed slide remains available during preparation.
3. `completed` has zero unfinished meetings and is terminal for continuation.
4. First-meeting preparation has a null lesson link. Actual first start creates
   the lesson, first event, and active meeting in one transaction.
5. A started meeting retains its timestamps and terminal outcome after closing.
   Continuing creates a new meeting ID and initial slide event.
6. A preparation reserves the teacher's existing unfinished-meeting slot.
   Saving a class releases that slot while preserving the lesson.
7. Each slide event, engagement summary, alert, and recording belongs to the
   meeting that produced it. Lesson revision changes exclude heartbeat and
   engagement-ingestion activity.
8. Repeated identical requests acknowledge their recorded outcome. A stale or
   conflicting request returns the authoritative state with a recoverable error.

## Legal transitions

| Action and prerequisite | Lesson after commit | Meeting after commit | Saved slide and next action |
| --- | --- | --- | --- |
| Prepare a first meeting | No lesson yet | Preparing | Existing presentation preview; Start or Cancel. |
| Cancel/expire first preparation | No lesson | Preparation removed | Teacher can prepare another class. |
| Start first meeting through either start entry point | Active | Ongoing | First valid slide; Navigate, Save, or Finish. |
| Navigate within active meeting | Active | Ongoing, fresh event when slide changes | Last accepted slide; Save or Finish uses this value. |
| Save active meeting | Saved for Later | Closed with `end_action=save` | Current confirmed slide; Continue or Finish saved lesson. |
| Prepare continuation of saved lesson | Saved for Later, displayed as Preparing to Continue | New preparing meeting linked to predecessor | Saved slide; Start or Cancel. |
| Cancel/expire continuation preparation | Saved for Later | Preparation removed | Same saved slide; Continue remains available. |
| Cameras unavailable at continuation start | Saved for Later, Preparing to Continue | Preparing | Same saved slide; Retry readiness or Cancel. |
| Start prepared continuation | Active | New ongoing meeting | Fresh event for saved slide; Navigate, Save, or Finish. |
| Finish active meeting | Completed | Closed with `end_action=finish` | Last accepted slide retained; History and reports available. |
| Finish saved lesson with zero unfinished meetings | Completed | Earlier meetings retain their outcomes | Saved slide retained; History and reports available. |

Finishing a saved lesson is available from its card after confirmation. It
requires zero prepared or ongoing meetings and completes the lesson without
starting cameras. A teacher can finish early or save on the last slide. Slide
number alone never completes the lesson.

Invalid transitions return an error and the persisted state. In particular,
completed lessons reject continuation, preparations reject Save/End, and a
saved lesson with a prepared continuation requires Start or Cancel before
another terminal action.

## Request and response contract

All paths below are under `/api/auth/`. Use existing CSRF/session authentication
for user actions and the existing paginated collection format.

| Route | Input | Success and retry behavior |
| --- | --- | --- |
| `GET lessons/?status=saved` | Existing pagination/search parameters | Owner-scoped lesson summaries including preparation state and blocking reasons. |
| `GET lessons/{id}/` | Lesson ID | Exact recovery summary with latest meeting, prepared/active meeting IDs, revision, and saved slide. |
| `GET sessions/{id}/` | Meeting ID | Exact meeting recovery through existing history permissions, including its committed outcome and continuation key. |
| `GET sessions/?lesson={id}` | Lesson filter plus existing pagination | Linked meeting history through existing history permissions. |
| `POST lessons/{id}/continue/` | `request_id`, `expected_revision`, `from_session`, `cameras` | 201 for a new prepared meeting. Same key and semantic input returns that meeting with 200 and its current state. |
| `POST sessions/{id}/start/` | `expected_revision` for a prepared continuation | Existing meeting response with additive lesson fields. Already-started retries return that same meeting's actual state. |
| `POST sessions/{id}/enter-slide/` | Existing `slide`, plus `expected_revision` from the new UI | Existing event response plus latest lesson revision. Re-selecting the current slide keeps its event and acknowledges current state. |
| `POST sessions/{id}/end/` | `action` of `save` or `finish`, plus `expected_revision` | Existing meeting response plus committed `end_action` and lesson summary. Same terminal action returns 200; conflicting action returns 409. |
| `POST lessons/{id}/finish/` | `expected_revision` | Completes a saved lesson with zero unfinished meetings. Repeated completion acknowledges current completed state. |
| `DELETE sessions/{id}/prepare/` | Existing meeting ID | Existing 204 response. Recover an uncertain response by reading the lesson. |

The first-meeting create/prepare paths retain their existing payloads. New UI
actions on a linked lesson send `expected_revision`. Validate strict integer
and UUID types, supported actions, a presentation-owned saved slide, and the
classroom-owned unique camera IDs at the trust boundary.

The legacy end request with an omitted action retains Finish semantics.
Legacy navigation keeps its current server-accepted event behavior. Additive
response fields preserve existing callers. A prepared continuation's start
uses its saved slide even if the teacher has previewed other slides.

Lesson summaries contain `id`, `state`, `revision`, owner/subject/classroom/
presentation references and display labels, `last_slide`, slide number/count,
last-taught timestamp, latest meeting ID, prepared/active meeting IDs, and a
continuation availability reason. Meeting responses add `lesson`,
`continued_from`, `continuation_request_id`, and `end_action`. UTC timestamps are rendered in the user's
local timezone, and each meeting's date is assigned at its actual start.

### Errors and recovery

- Return 400 for malformed values or resource validation failures, 401/403
  through existing authentication rules, and 404 for an inaccessible lesson
  or meeting. ID guesses must retain organization isolation.
- Return 409 for stale revision, another unfinished meeting, conflicting
  terminal action, reused key with different semantic input, completed
  lesson continuation, or changed continuation source.
- Actionable errors include a stable `code` and `detail`. Once access is
  established, include the current lesson revision, relevant owned meeting
  ID/state, and committed `end_action` where applicable.
- Check a committed meeting outcome or matching request key before rejecting
  its retry for stale revision. Replays acknowledge history without changing
  a later meeting or the current lesson state.
- After losing a response, read the exact lesson and meeting. Confirm Save
  using `end_action=save`, and Finish using its committed completion result.
  Resolve a continuation through its request key and meeting identity.
- Prepared-start recovery matches its original session ID even when the first
  start response was lost before a lesson ID reached the browser. Resolve
  that meeting before applying another action.
- Cancellation or expiry increments the lesson revision before deleting its
  prepared meeting. An old preparation retry with the old revision returns
  409. A fresh explicit Continue action uses a fresh UUID and current revision.
- A lost cancellation response may produce 404 on a repeated DELETE. The
  lesson read establishes whether it is saved or has another preparation.
- Until the outcome is known, show a reconnection/recovery state and suppress
  competing actions. If Save failed before commit, return to the ongoing
  class after reconnecting. Process exit alone leaves the meeting's persisted
  lifecycle in place for explicit recovery when the service returns.

## Transaction and concurrency requirements

Route both start entry points and continuation through shared lifecycle
operations. Serialize user-slot reservation and lesson changes, lock the
affected meeting and current event, then revalidate prerequisites before
commit. Use one documented lock order across lifecycle, preparation cleanup,
and dependent-resource operations. C2 must check lock behavior on PostgreSQL.

The slide event and lesson's saved slide/revision commit together. The end
timestamp, `end_action`, and lesson state/revision commit together. If Save
and navigation race, the revision check either commits the acknowledged
slide or returns a stale-state conflict for review. Two terminal actions
commit one outcome. Two Continue requests reserve one successor.

Expiry must recheck that the preparation is still unstarted under the same
locking protocol as Start. Cleanup skips a meeting that has already started.
An ingestion already accepted can acknowledge its existing ingestion ID;
new submissions to a closed meeting retain the existing rejection behavior.

## Saved-slide and meeting boundaries

- Start first teaching on the first valid slide. Persist each later accepted
  slide as both a meeting event and the lesson's current slide.
- Revisiting slide 2 after slide 12 makes slide 2 the saved slide. It represents
  where teaching stopped. Include slide number in the Save confirmation.
- Saving on slide 25 of 25 still permits continuation on slide 25. Finishing
  remains an explicit choice.
- Reject a missing slide or unavailable presentation with an actionable error
  and retain progress. Require resource recovery before continuation.
- End each meeting's last slide interval at that meeting's end timestamp.
  Start a fresh interval at continuation start, including for the same slide.
- Stop recording through normal work discovery after the meeting closes.
  Preparation retains normal readiness processing and recorder standby.
  Actual continuation start produces a fresh recording under the new ID.

## Existing data, access changes, and resource lifecycle

- Add nullable meeting fields and an empty legacy outcome without rewriting
  previous timestamps, slide events, summaries, reports, or recording files.
  Existing meetings keep their current lifecycle. Continuation is available
  for newly tracked lessons. Existing ongoing meetings can finish normally.
- New progress endpoints require ownership and current membership in the
  saved organization. Existing org-admin history/report permissions continue
  to govern access to the linked meeting records.
- Revalidate active user/organization, subject assignment, original classroom,
  presentation readiness, and selected cameras at preparation and start.
  Reassignment or archival blocks continuation with an explanation and retains
  history. Completion remains available to the authorized owner for a saved
  lesson whose teaching dependencies are unavailable.
- A resource becoming unavailable during an active meeting must leave a
  permitted Save/Finish cleanup path for its authorized owner. After user or
  organization access is revoked, recovery uses existing authorized
  administration procedures and retains the persisted meeting identity.
- Block presentation archival/deletion and individual meeting archival while
  their linked lesson is active or saved. Tell the teacher to finish the
  lesson first. Protect original files, slides, predecessor references, and
  lesson rows against destructive deletion through their FK relationships.
- Apply dependency guards before file deletion or derived-slide regeneration
  in `presentation_processing.py` and presentation cleanup paths. Database
  protection must be checked while referenced media is still intact.
- Classroom/subject/organization archival follows existing administration
  policy. Continuation becomes unavailable until its dependencies are restored
  or the saved lesson is completed. A completed lesson stays completed after
  restoring any archived resource.
- Backward migration must address newly persisted progress and links before
  dropping feature fields. Document the recovery procedure with C2's migration.
- Existing report and engagement retention policies still apply to older
  meetings. History must identify missing/expired evidence when relevant.
  Lesson progress persists independently of summary retention.

## Acceptance trace

All timestamps in this example use Asia/Singapore. IDs are illustrative.

| Step | Lesson | Meeting and slide | Timing and recording |
| --- | --- | --- | --- |
| Nov 7, 09:00 Start | L1 Active | M1 ongoing; initial event for slide 1 of 25 | M1 timer and capture start. |
| Navigate to slide 12 | L1 Active, last slide 12 | M1 event for slide 12 | Earlier visits stay in M1. |
| 09:40 Save | L1 Saved for Later, last slide 12 | M1 closed with Save | M1 duration 40 minutes; last interval closes; capture stops. |
| Restart TAGAD; teach another class | L1 remains Saved for Later | Other lesson uses its own meeting | L1 has zero ongoing work. |
| Nov 8, 08:55 Continue | L1 Saved, Preparing to Continue | New M2 preparation linked to M1; preview slide 12 | Readiness checks run; recorder stays in standby. |
| Cancel or expire preparation | L1 remains Saved, last slide 12 | Unstarted M2 preparation removed | Teacher reservation released; retry uses a fresh request. |
| Continue again; 09:00 Start | L1 Active, last slide 12 | M3 ongoing; fresh initial event for slide 12 | New dated meeting, timer, and recording folder. |
| 09:40 Finish after slide 25 | L1 Completed, last slide 25 | M3 closed with Finish | M3 duration 40 minutes; capture stops. |

The successful meetings each contribute 40 minutes. Their combined teaching
time is 80 minutes. The overnight interval contributes zero slide or meeting
duration. History links M1 and M3 to L1. The cancelled preparation contributes
zero teaching events or recording time. Repeating Continue while L1 is
completed yields a completion conflict and a history link.

## Engineering review evidence

The contract review traced both current start paths, session ownership,
preparation cleanup, end/navigation actions, analytics timing, ingestion, and
automatic recording. It resolved these gaps in the initial checklist.

| Scenario reviewed | Contract resolution |
| --- | --- |
| Multi-day gap inflated duration | Separate dated meetings and closed final intervals. |
| Continuing opened slide 1 | Saved slide overrides the first-slide default at continuation start. |
| Cancel/expiry removed saved progress | Lesson survives deletion of its preparation; revision advances. |
| Expiry raced with Start | Shared locking and an unstarted recheck. |
| Lost Save response mistaken for Finish | Persisted explicit `end_action` and exact-meeting recovery. |
| Old start retry restored another class | Match lesson, request key, predecessor, and meeting identity. |
| Save raced with another-tab navigation | Atomic slide/progress update plus revision conflict. |
| Duplicate or conflicting continuation | Request-key uniqueness, successor uniqueness, and teacher/lesson reservations. |
| Old cancelled preparation retried later | Stale revision rejection and fresh-key requirement. |
| Teacher reviewed an earlier or final slide | Last confirmed slide retained; completion is explicit. |
| Saved lesson needed finishing with offline cameras | Saved-card Finish closes the lesson without creating a meeting. |
| Presentation or assignment became unavailable | Retain identity/history and expose the dependency recovery path. |
| Old ingestion arrived after continuation | Preserve session/event association and ended-session checks. |
| Legacy data and clients encountered new fields | Nullable links, legacy lifecycle, additive responses, default Finish. |

C1 completion means these decisions and the acceptance trace are documented
and internally reviewed. The C2 backend, migration, and C3–C5 software integration
checks are complete. The user reported C6 physical camera acceptance passed on
November 9, 2026. The checklist records the evidence source and its limits.

Contract checks resolved all nine referenced source files, confirmed the
fourteen review scenarios and seven C1 checklist items, and traced the two
40-minute meetings with a cancelled preparation between them. The independent
design walkthrough restored slide 12 and calculated 80 teaching minutes.
