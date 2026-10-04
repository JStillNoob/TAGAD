# TAGAD Operations Guide

This guide covers local startup, health checks, diagnostics, backup, and safe
recovery. Commands assume PowerShell from the repository root.

## Start and stop

Confirm PostgreSQL is running:

```powershell
Get-Service *postgres*
```

For the prepared development computer, run the preflight and all three TAGAD
services—Django, Vite, and the camera controller—with one command from the
repository root:

```powershell
.\scripts\tagad.ps1 start
```

The command checks pending migrations, the database connection, model files
and checksums, local camera configuration, frontend dependencies, and CUDA. It
loads `PIPELINE_API_KEY` from the ignored `backend\.env` without printing it.
Service output and the PID file are stored in the ignored `.runtime` directory.
Use:

```powershell
.\scripts\tagad.ps1 status
.\scripts\tagad.ps1 stop
```

The stop action first signals the controller to release video files and report
Stopped worker states, then stops Vite and Django. If PowerShell blocks local
scripts, use `powershell -ExecutionPolicy Bypass -File .\scripts\tagad.ps1 start`.

Run the preflight without starting anything with:

```powershell
.\scripts\tagad.ps1 check
```

The manual three-terminal procedure remains available for troubleshooting.

Start Django in the first terminal:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```

Start Vue in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Stop each development server with `Ctrl+C` in
its terminal. Do not close PostgreSQL while Django is writing data.

When using the manual procedure with camera processing, also set
`TAGAD_PIPELINE_API_KEY`, set `PYTHONPATH` to `pipeline`, and start
`pipeline\.venv\Scripts\python.exe -m tagad_pipeline.controller` as documented
in [`../pipeline/README.md`](../pipeline/README.md).

## Health and readiness

Liveness proves Django can answer HTTP requests:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/live/
```

Readiness checks every dependency needed by the current application:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/ready/
```

The readiness endpoint returns HTTP 200 with `status: ready`, or HTTP 503 with
`status: unavailable`. It exposes only these safe component states:

- `django`: request handling is running.
- `postgresql`: a minimal database query succeeds.
- `file_storage`: a temporary probe can be written, found, and removed.
- `presentation_converter`: LibreOffice or registered Microsoft PowerPoint is
  available for PPTX conversion.
- `websocket`: the configured Channels layer completes an isolated round trip.

The report never includes credentials, filesystem paths, exception messages,
account information, or classroom data.

## Request references and logs

Every backend response includes an `X-Request-ID`. Unexpected frontend errors
show this value as a reference. Search for the reference in:

```powershell
Select-String -Path backend\logs\tagad*.log -Pattern "PASTE-REQUEST-ID-HERE"
```

Logs are one JSON object per line. Sensitive key/value patterns are redacted,
request bodies are not logged, and only the URL path—not its query string—is
recorded. Defaults keep five rotated 5 MB files under `backend\logs`; the
directory is excluded from Git. Configure limits with the `LOG_*` entries in
`backend\.env`.

## Common failures

### PostgreSQL reports failed

1. Run `Get-Service *postgres*` and start the installed PostgreSQL service if
   it is stopped.
2. Verify `DB_HOST`, `DB_PORT`, `DB_NAME`, and `DB_USER` in `backend\.env`.
3. Do not paste `DB_PASSWORD` into logs, screenshots, commits, or chat.
4. Run `python manage.py check` from the activated backend environment.

### File storage reports failed

Verify the account running Django can create and delete files under
`backend\media`. Check free disk space. Do not delete presentation files by
hand; use TAGAD's presentation deletion action.

### Presentation converter reports failed

Install LibreOffice or Microsoft PowerPoint. For LibreOffice, optionally set
`LIBREOFFICE_PATH` to the full `soffice.exe` path, restart Django, and check
readiness again.

### WebSocket reports failed

Restart Django and check that the `daphne` and `channels` packages are
installed. The current in-memory layer supports one backend process only; a
multi-process deployment requires a shared production Channels layer.

### Unexpected request fails

Copy the displayed request reference, find it in the structured log, and use
the logged event, path, status, and exception type. The browser should never
show a Python traceback or database error.

## PostgreSQL backup

Create a custom-format backup without placing the database password on the
command line:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py backup_database
```

