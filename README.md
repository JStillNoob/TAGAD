# TAGAD

TAGAD is a desktop web application for managing classrooms, presentations,
monitoring sessions, engagement analytics, and reports. The Vue frontend and
Django backend are separate development servers and both must be running.

## Requirements

- Python 3.11+
- Node.js 20+
- PostgreSQL
- LibreOffice or Microsoft PowerPoint for PPTX-to-PDF conversion

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
`ENABLE_PIPELINE_SIMULATOR=True`. Keep it `False` outside development. A future
external AI worker must send a long private `PIPELINE_API_KEY` through the
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
