# TAGAD System Reliability Roadmap

Last updated: September 15, 2026

This roadmap tracks application reliability separately from
`docs/engagement-pipeline-stages.md`. Reliability stages use the `R` prefix so
they are not confused with the computer-vision pipeline stages.

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
| R5 | Operational health and diagnostics | Next |
| R6 | Data lifecycle and scaling | Planned |
| R7 | Computer-vision pipeline handoff | Deferred until pipeline is ready |
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
- [x] All 10 real-browser workflow tests pass, including login and
      password-reset throttling.
- [x] The frontend production build succeeds.

### Explicitly deferred

- [ ] CAPTCHA — revisit near deployment.
- [ ] Two-factor authentication — revisit near deployment.
- [ ] OAuth — revisit near deployment.

## R5 — Operational health and diagnostics

**Status: Planned.**

### Objective

Make failures identifiable and recoverable without inspecting source code.

### Checklist

- [ ] Add a health/readiness check for Django, PostgreSQL, file storage, the
      presentation converter, and the WebSocket layer.
- [ ] Add structured application logging with safe retention.
- [ ] Assign request/correlation IDs to unexpected server failures.
- [ ] Return useful user-facing errors while keeping sensitive details out of
      responses.
- [ ] Document startup, shutdown, common failures, and recovery commands.
- [ ] Document and rehearse database backup and restoration.

### Verification gate

- [ ] An operator can identify a failed dependency from one health report.
- [ ] An unexpected error can be traced without exposing credentials or student
      data.
- [ ] A test backup can be restored successfully.

## R6 — Data lifecycle and scaling

**Status: Planned.**

### Objective

Keep the application responsive and its stored data intentional as usage grows.

### Checklist

- [ ] Define retention rules for presentations, generated slides, reports,
      engagement summaries, and system logs.
- [ ] Add safe cleanup commands with dry-run behavior.
- [ ] Paginate growing presentation, session, report, classroom, and user lists.
- [ ] Add database indexes only where measured queries require them.
- [ ] Test organization isolation across paginated and filtered results.
- [ ] Verify file cleanup does not remove records still referenced by sessions.

### Verification gate

- [ ] Cleanup reports exact targets before deletion and preserves referenced
      records.
- [ ] Large seeded lists remain responsive.
- [ ] Query counts and response times are measured before and after changes.

## R7 — Computer-vision pipeline handoff

**Status: Deferred until the offline pipeline is ready.**

### Entry requirements

- [ ] Confirmed-track filtering and explicit unclassified handling pass offline
      testing.
- [ ] Realistic classroom latency and classification-success metrics exist.
- [ ] The four selected artifacts and their checksums are frozen for integration.

### Planned scope

- [ ] Correct Django configuration from one SVM artifact to separate rich-state
      and DIPSER-attention artifacts.
- [ ] Validate the exact 25-feature and 10-feature column orders.
- [ ] Encode and test the final two-SVM decision mapping.
- [ ] Run inference in a dedicated worker, never inside a normal Django request.
- [ ] Submit aggregated results through the existing Stage 1 API.
- [ ] Display worker and camera health without exposing credentials.

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

Begin **R5 — Operational health and diagnostics** by defining one safe health
report for Django and its required dependencies. CAPTCHA, two-factor
authentication, and OAuth remain deferred.
