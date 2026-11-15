# TAGAD Session Continuation Checklist

Prepared November 7, 2026.

**Status — C1–C6 complete. C6 physical acceptance reported passed by the user on November 9, 2026.**

## Objective

Allow a teacher to save an unfinished lesson, end the current class meeting,
and continue the same uploaded presentation from its saved slide during a
later meeting. Preserve progress across browser closure and application or
laptop restarts. Keep dates, durations, engagement results, and recordings
attributed to their actual class meetings.

Check implementation items only after their verification gate passes. Track
physical-camera acceptance separately from software verification.

## Teacher experience

1. The teacher uploads a presentation and starts a class through the existing
   preparation and camera-readiness flow.
2. **End Class** opens a dialog with three clearly labeled actions.
   - **Save & Continue Later** saves the last confirmed slide and closes this
     meeting. Explain that the lesson can be continued next time.
   - **Finish Lesson** closes the meeting and marks the lesson complete.
     Confirm this choice before applying it.
   - **Keep Teaching** dismisses the dialog and returns to the current slide.
3. The Live Session page shows saved lessons with presentation title, subject,
   classroom, last-taught date, and progress such as **Slide 12 of 25**.
4. **Continue Lesson** opens preparation using the existing presentation and
   saved slide. The teacher reviews camera readiness and starts the meeting.
5. The resumed presentation starts on the saved slide. Previous/Next controls
   remain available for review and normal teaching.
6. Each later meeting can be saved again or finished. The teacher can start a
   different class while a lesson is saved.

Example acceptance journey — teach slides 1 through 12 of a 25-slide deck,
save the lesson, restart TAGAD, continue on slide 12 next day, and finish the
remaining slides. History shows two linked meetings with their own reports.

## Structural decisions

These are the implementation defaults for the first version.

- A lesson-progress record belongs to one teacher, subject/classroom, and
  uploaded presentation. It holds the last confirmed slide and lesson state.
- Each actual class meeting uses a `ClassroomSession` linked to that record.
  A continuation gets a new session ID, date, slide events, summaries, and
  recording folder.
- Lesson states are **Active**, **Saved for Later**, and **Completed**.
  A continuation in preparation is displayed as **Preparing to Continue**,
  derived from its prepared meeting. Its saved progress remains recoverable.
- Create the lesson-progress record when the first meeting actually starts.
  Preparing a continuation references the existing record. Cancelling or
  expiring that preparation leaves the saved lesson available.
- Preserve the existing database rule allowing one unfinished meeting per
  teacher. Enforce at most one prepared or active meeting per lesson as well.
- Bind continuation to the saved subject, classroom, presentation, and owner.
  Resolve selected cameras through that classroom's current active records.
- Persist the last slide after each accepted slide navigation. The server's
  latest accepted slide is the recovery reference.
- Existing sessions retain their history and completion meaning through a
  backward-compatible migration. Continuation eligibility is explicit for
  lessons created with the new workflow.
- Apply the current UI conventions in `UI_STYLE_GUIDE.md` and reuse existing
  session preparation, presentation rendering, pagination, and recovery logic
  where their behavior fits the new workflow.

## C1 — Confirm the data and lifecycle contract

**Status — Complete as a reviewed design, November 7, 2026.**

The reviewed [C1 contract](SESSION_CONTINUATION_CONTRACT.md) defines the schema,
transitions, API behavior, recovery, compatibility, and acceptance trace.

- [x] Define the lesson-progress fields, meeting link, lesson-state choices,
      and explicit save/finish request and response contracts.
- [x] Document legal transitions from first start through repeated
      save/continue cycles and final completion.
- [x] Define how prepared continuation, cancellation, expiry, and competing
      requests affect the saved lesson and teacher's active-meeting slot.
- [x] Define saved-slide recovery, including a saved final slide and repeated
      visits to earlier slides.
- [x] Define existing-session migration behavior and presentation/archive
      lifecycle rules for lessons with saved progress.

### Verification gate

- [x] Every action has an unambiguous resulting lesson state, meeting state,
      saved slide, and eligibility for another action.
