# TAGAD System Reliability Roadmap

Last updated: September 24, 2026

This roadmap tracks application reliability separately from
`engagement-pipeline-stages.md`. Reliability stages use the `R` prefix so
they are not confused with the computer-vision pipeline stages.

Detailed R7 progress is tracked in
[`PIPELINE_INTEGRATION_CHECKLIST.md`](PIPELINE_INTEGRATION_CHECKLIST.md).
The current hardware-independent orchestration goal is tracked in
[`OFFLINE_CAMERA_ORCHESTRATION_CHECKLIST.md`](OFFLINE_CAMERA_ORCHESTRATION_CHECKLIST.md).

## Tracking rules

- Work on one reliability stage at a time.
- Do not mark a stage complete until its automated and manual verification
  gates both pass.
- Each implementation follows the engineering loop: reproduce or define the
  expected behavior, add regression tests, implement the smallest change, run
  targeted tests, run full tests and the production build, inspect the diff,
  and complete manual verification.
- Preserve unrelated work already present in the repository.
- CAPTCHA, two-factor authentication, and OAuth are explicitly deferred until
  deployment is close.

## Current status

| Stage | Name | Status |
| --- | --- | --- |
| R0 | Functional application baseline | Complete |
| R1 | Session reliability and recovery | Complete |
| R2 | Presentation lifecycle reliability | Complete |
| R3 | Real browser workflow testing | Complete |
| R4 | Authentication abuse protection | Complete |
| R5 | Operational health and diagnostics | Complete |
| R6 | Data lifecycle and scaling | Complete |
| R6.1 | Scalable configuration pickers | Complete |
| R6.2 | Safe administration and record lifecycle | Complete and verified |
| R6.3 | Validation and UX hardening | Complete and verified |
| R7 | Computer-vision pipeline handoff | In progress — offline three-camera orchestration built |
| R7.1 | Analytics trustworthiness | Complete and verified |
| R8 | Deployment hardening | Deferred until deployment is close |

## R0 — Functional application baseline

**Status: Complete and manually verified.**

### Completed scope

- [x] Registration, login, logout, protected routes, and Django Admin access.
- [x] Password hashing, password policy, password recovery, and password change.
- [x] Role-based user and organization management.
- [x] Classroom, subject, and camera CRUD operations.
- [x] Atomic Quick Setup for a classroom, multiple cameras, and first subject.
- [x] PDF and PPTX upload, conversion, preview, and generated slides.
- [x] Classroom-session creation, slide navigation, camera linking, and ending.
- [x] Automatic active-camera selection and visible live-session camera status.
- [x] Dashboard, global search, system logs, settings, themes, analytics, CSV,
      and polished PDF reports.
- [x] Stage 1 engagement ingestion contract, simulator, alerts, and WebSockets.
- [x] Model-path readiness foundation without loading model artifacts.

### Last known automated gate

- [x] Django suite: 161 tests passing.
- [x] Frontend suite: 15 tests passing.
- [x] Frontend production build passing.
- [x] No pending Django model migrations.

## R1 — Session reliability and recovery

**Status: Complete and manually verified.**

### Objective

Make the teacher's active session recover safely from accidental actions,
refreshes, duplicate requests, and temporary network failures.

### Checklist

- [x] Add a clear confirmation before ending a session.
- [x] Make the end-session endpoint idempotent.
- [x] Recover correctly when the server ended a session but the response was
      lost.
- [x] Resume the active session after a browser refresh.
- [x] Restore the saved current slide and linked cameras after refresh.
- [x] Prevent duplicate start, slide-change, and end actions.
- [x] Improve WebSocket reconnecting, connected, and unavailable feedback.
- [x] Keep simulator-only sessions supported.
- [x] Add backend and frontend regression tests.

### Verification gate

- [x] Refreshing during a session restores the correct slide and cameras.
- [x] Repeating End Session returns the same completed session safely.
- [x] A lost or delayed end response does not strand the teacher in live mode.
- [x] Accidental End Session clicks can be cancelled.
- [x] Targeted tests, full suites, production build, and diff checks pass.
- [x] Manual testing is accepted.

## R2 — Presentation lifecycle reliability

**Status: Complete and manually verified.**

### Objective

Make uploads and conversion failures manageable without database or file-storage
clutter.

### Checklist