Backups are written under `backend\backups` and excluded from Git. The command
refuses to overwrite an existing file or write outside that directory. Copy
important backups to encrypted storage with access controls; a local backup on
the same disk is not sufficient disaster recovery.

## Recovery rehearsal

Run the automated rehearsal during a maintenance window:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py rehearse_database_recovery
```

It creates a fresh backup, creates a randomly named
`tagad_restore_test_*` database, restores the backup, verifies Django migration
history, and removes the temporary database even if restoration fails. It
never restores over the active database.

The configured database role needs PostgreSQL `CREATEDB` permission for the
rehearsal. A PostgreSQL administrator may grant it temporarily:

```sql
ALTER ROLE your_tagad_database_user CREATEDB;
```

After a successful rehearsal, the administrator may revoke it:

```sql
ALTER ROLE your_tagad_database_user NOCREATEDB;
```

If policy forbids `CREATEDB`, ask the database administrator to run the
rehearsal with a dedicated recovery role. Do not grant application users
superuser privileges.

## Production restoration procedure

1. Stop application writes and record the incident request IDs.
2. Preserve the damaged database; never restore over it first.
3. Create a separate empty PostgreSQL database using an authorized recovery
   account.
4. Restore the selected custom-format `.dump` into that new database with
   `pg_restore --exit-on-error --no-owner --no-privileges`.
5. Point a maintenance instance of TAGAD at the restored database.
6. Run `python manage.py migrate --check`, the readiness endpoint, and critical
   browser smoke tests.
7. Switch application traffic only after the restored data is approved.
8. Keep the previous database until rollback is no longer required.

Never put database passwords directly in command history. Use an approved
PostgreSQL password file, secret manager, or temporary process environment.

## Data retention and cleanup

TAGAD keeps completed classroom sessions and ready presentations until a user
explicitly removes them. The cleanup command applies only these conservative
defaults:

| Data | Default retention | Cleanup rule |
| --- | ---: | --- |
| Failed presentations and generated slides | 30 days | Only when no session or slide event references them |
| Generated PDF/CSV reports | 365 days | Database row and unshared stored file |
| Engagement summaries | 180 days | Summary rows and their dependent alerts |
| System activity logs | 180 days | Log rows |

Generated slide images have the same lifetime as their presentation. Source
files, converted previews, and slide images for a referenced presentation are
never cleanup targets. A report file is preserved when another retained report
row uses the same storage path.

The values can be changed with the `RETENTION_*_DAYS` entries in
`backend\.env`. Values cannot be negative. Review cleanup targets first:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py cleanup_data
```

Dry-run is the default. It prints every target ID and changes nothing. Before
deleting, make and retain a database backup, review the complete dry-run list,
then execute the same policy explicitly:

```powershell
.\venv\Scripts\python.exe manage.py backup_database
.\venv\Scripts\python.exe manage.py cleanup_data --execute
```

There is no automatic cleanup schedule in development. A production operator
may schedule the command only after backup monitoring and dry-run review are in
place.

## Record lifecycle and privacy

TAGAD uses three different lifecycle actions deliberately:

- **Deactivate** a user account or organization to stop access while preserving
  ownership and audit history.
- **Archive** a classroom, subject, camera, used presentation, or completed
  session to remove it from normal workflows while keeping it restorable.
- **Delete permanently** only an unused presentation or a generated report.

Administrators can switch supported pages between Active, Archived, and All
records. Archived records are excluded from new-session selectors, global
search, dashboard counts, report choices, and camera-controller work. Ongoing
sessions must be ended before any related account or record can be archived.
Restoring a child record requires its parent classroom or organization to be
active. Record codes remain unique while archived so historical references do
not become ambiguous.

Deleting an unused presentation removes its original upload, converted preview,
generated slide images, and database row. A presentation referenced by a
completed session is archived instead. Deleting a generated PDF or CSV removes
only that export; its session and analytics remain available for regeneration.