- [x] The 25-slide acceptance journey can be traced through the proposed data
      without counting the time between meetings as teaching time.

### Engineering-loop evidence

- Inspected both start entry points, ownership queries, preparation expiry,
  slide navigation, end actions, analytics intervals, ingestion, and recording.
- Resolved preparation/start races, exact-action retry recovery, revision
  checks, explicit final-slide handling, and dependency/archive rules.
- Traced two 40-minute meetings, a cancelled continuation preparation,
  application restart, another class, and final completion across two days.
- Reviewed the contract's transition table and fourteen failure/compatibility
  scenarios. Runtime implementation and physical verification are tracked in C2–C6.
- Passed source-reference/checklist checks and an independent design walkthrough
  restoring slide 12 with two distinct 40-minute meetings and no overnight time.

## C2 — Persistent progress and safe backend actions

**Status — Complete, November 7, 2026.**

- [x] Add the smallest model and migration changes required by C1.
- [x] Connect both existing session-start entry points to lesson creation or
      continuation through shared lifecycle logic.
- [x] Save accepted slide navigation and lesson progress atomically.
- [x] Implement **Save & Continue Later** and **Finish Lesson** atomically
      with the current meeting's end timestamp and final saved slide.
- [x] Prepare and start a continuation from its saved slide. Reuse camera
      readiness checks before its actual start.
- [x] Lock the affected lesson and meeting during transitions. Enforce the
      one-meeting rules at the database boundary.
- [x] Make repeated identical requests return the committed result. Reject
      conflicting save/finish or continuation requests with actionable errors.
- [x] Apply teacher ownership and organization scoping to list, detail, save,
      continue, and finish actions, including direct requests by guessed IDs.
- [x] Paginate saved lessons and linked meeting history using existing APIs.

### Verification gate

- [x] Independent backend requests retrieve the saved lesson and confirmed
      slide from persisted data. Browser restoration is verified with C4.
- [x] Repeated requests and concurrent client requests create at most one continuation
      and one terminal result for a meeting.
- [x] Cancelling or expiring a continuation preparation preserves progress.
- [x] Existing start, end, cancellation, and slide-navigation callers pass
      their relevant regression checks.

### C2 implementation and evidence

- `backend/core/models.py` and migration `0017_session_continuation` add durable
  lesson progress, protected references, nullable legacy-compatible meeting
  links, explicit outcomes, and database uniqueness/check constraints.
- `backend/core/session_lifecycle.py` shares creation/start operations and
  serializes transitions in user, presentation, lesson, then meeting order.
  Preparation expiry rechecks state under the same locking protocol.
- `backend/core/lesson_views.py` adds owned lesson list/detail/continue/finish
  and exact meeting detail. Existing navigation/end APIs accept additive
  revision/action fields and return committed outcomes for recovery.
- Backend guards preserve referenced media before presentation processing or
  cleanup and block archiving unfinished lesson dependencies. Missing media,
  unavailable storage, and reassignment retain saved progress.
- `python manage.py test core.tests --settings=tagad.test_settings --noinput
  --verbosity 0` completed 283 checks. The five PostgreSQL concurrency checks
  are skipped by SQLite and run separately below.
- All 24 checks in `core.tests.test_lesson_continuation` passed on PostgreSQL
  in a unique temporary schema, including five real concurrent-request checks.
  The local role supports schema creation and lacks database-creation rights,
  so the rehearsal used a schema-scoped Django runner. Its search path was
  restricted to that schema, which was removed after verification. Application
  session, presentation, and engagement-summary counts remained unchanged.
- Concurrent checks cover identical continuation keys, competing keys,
  Save versus Finish, Save versus slide navigation, and Start versus Cancel.
- The acceptance fixture restores slide 12 and verifies two separate
  40-minute meetings across an overnight gap. Additional checks cover expiry,
  earlier/final slides, exact-action retries, authorization, legacy sessions,
  storage failures, media protection, and migration reversal protection.