- [x] Add a complete presentation-library management panel.
- [x] Allow failed and unused presentations to be deleted from the frontend.
- [x] Allow failed conversions to be retried safely.
- [x] Prevent duplicate upload submissions.
- [x] Show useful upload and processing progress.
- [x] Keep original, preview, and slide-file cleanup consistent.
- [x] Add keyboard arrow navigation and fullscreen projector mode to live
      presentations.
- [x] Decide whether PPTX conversion must move out of the HTTP request before
      deployment; the current conversion request may run for up to 120 seconds.
- [x] Add failure, retry, deletion, and permission tests.

### Conversion execution decision

Keep conversion synchronous during local development because it is simpler to
operate and the UI now distinguishes file upload from slide generation. Recheck
this decision before deployment: move conversion to a background worker when
concurrent users are introduced or measured conversions regularly exceed ten
seconds. The existing 120-second converter timeout is not a production latency
target.

### Verification gate

- [x] PDF and PPTX success paths work.
- [x] Missing converter, corrupt file, oversized file, and timeout paths recover.
- [x] Retry does not produce duplicate slides or orphaned files.
- [x] Deleting an eligible presentation removes all associated files.
- [x] Presentations used by sessions remain protected.
- [x] Automated tests and the production build pass.
- [x] Keyboard navigation and fullscreen mode are manually accepted.
- [x] Presentation upload, retry, and deletion are manually accepted.

## R3 — Real browser workflow testing

**Status: Complete.**

### Objective

Test the rendered Vue application against Django instead of relying primarily
on source-level frontend smoke checks.

### Checklist

- [x] Add a browser-testing framework and isolated test configuration.
- [x] Test registration, login, logout, and password recovery navigation.
- [x] Test administrator Quick Setup and user management.
- [x] Test teacher upload, session, simulator, analytics, report, and logout.
- [x] Test page refresh during an active session.
- [x] Test permission-denied navigation for every role.
- [x] Capture useful failure output without storing sensitive screenshots.

### Verification gate

- [x] One command runs the critical browser journey reliably from a clean test
      database.
- [x] Tests do not depend on personal accounts or development data.
- [x] Repeated runs produce the same result.

## R4 — Authentication abuse protection

**Status: Complete.**

### Objective

Protect existing authentication endpoints without adding the explicitly
deferred authentication features.

### Checklist

- [x] Rate-limit login attempts by a safe combination of account and client.
- [x] Rate-limit password-reset requests.
- [x] Preserve generic responses that do not reveal whether an email exists.
- [x] Log security-relevant throttling events without logging passwords or
      reset tokens.
- [x] Document lockout duration and administrator recovery behavior.
- [x] Add abuse, recovery, and organization-isolation tests.

### Verification gate

- [x] All 13 focused authentication-throttling tests pass.
- [x] All 188 backend tests pass with no Django system-check issues or pending
      model changes.
- [x] All 12 real-browser workflow tests pass, including login and
      password-reset throttling.
- [x] The frontend production build succeeds.

### Explicitly deferred

- [ ] CAPTCHA — revisit near deployment.
- [ ] Two-factor authentication — revisit near deployment.
- [ ] OAuth — revisit near deployment.

## R5 — Operational health and diagnostics

**Status: Complete.**

### Objective

Make failures identifiable and recoverable without inspecting source code.

### Checklist

- [x] Add a health/readiness check for Django, PostgreSQL, file storage, the
      presentation converter, and the WebSocket layer.
- [x] Add structured application logging with safe retention.
- [x] Assign request/correlation IDs to unexpected server failures.
- [x] Return useful user-facing errors while keeping sensitive details out of
      responses.
- [x] Document startup, shutdown, common failures, and recovery commands.
- [x] Document and rehearse database backup and restoration.

### Verification gate

- [x] An operator can identify a failed dependency from one health report.
- [x] An unexpected error can be traced without exposing credentials or student
      data.
- [x] A test backup can be restored successfully.

## R6 — Data lifecycle and scaling

**Status: Complete and verified.**

### Objective

Keep the application responsive and its stored data intentional as usage grows.

### Checklist

- [x] Define retention rules for presentations, generated slides, reports,
      engagement summaries, and system logs.
- [x] Add safe cleanup commands with dry-run behavior.
- [x] Paginate growing presentation, session, report, classroom, subject, camera,
      and user lists, including the Live Session subject selector and
      recent-session panel.
- [x] Measure query behavior and add no speculative indexes; current evidence
      identified relationship-loading issues instead.
- [x] Test organization isolation across paginated and filtered results.
- [x] Verify file cleanup does not remove records still referenced by sessions.

### Verification gate

- [x] Cleanup reports exact targets before deletion and preserves referenced
      records.
