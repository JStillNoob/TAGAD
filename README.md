# TAGAD

TAGAD is a desktop web application for managing classrooms, presentations,
monitoring sessions, engagement analytics, and reports. The Vue frontend and
Django backend are separate development servers and both must be running.

## Requirements

- Python 3.11+
- Node.js 20+
- PostgreSQL
- LibreOffice or Microsoft PowerPoint for PPTX-to-PDF conversion

Startup, health checks, structured-log troubleshooting, and safe PostgreSQL
backup/recovery procedures are documented in [the operations guide](docs/OPERATIONS.md).
See the [documentation index](docs/README.md) for checklists, pipeline reports,
hardware guidance, and project roadmaps.

## 1. Configure PostgreSQL

Create an empty PostgreSQL database and a database user with access to it. From
the repository root, create the private backend environment file:

```powershell
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env` and set `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
`DB_HOST`, and `DB_PORT`. The example documents every supported setting. Never
commit `.env` or real credentials.

The frontend does not currently need its own `.env`: Vite proxies `/api` and
`/admin` and `/ws` to Django using `frontend/vite.config.js`.

For local engagement-pipeline testing, set
`ENABLE_PIPELINE_SIMULATOR=True`. Keep it `False` outside development. The
external AI worker sends a long private `PIPELINE_API_KEY` through the
`X-Pipeline-Key` header; this key must never be placed in frontend code.

You can generate a worker key in PowerShell without an online service:

```powershell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
[Convert]::ToHexString($bytes)
```

Copy the printed value into `PIPELINE_API_KEY` in `backend\.env`. Leave the
setting empty when no external pipeline worker is connected; the ingestion API
then fails closed. The built-in simulator does not require or expose this key.

### Authentication abuse protection

TAGAD limits repeated authentication requests using hashed identity/client keys
in Django's cache. The default policy allows five failed sign-in attempts per
identity/client pair in 15 minutes, with a broader ceiling of 25 failures per
client. Password recovery allows three requests per email/client pair, with a
broader ceiling of 15 requests per client. Restrictions expire after 15 minutes.

A successful sign-in before restriction clears that identity/client failure
state. Once restricted, the account remains active and no database flag needs
to be changed: the user must wait for the displayed period. Administrators
should verify that the account itself is active but should not deactivate,
recreate, or change its role to resolve a temporary restriction.

The local default cache is process-local and is suitable for one Django process.
Configure a shared production cache such as Redis before running multiple
backend processes, otherwise each process maintains separate counters.

Forwarded client addresses are ignored by default. Set `TRUSTED_PROXY_COUNT`
only when Django is behind that exact number of trusted reverse proxies; an
incorrect value can make client-based limits unreliable. All limits and windows
are documented in `backend\.env.example` and can be adjusted there per
environment. CAPTCHA, two-factor authentication, and OAuth remain deferred.

### Model artifact configuration

The integrated worker expects the four frozen model files in the ignored
`backend/model_artifacts/` directory by default. Paths may be overridden in
`backend\.env`; never commit trained weights to Git:

```env
TAGAD_YOLO_MODEL_PATH=model_artifacts/tagad_yolo11_head_v2_best.pt
TAGAD_FACE_LANDMARKER_PATH=model_artifacts/face_landmarker.task
TAGAD_STATE_MODEL_PATH=model_artifacts/tagad_state_svm_rich_threshold1_candidate.joblib
TAGAD_ATTENTION_MODEL_PATH=model_artifacts/dipser_attention_10-feature_diagnostic.joblib
TAGAD_MODEL_PIPELINE_VERSION=hierarchical-1
```

After all downloads and training finish, verify the paths without loading the
models or importing the machine-learning libraries:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py check_model_setup
```

The dedicated workers in `pipeline/` verify artifact checksums, implement the
two-SVM hierarchy, and submit camera-attributed Stage 1 aggregates. The offline
controller discovers active sessions and manages isolated Front, Left, and
Right simulated sources; Front alone publishes official engagement while the
side views remain diagnostics. An
obstructed face or failed landmark extraction uses `label=None`, which is
counted as unclassified rather than disengaged. See
[`pipeline/README.md`](pipeline/README.md) for its offline and live commands.

## 2. Install and prepare the backend

```powershell
cd backend
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
```

Create a system administrator when needed:

```powershell
.\venv\Scripts\python.exe manage.py createsuperuser
```

Afterward, open Django Admin, edit the new user, and set its TAGAD role to
`System Administrator`. Django's superuser flag and TAGAD's role are separate.

## 3. Install the frontend

Open a second PowerShell window at the repository root:

```powershell
cd frontend
npm install
```

## 4. Run TAGAD

Backend terminal:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py runserver
```

Frontend terminal:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`. Django Admin is available through the frontend at
`http://localhost:5173/admin/` or directly at `http://127.0.0.1:8000/admin/`.

## Optional demo workspace

The following repeatable command creates one demo organization, administrator,
teacher, classroom, subject, and camera configuration. It does not delete
existing data. Choose a private password that satisfies the displayed policy:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py seed_demo --password "YOUR-PRIVATE-DEMO-PASSWORD"
```

Sign in with `demo.admin` or `demo.teacher` and the password you supplied. Do
not use demo accounts or shared passwords in production.

## Verification

Backend:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py test --settings=tagad.test_settings
```

The test settings use a temporary in-memory database. They never modify the
development PostgreSQL database and do not require PostgreSQL `CREATEDB`
permission.

Frontend:

```powershell
cd frontend
npm test
npm run build
```

Real-browser workflow tests use Chromium, ports 4173 and 8001, and a dedicated
SQLite database under `backend\.e2e`. They do not read or modify the development
PostgreSQL database or personal accounts. Install the browser once, then run the
entire journey with one command:

```powershell
cd frontend
npm run test:e2e:install
npm run test:e2e
```

Each run deletes and rebuilds only the isolated E2E directory, applies all
migrations, creates synthetic accounts, starts both test servers, and runs the
authentication, administration, teacher-session, refresh, reporting, and role
permission journeys.

## Common problems

- `ModuleNotFoundError`: run commands with `backend\venv\Scripts\python.exe`
  and install `requirements.txt`.
- `ECONNREFUSED 127.0.0.1:8000`: Django is not running. Start the backend.
- `Port 5173 is already in use`: an existing frontend server is already running;
  use that instance or stop it before starting another.
- PostgreSQL connection errors: verify PostgreSQL is running and the values in
  `backend\.env` match the database.
- PPTX conversion errors: install LibreOffice or Microsoft PowerPoint and, when
  necessary, set `LIBREOFFICE_PATH` in `backend\.env`.