- Created the ignored backup
  `backend/backups/tagad-20261107-075447.dump` before applying migration 0017
  to the local application database. Existing session, presentation, event,
  engagement-summary, and user counts were preserved. Existing sessions kept
  null lesson links and their prior lifecycle.
- `migrate --check`, `makemigrations --check --dry-run`, and Django `check`
  passed. Migration reversal stops while persisted lesson progress exists.
  Recover through the pre-migration backup or preserve new progress before
  attempting reversal.
- All 51 pipeline checks passed after the backend changes.

Backend actions and teacher controls are available. Physical camera acceptance
stays in C6.

## C3 — Camera, processing, and recording lifecycle

**Status — Software integration verified November 7, 2026. Physical acceptance reported passed November 9, 2026, under C6.**

- [x] Ending a meeting through either action closes its work-discovery entry,
      camera processing, and automatic recording through the shared lifecycle.
- [x] A saved lesson releases the teacher's active-meeting slot.
- [x] Preparing a continuation performs the normal camera-readiness flow.
      Recording waits for that new meeting's actual start.
- [x] Start recording under the continuation's new session ID and preserve
      earlier meeting files and manifests.
- [x] Preserve saved progress if cameras are unavailable, the controller is
      stopped, or continuation preparation fails.
- [x] Confirm that old slide events and late engagement submissions cannot
      enter the resumed meeting's analytics.

### Verification gate

- [x] Mocked work-discovery and recorder checks demonstrate stop after save,
      standby during preparation, and a new capture after continuation starts.
- [x] Camera failure produces a recoverable preparation state with the saved
      lesson and its slide intact.

### C3 implementation and evidence

- `backend/core/tests/test_session_camera_continuation.py` exercises real
  preparation/start/save/continue/finish APIs and authenticated work discovery
  using three simulated camera heartbeats. It verifies recorder-standby
  signals, a fresh slide event on resumed slide 12, teacher-slot release,
  cancellation, stopped/offline workers, and readiness recovery.
- The same backend checks reject new submissions to an ended meeting and
  mismatched old/new session-event pairs. Replaying an already accepted
  ingestion acknowledges its original record, leaving one summary in each
  actual meeting. Old Online heartbeats are rejected after a meeting closes.
- `pipeline/tagad_pipeline/controller.py` retains a closing worker until its
  thread exits and reserves that source during handoff. A continuation waits
  for its previous worker to close. RTSP opening and reading request 10-second
  and 5-second limits through the FFmpeg capture backend.
- Workers check stop signals after a blocking read and around inference so a
  returned frame can be discarded during closure. The first stop reason is
  retained through later controller shutdown. Prepared workers still publish
  readiness heartbeats while their slide-event ID is empty.
- `pipeline/tagad_pipeline/backend_client.py` normalizes socket timeouts and
  connection failures into the existing recoverable backend-error path.
- `pipeline/tests/test_recording_controller.py` drives both controllers through
  prepare, start, save, continuation preparation, continuation start, and end.
  Real PyAV stream-copy jobs use generated synthetic video with input opening
  redirected to the fixture. All six resulting videos decode successfully,
  contain zero audio streams, and belong to two distinct session IDs/folders.
  Earlier video and manifest bytes remain identical after continuation.
- The synthetic fixture also verifies that the installed OpenCV FFmpeg
  backend accepts the configured timeout arguments and reads a local frame.
  Physical acceptance is recorded under C6. Numerical RTSP timeout measurements
  were not supplied with the user's acceptance confirmation.
- Full pipeline discovery passed all 57 checks. Full backend discovery
  completed 286 checks with the five PostgreSQL-only checks skipped by SQLite.
  Their separate PostgreSQL evidence is recorded under C2. Django migration
  and model-drift checks passed. C3 adds zero schema changes.
- Verification used mocked camera/controller failures, simulated heartbeats,
  and generated media. Actual camera connections, model inference, and
  classroom recording are covered by the user's physical acceptance report in C6.

### Prepared-camera handoff correction, November 9, 2026