- [x] A 120-record regression fixture keeps paged lists below one second in the
      test environment with bounded query counts.
- [x] Query counts and response times are measured before and after changes;
      results and limitations are recorded in `OPERATIONS.md`.

### Final verification

- [x] Real-browser checks browse forward and backward through Users, Classrooms,
      Subjects, Cameras, Live Session subjects, Presentations, Recent Sessions,
      Analytics, and Reports; active user and class-management searches reset
      their lists to the first page.
- [x] Run `python manage.py cleanup_data`, review every reported ID, and confirm
      the command says that no records or files were deleted.

## R6.1 — Scalable configuration pickers

**Status: Complete and verified.**

### Objective

Keep administrative forms usable without downloading every organization,
classroom, or teacher into the browser.

### Checklist

- [x] Add one paginated, server-searchable configuration lookup API.
- [x] Scope organization, classroom, and teacher choices by administrator role.
- [x] Keep a selected edit value available when it is outside the first page.
- [x] Replace class-management and user-management bulk dropdowns with a shared
      searchable picker.
- [x] Filter teacher choices to the selected classroom or organization.
- [x] Add empty, loading, request-error, and previous/next states.
- [x] Add backend, frontend, and real-browser regression coverage.

### Verification gate

- [x] A 22-record fixture can select classrooms and teachers beyond page one.
- [x] Organization Administrators cannot search another organization's records.
- [x] Existing Quick Setup and user-creation workflows still pass.
- [x] All automated suites, production build, migration, and diff checks pass.

## R6.2 — Safe administration and record lifecycle

**Status: Complete and verified.**

### Objective

Preserve historical classroom evidence while giving administrators safe,
reversible controls for records that should no longer be used.

### Checklist

- [x] Deactivate and reactivate accounts without deleting their history.
- [x] Invalidate existing login sessions after account or organization
      deactivation.
- [x] Prevent self-deactivation, loss of the final System Administrator, and
      deactivation while a teacher owns an active classroom session.
- [x] Archive and restore organizations, classrooms, subjects, cameras, used
      presentations, and completed classroom sessions.
- [x] Block archival while an affected classroom session is ongoing.
- [x] Hide archived records from ordinary lists, selectors, search, dashboards,
      reporting choices, and pipeline work discovery.
- [x] Provide Active, Archived, and All filters in the administrative pages.
- [x] Keep permanent deletion for unused presentations and generated reports.
- [x] Preserve completed sessions, analytics, reports, and presentation files
      when referenced records are archived.
- [x] Reject archived records and deactivated teachers during new
      configuration and session creation.
- [x] Audit archive, restore, account lifecycle, and intentional deletion
      operations.

### Privacy boundary

TAGAD does not persist classroom video, audio, individual frames, face crops,
facial landmarks, biometric embeddings, or temporary tracking identifiers.
Only aggregate monitoring results and operational metadata are retained.

### Verification gate

- [x] Backend lifecycle, authorization, organization-isolation, file cleanup,
      history-preservation, and session-invalidation tests pass.
- [x] Browser tests cover account deactivation/reactivation, subject
      archive/restore, used-presentation archive/restore, completed-session
      archive/restore, and generated-report deletion.
- [x] Full automated suites, production build, migration check, preflight, and
      diff review pass.

## R6.3 — Validation and UX hardening

**Status: Complete and verified.**

### Objective

Reject invalid administrative data consistently, preserve form input after a
failed request, and give operators a specific correction instead of a generic
failure message.

### Checklist

- [x] Normalize organization, classroom, and subject codes to uppercase.
- [x] Enforce case-insensitive database uniqueness for organization,
      classroom, and subject codes.
- [x] Validate code characters, contact-number formats, email formats, field
      lengths, required values, and classroom capacity limits in Django.
- [x] Apply the same rules to registration, account settings, user management,
      individual class-management forms, and Quick Setup.
- [x] Keep lifecycle, permission, organization-isolation, and active-record
      validation enforced by the backend.
- [x] Return the first useful validation message while retaining structured
      field errors for inline display.
- [x] Add missing inline errors and browser limits to administrative forms.
- [x] Prevent repeated submissions while create, edit, upload, authentication,
      recovery, or settings requests are pending.
- [x] Preserve entered form values after validation failures.
- [x] Keep existing loading, empty, error, and permission-denied states.

### Verification gate

- [x] Backend tests cover normalization, invalid formats, bounds, settings,
      Quick Setup, and case-insensitive database constraints.
