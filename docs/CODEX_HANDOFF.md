# TAGAD Codex Handoff

Snapshot date: October 4, 2026  
Repository branch: `main`  
Snapshot base commit: `9f448e2`

## Start here

1. Read the repository-root `AGENTS.md` completely before changing anything.
2. Read this file, `README.md`, and `docs/OPERATIONS.md`.
3. Run `git status --short` and preserve any user-owned changes.
4. Define a small, verifiable goal before editing, then test until it passes.
5. Do not start or stop Django, Vite, the camera controller, or another process unless the user explicitly asks. The user operates the running system.
6. Keep progress messages minimal. Report when material work finishes or when user input is genuinely required.

`AGENTS.md` is intentionally local and ignored by Git. If this repository is moved to another computer, copy that file to the repository root separately.

## Project purpose

TAGAD is a classroom engagement monitoring system with:

- a Django and PostgreSQL backend in `backend/`;
- a Vue and Vite frontend in `frontend/`;
- a Python camera inference and orchestration pipeline in `pipeline/`;
- PowerShell operational commands in `scripts/tagad.ps1`.

The pipeline processes camera frames but does not retain student video. Aggregated classifications and operational health are stored for analytics.

## Current hardware and pipeline state

- CUDA preflight passed on the development laptop.
- Three physical TP-Link VIGI C440I cameras have connected successfully over RTSP.
- Front, Left, and Right are official analytics sources and publish camera-attributed summaries.
- Session analytics combine observations from all selected cameras. Overlapping views can still observe the same student more than once until seating zones are calibrated.
- Camera workers operate independently; one failed source must not stop the others.
- Worker states include Starting, Online, Reconnecting, Offline, and Stopped.

Private values belong only in these ignored local files:

- `backend/.env`
- `pipeline/camera_sources.local.json`

Never commit an API key, database password, camera password, credential-bearing RTSP URL, video, model artifact, log, or runtime file. The camera password appeared in the previous account's chat, so it should be rotated and then updated only in the ignored local camera configuration.

## Required session flow

This workflow is intentional and must not be collapsed into a single automatic start action:

1. On the setup view, the teacher chooses the subject/classroom, ready presentation, and cameras.
2. **Prepare Session** creates a prepared session and opens the normal presentation/session screen.
3. On that screen, the teacher can review and navigate the presentation while cameras warm up.
4. During preparation:
   - the timer stays at `00:00:00`;
   - Camera & Worker Health is visible;
   - no session timing, slide events, or analytics are recorded;
   - the action is **Start Session**, not **End Session**.
5. When all selected cameras are Online, the teacher presses **Start Session**.
6. A five-second countdown appears on the same presentation screen.
7. Only after the countdown completes does the backend set `started_at`, create the first slide event, and allow analytics submission.
8. The same screen becomes the active session and displays **End Session**.

There is no attendance feature. Attendance was only an example of something a teacher might do while the prepared screen is open; do not add it to TAGAD.

Primary implementation locations:

- `frontend/src/views/SessionView.vue`
- `frontend/src/sessionReliability.js`
- `frontend/src/sessionCountdown.js`
- `backend/core/session_views.py`
- `backend/core/session_serializers.py`
- `backend/core/session_preparation.py`
- `backend/core/migrations/0013_session_preparation.py`

Relevant endpoints:

- `POST /api/auth/sessions/prepare/`
- `POST /api/auth/sessions/<id>/start/`
- cancel-preparation endpoint defined in `backend/core/urls.py`

Prepared sessions use `prepared_at` with a nullable `started_at`. The controller may preload the assigned camera worker for a prepared session, but the pipeline must not submit engagement analytics until the session has a current slide event.

## Completed system work

- Server-side pagination and search were added to growing lists, including Subjects, Cameras, and Recent Sessions.
- Data lifecycle rules now use archive/restore for historical records and deactivation for accounts.
- An unused presentation may be permanently deleted; a presentation used by session history is archived instead.
- Validation hardening and duplicate-submission protection were added across backend and frontend forms.
- Unknown pipeline results remain `Unclassified`; they are not silently counted as Disengaged.
- Analytics reports data source, classification coverage, confidence, and insufficient-data states.
- Offline three-camera orchestration, worker isolation, health reporting, reconnection behavior, and source separation were implemented.
- One-command preflight/start/status/stop operations were added through `scripts/tagad.ps1`.
- Local model artifacts, recordings, credentials, generated media, logs, virtual environments, and runtime files are excluded from Git.
- Documentation was consolidated under `docs/`, with the root `README.md` retained as the entry point.

## Last recorded verification

At the time of this handoff:

- `npm test` in `frontend/`: 45 tests passed.
- `npm run build` in `frontend/`: production build passed.
- Targeted backend presentation/session suite: 34 tests passed.
- An earlier full backend run in the same workstream: 248 tests passed.
- Pipeline suite in the same workstream: 25 tests passed.
- `git diff --check` reported no patch errors; only Windows line-ending warnings.
- A secret audit found no real camera password, RTSP credential, database password, API key, or private key in pushable files or Git history.
- The working tree was clean at base commit `9f448e2` before this handoff file was added.

Rerun the tests relevant to any new change. Do not claim live browser or camera verification unless the user actually runs the system and confirms it.

## Operating commands

From the repository root:

```powershell
.\scripts\tagad.ps1 check
.\scripts\tagad.ps1 start
.\scripts\tagad.ps1 status
.\scripts\tagad.ps1 stop
```

`start` launches Django, Vite, and the camera controller only after preflight succeeds. Agents must not invoke it without explicit user authorization.

## Recommended next goal

The next useful goal is **Three-Camera Pilot Stability and Calibration**:

1. Run a real three-camera classroom-style session for 60–90 minutes.
2. Confirm preparation, manual start, countdown, slide navigation, end-session shutdown, and analytics generation.
3. Monitor worker FPS, CPU, GPU, and memory for stalls or continuous growth.
4. Disconnect and reconnect the camera network cable and verify Reconnecting to Online recovery.
5. Restart only the controller during a prepared or active session and verify recovery.
6. Compare predicted states against a small human ground-truth worksheet by timestamp.
7. Record false classifications and camera placement/lighting limitations.

Do not retrain or declare the model accurate without representative classroom recordings and ground-truth labels. Calibrate non-overlapping seating zones before claiming unique combined student totals.

## New-account continuation prompt

Use this prompt in the new Codex account:

> Open the TAGAD repository. Read `AGENTS.md` and `docs/CODEX_HANDOFF.md` completely before acting. Inspect `git status`, preserve existing changes, do not start services unless I explicitly ask, and tell me the smallest verified next goal.