- Starting an already prepared meeting preserves its camera-health polling and
  last confirmed states. The transition uses the same session and camera
  workers, with fresh health responses continuing to report actual failures.
- A worker announces Online after its first processed frame on each opened
  stream. Camera connection and initial inference readiness happen during
  preparation before Start Session becomes available.
- Controller checks cover reuse of all three workers and the first-frame
  readiness gate. Backend checks preserve the prepared heartbeat records
  across Start. The browser regression delays a health response during Start,
  verifies uninterrupted Online status, then verifies a later Offline update.
- Verification passed 59 pipeline checks, four backend camera-lifecycle checks,
  58 frontend unit checks, the production build, and all 18 browser scenarios.
  Browser fixtures use a fixed key in isolated E2E settings for synthetic
  heartbeats. Production camera credentials remain in local configuration.
- The user reported physical acceptance passed under C6. Numerical startup
  timings were not supplied with that confirmation.

### Startup progress correction, November 9, 2026

- Initial preparation publishes status independently of blocking camera or
  inference work, with updates at most two seconds apart plus request time.
  The website labels the existing Starting state as Preparing. Online still
  requires a successfully processed frame.
- After 60 seconds without initial readiness, the reporter publishes Offline
  with retry guidance. A late successful frame follows the backend's legal
  recovery transitions. Reporter shutdown and heartbeat serialization prevent
  an old Preparing response from replacing Online or Stopped.
- The first decoded frame is processed immediately. Controller discovery and
  status requests have a maximum three-second timeout and recover through their
  regular cycles. Engagement submissions retain their existing retry policy.
- Private controller timing lines measure opening, reading, waiting for shared
  inference, processing, and total initial preparation. Frame-rate reporting
  includes completed processing time. Numerical real-camera latency remains
  unrecorded in this checklist.
- Verification passed 66 pipeline checks, 11 backend camera/readiness checks,
  58 frontend checks, the production build, and the browser handoff scenario.
  Coverage includes blocked inference, repeated Starting updates, a startup
  deadline, recovery, cancellation, first-frame sampling, and failed registration.

## C4 — Teacher-friendly interface and recovery

**Status — Software verified, November 7, 2026.**

- [x] Add the **End Class** dialog and concise explanations for both choices.
- [x] Show **Saving**, **Finishing**, and **Preparing** feedback. Disable
      repeated submissions while each request is pending.
- [x] Add saved-lesson cards with **Continue Lesson**, saved-slide progress,
      subject/classroom, last meeting date, and clear empty/error states.
- [x] Allow confirmed **Finish Lesson** from a saved card when it has zero
      unfinished meetings, including when teaching cameras are unavailable.
- [x] Show the restored slide during continuation preparation and after start.
- [x] After an uncertain response, query the exact lesson and meeting to
      establish the committed action before offering a retry.
- [x] Match recovery to the requested lesson and action. Existing recovery
      helpers currently accept any matching ended meeting or own active
      meeting, so verify their callers before extending them.
- [x] Keep the current presentation visible after an unconfirmed save failure.
      Restore normal controls after the server outcome has been resolved.
- [x] Handle browser refresh, expired login, and another-tab updates using the
      server state and an understandable next action.
- [x] Verify keyboard access, dialog focus, mobile layout, and both themes.

### Error behavior

| Situation | Required behavior |
| --- | --- |
| Network fails before save commits | Keep the current meeting recoverable and offer Retry after reconnecting. |
| Save commits but its response is lost | Recover the exact saved outcome and show Continue Lesson. |
| Finish commits but its response is lost | Recover the exact completed outcome and show the completed meeting. |
| Two tabs try to continue | Resolve both to the same prepared/active meeting or show a clear conflict with a link to it. |
| Save and Finish arrive together | Commit one transition and return its actual state to the other request. |
| A different class is already active | Explain which class must be ended or preparation cancelled. Preserve this saved lesson. |
| Cameras are offline | Show the affected cameras and allow readiness checks to retry while progress remains saved. |
| Prepared continuation is cancelled or expires | Return the lesson to its saved card with the same slide. |
| Saved presentation or slide is unavailable | Explain the affected resource and preserve the lesson for recovery. |
| Teacher or classroom becomes inactive, archived, or reassigned | Revalidate current access and availability before continuation. Preserve existing history. |
| Browser or laptop closes unexpectedly | Recover the persisted meeting state and confirmed slide on reconnect. Require an explicit teacher action to save or finish. |