- [x] Frontend tests cover useful API validation messages, field errors,
      browser limits, and duplicate-submit guards.
- [x] A real-browser test rejects an invalid contact number, keeps entered
      values, accepts the corrected value, and verifies code normalization.
- [x] Full automated suites, production build, migration check, preflight, and
      diff review pass.

## R7 — Computer-vision pipeline handoff

**Status: In progress — offline three-camera orchestration is integrated; live hardware remains.**

### Entry requirements

- [x] Confirmed-track filtering and explicit unclassified handling pass offline
      testing.
- [ ] Realistic classroom latency and classification-success metrics exist.
- [x] The four selected artifacts and their checksums are frozen for integration.

### Planned scope

- [x] Correct Django configuration from one SVM artifact to separate rich-state
      and DIPSER-attention artifacts.
- [x] Validate the exact 25-feature and 10-feature column orders.
- [x] Encode and test the final two-SVM decision mapping.
- [x] Run inference in a dedicated worker, never inside a normal Django request.
- [x] Submit aggregated results through the existing Stage 1 API.
- [x] Display worker and camera health without exposing credentials.
- [x] Prevent simulator and pipeline summaries from mixing in a new session,
      and label analytics provenance for new and historical sessions.
- [x] Provide one-command Windows preflight, startup, status, and graceful
      controller shutdown for the prepared pilot computer.
- [ ] Validate the RTSP source and latency with the selected classroom hardware.
- [x] Extend the baseline to three isolated simulated camera sources.

## R7.1 — Analytics trustworthiness

**Status: Complete and verified.**

### Objective

Make the evidence behind analytics visible so teachers do not mistake sparse,
unclassified, simulated, or historically mixed results for validated classroom
conclusions.

### Checklist

- [x] Display unclassified detections and classified coverage in Analytics.
- [x] Assign Good, Limited, or Insufficient evidence-quality labels using
      documented thresholds.
- [x] Withhold insights and recommendations when evidence is Insufficient.
- [x] Compare engagement only with an older session for the same subject and
      the same clean source type.
- [x] Mark simulator and historically mixed data as not official.
- [x] Include source, model versions, quality, windows, coverage, and
      unclassified counts in PDF and CSV reports.
- [x] Add backend, frontend, and real-browser regression tests.

### Evidence-quality rules

These labels measure evidence completeness, not whether the model's predictions
are correct. Model accuracy still requires human ground truth.

- **Good:** at least 20 monitoring windows, at least 75% classified coverage,
  average confidence of at least 70%, and one clean data source.
- **Limited:** at least 5 monitoring windows, at least 50% classified coverage,
  and one clean data source, but the Good threshold is not met.
- **Insufficient:** fewer than 5 monitoring windows, less than 50% classified
  coverage, no data, or mixed simulator and pipeline data.

### Verification gate

- [x] Backend analytics and report tests cover Good, Limited, Insufficient,
      simulator, mixed-source, unclassified, and compatible-comparison cases.
- [x] Analytics displays provenance and quality without hiding unclassified
      results.
- [x] PDF and CSV exports preserve the same provenance and quality context.
- [x] Full backend, frontend, pipeline, browser, build, migration, preflight,
      and diff checks pass.

## R8 — Deployment hardening

**Status: Deferred until deployment is close.**

### Checklist

- [ ] Separate development and production settings.
- [ ] Configure a strong production secret, `ALLOWED_HOSTS`, trusted origins,
      HTTPS redirect, secure cookies, and HSTS after HTTPS is verified.
- [ ] Set `DEBUG=False` and run `manage.py check --deploy` without unresolved
      warnings.
- [ ] Replace the in-memory Channels layer with a production-capable shared
      channel layer when multiple processes are used.
- [ ] Configure production email delivery and file storage.
- [ ] Complete deployment, rollback, monitoring, and disaster-recovery tests.
- [ ] Re-evaluate CAPTCHA, two-factor authentication, and OAuth based on the
      deployment environment and project requirements.

## Immediate next action

Complete the **R7 model-quality review** with human ground truth and a
representative continuous classroom recording when one becomes available.
R7.1 now prevents incomplete or simulated evidence from appearing as an
unqualified conclusion, but it does not prove classification accuracy. The
three-camera CUDA pipeline has passed a 60-minute looped stability test. After
physical cameras are selected, validate one RTSP stream and its placement before
enabling live classroom use. CAPTCHA, two-factor authentication, OAuth, and R8
remain deferred until deployment is close.