The runtime pipeline may temporarily hold frames, landmarks, and tracking IDs
in memory, but TAGAD does not persist classroom video, audio, individual frames,
face crops, facial landmarks, biometric embeddings, or temporary tracking
identifiers. Logs and reports must never include camera credentials or raw
biometric material. Stored engagement data consists of aggregate counts,
unclassified counts, confidence, timing, provenance, and operational health.

## List scaling measurements

User, classroom, subject, camera, presentation, classroom-session, report, and
system-log APIs return 20 rows per page by default. The Live Session subject
selector uses a separate paginated endpoint with the same limit. Clients may
request `page` and `page_size`; `page_size` is capped at 100. Search and
role/status/type filters are applied inside the organization-scoped queryset
before pagination.

Dashboard recent activity is intentionally capped at five records and global
search returns only its small result groups; neither endpoint is a general list.
Analytics slide details are scoped to one selected session. Static role, status,
and camera-position choices are finite enumerations. Organization, classroom,
and teacher form choices use the permission-scoped configuration lookup API,
which applies server-side search and returns 20 choices per page while keeping a
selected edit value reachable.

The R6 regression fixture uses 120 presentations, sessions, users, classrooms,
subjects, and reports. On the local SQLite test configuration, a representative
20-session serialization measured 44 queries and 38.49 ms before the
bounded-query changes. The paginated API measured 7 queries and 15.23 ms;
presentations measured 5 queries and 8.61 ms. Subject and classroom totals use
database-side aggregate counts rather than loading every related row. Timings
are diagnostic rather than production capacity claims, while query ceilings are
enforced by automated tests. No new database indexes were added: the
measurements showed relationship-loading problems, not evidence that an index
would improve the current workload. Re-measure with production-like PostgreSQL
volume and `EXPLAIN (ANALYZE, BUFFERS)` before adding indexes.

## Offline camera orchestration

Camera source paths and future RTSP credentials belong only in the ignored
`pipeline\camera_sources.local.json`. Copy the committed example, configure the
three positions, and set `TAGAD_PIPELINE_API_KEY` in the controller process to
the same private value as backend `PIPELINE_API_KEY`. Apply Django migrations
before starting the controller.

The current CPU-safe three-camera target is 2.5 analyses/second per source. A
20-second looping smoke test delivered 2.70–2.73 analyses/second per source,
used one shared model bundle (about 118 MB added at load), peaked near 724 MB
process RSS, and finished near 522 MB. This is evidence for short offline load
operation only, not full-class stability or RTSP readiness.

Front is the sole official analytics source. Left and Right health and counts
are diagnostic and must not be combined. A stale heartbeat is displayed as
Offline after `PIPELINE_HEARTBEAT_TIMEOUT_SECONDS` (10 seconds by default), but
does not end the session or stop another worker. Stop the controller with
Ctrl+C; it reports Stopped and releases each source before closing the shared
models.

The development simulator is allowed only when a session has no assigned
cameras. Once a session receives either simulator results or real pipeline
results, the backend rejects the other source for that session. Analytics marks
results as Pipeline, Development simulation, No source, or Mixed sources. The
Mixed label exists only to identify older contaminated sessions; those totals
must not be treated as official analytics.

## Analytics evidence quality

Analytics and generated reports expose monitoring-window count, unclassified
detections, classified coverage, average confidence, source provenance, and
pipeline versions. Development simulation and historical mixed-source results
are explicitly marked as not official.

Evidence quality uses these fixed rules:

- **Good:** at least 20 monitoring windows, at least 75% classified coverage,
  average confidence of at least 70%, and one clean source.
- **Limited:** at least 5 monitoring windows and at least 50% classified
  coverage from one clean source, without meeting every Good threshold.
- **Insufficient:** fewer than 5 monitoring windows, less than 50% coverage, no
  data, or mixed simulator and pipeline data.

When quality is Insufficient, TAGAD withholds generated insights and
recommendations. Session-to-session engagement comparisons use only an older
session for the same subject and the same clean source type; simulator results
are never compared with pipeline results.

These labels describe the quantity and completeness of evidence. They do not
measure classification accuracy or replace validation against human-labeled
ground truth.