### Verification gate

- [x] A teacher can complete the acceptance journey through the interface.
- [x] Retry and error states explain what happened and what the teacher can
      do next, without claiming success before the server confirms it.

### C4 implementation and evidence

- `SessionView.vue` adds saved-lesson cards, continuation setup using current
  classroom cameras, confirmed saved-card completion, and persisted-slide
  restoration. `SessionEndDialog.vue` uses a native modal dialog with Save,
  confirmed Finish, and Keep Teaching choices and visible busy/error states.
- Recovery reads the exact meeting and requested action. Unconfirmed actions
  preserve the presentation and lock competing controls until a status check
  resolves the server outcome. Continuations match their lesson and request key.
- The owned-session query restores an administrator's own current meeting
  independently of organization-wide history pagination. Polling rechecks the
  exact meeting for other-tab changes and restores its accepted slide/revision.
- Browser journeys verify save, refresh, continuation preparation, cancellation,
  another-tab start/navigation/save, a committed Save with a lost response,
  saved-card Finish, and a failed Save with an unavailable recovery read.
  Expired browser cookies require sign-in and restore the same ongoing class.
- Desktop light and 390px mobile dark screenshots were inspected. Keyboard
  checks cover modal focus, focus return, blocked background slide shortcuts,
  and Escape while an outcome remains unconfirmed. Mobile has no page overflow.
- Browser verification uses isolated SQLite/media, generated PDF slides, and
  simulator-only meetings. Physical camera acceptance remains in C6.

## C5 — History, analytics, and reports

**Status — Software verified, November 7, 2026.**

- [x] Show linked meetings in teaching order with their dates and saved/finished
      outcome, while retaining access to each meeting's analytics.
- [x] Calculate meeting and slide durations only inside their meeting's start
      and end boundaries. Exclude the interval between class meetings.
- [x] Attribute a revisited slide to its actual visit events within each meeting.
- [x] Keep engagement summaries, alerts, recordings, and exported reports tied
      to their session IDs and slide events.
- [x] Make dashboard, history, and report wording distinguish a closed class
      meeting from a lesson that is **Saved for Later** or **Completed**.
- [x] Protect presentation/history lifecycle operations that would leave a
      resumable lesson with unavailable dependencies.

### Verification gate

- [x] Two 40-minute meetings on different days each report 40 minutes, and
      their displayed slide durations exclude the overnight interval.
- [x] Earlier analytics and reports remain attributable to their original
      meeting after continuation, slide review, and final completion.

### C5 implementation and evidence

- Saved cards and session records open paginated lesson history in teaching
  order. Every meeting retains its date, ID, outcome, predecessor, and analytics
  link. An exact analytics link retrieves its meeting even outside the visible
  options page. Inaccessible IDs show an error without selecting another class.
- Dashboard, analytics, history, and reports label a meeting's saved/finished
  outcome separately from the lesson's current state. Dashboard history reuses
  organization-scoped access, including the lesson's original organization.
- Analytics clips each visit to the meeting's boundaries and sums actual
  revisits. The overnight fixture verifies two 40-minute meetings, 25 minutes
  across two visits to slide 1, and 15 minutes on slide 2 in the first meeting.
  Engagement results remain 3 detections in the first class and 5 in the second.
- CSV keeps its existing column order and appends meeting/lesson identity,
  outcome, state, and predecessor. PDF headers identify their meeting and
  lesson on every page. Both pages of a generated synthetic PDF were rendered
  and visually inspected. Report download names include their meeting ID.
- Stored PDF/CSV downloads remain byte-identical after continuation and final
  completion. Regenerating reports uses the selected meeting's events and
  reports the lesson state at generation time. Earlier meeting outcomes stay
  unchanged when the lesson later becomes completed.
- Existing dependency/archive protections from C2 remain enforced. C3's session
  and event identity checks keep recordings, late submissions, and accepted
  ingestion replays attributed to their actual meeting.

## C6 — Verification and completion evidence

**Status — Passed as reported by the user, November 9, 2026.**

### Software verification

- [x] Add focused backend checks for lifecycle transitions, ownership,
      persistence, migration compatibility, cancellation, and expiry.
- [x] Check duplicate and competing requests against database guarantees.
      Use PostgreSQL for concurrency behavior that SQLite cannot establish.
- [x] Add frontend checks for dialog choices, exact-action recovery, restored
      slide, busy/error states, and refresh/another-tab behavior.
- [x] Check analytics and exports using meetings separated by an overnight gap.
- [x] Run the relevant existing suites and frontend production build.
- [x] Record commands, outcomes, and remaining failures as completion evidence.

### C4–C5 regression evidence

- `backend/venv/Scripts/python.exe backend/manage.py test core.tests
  --settings=tagad.test_settings --noinput --verbosity 0` completed 291 checks.
  SQLite skipped the five PostgreSQL-only concurrency checks. Their PostgreSQL
  results are recorded under C2, and C4–C5 add zero schema changes.
- From `frontend`, `npm test` passed all 58 unit checks and `npm run build`
  passed. Vite retains the existing large-chunk advisory for the main bundle,
  now approximately 544 kB before gzip.
- From `frontend`, `node scripts/run-e2e.mjs` rebuilt the isolated SQLite/media
  fixtures and passed all 17 Playwright scenarios in 2.9 minutes. Existing
  browser selectors were updated for current field labels, administrator
  navigation, and exact link/text matching. The final run has zero failed tests.
- The browser checks cover both ordinary prepare/start/finish/report/archive
  behavior and the continuation/recovery journey. They also verify direct
  analytics links outside the visible options page and reject inaccessible IDs.
- From `pipeline`, `.venv/Scripts/python.exe -m unittest discover -s tests`
  passed all 57 software checks. Django `check`, `makemigrations --check
  --dry-run`, `migrate --check`, and `git diff --check` passed.
- Generated slides, simulated camera/controller state, isolated test storage,
  and rendered synthetic reports provide software evidence. The local
  application database, real camera streams, and classroom recordings were
  outside this verification run. Physical acceptance remains below.

### Physical acceptance reported passed, November 9, 2026

- [x] Measure initial preparation readiness and confirm starting the prepared
      meeting preserves camera processing and health without reopening streams.
- [x] Save during a real three-camera meeting and verify processing and
      recording close for that meeting.
- [x] Restart TAGAD, continue the lesson, and verify the saved slide, camera
      readiness, new recording files, and correct engagement attribution.
- [x] Open both meetings' videos and reports to verify their separation.
- [x] Confirm an unavailable camera leaves progress recoverable.

The user confirmed that C6 succeeded. The physical items above are recorded
from that stage-level confirmation. Session IDs, numerical startup timings,
recording manifests, and exported reports were not supplied for independent
inspection in this chat. No additional physical run was performed while
recording this result.

## Goal sequence

**C1 — Lifecycle contract**, **C2 — Persistence and backend**, **C3 — Software
camera lifecycle**, **C4 — Teacher interface**, and **C5 — History and analytics**
are implemented. **C6 — Verification and completion evidence** is complete
based on the recorded software results and the user's physical acceptance
confirmation on November 9, 2026.

Suggested software goal text follows.

> Implement teacher-owned Save & Continue Later and Finish Lesson actions,
> durable lesson progress, and linked class meetings that resume at the saved
> slide. Preserve organization isolation, accurate meeting analytics, and the
> automatic camera/recording lifecycle. Verify recovery, repeated requests,
> permissions, migration compatibility, and the teacher interface through
> software checks, with physical acceptance tracked separately in C6.

The C2 backend is migrated, and C3–C5 software integration is verified.
Physical three-camera acceptance was reported passed under C6 on November 9, 2026.
