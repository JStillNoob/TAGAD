# TAGAD Superadmin Setup Guide

This guide creates a new **Django superuser** and assigns the separate TAGAD
**System Administrator** role. Both are required for full access:

- Django's `is_staff` and `is_superuser` flags allow access to Django Admin.
- TAGAD's `system_admin` role allows system-wide access in the TAGAD frontend.

Do not share superadmin credentials with other users. Create a separate account for
each administrator.

## Prerequisites

Install the following before continuing:

- Python 3.11
- PostgreSQL
- Git

The PostgreSQL database must exist and `backend/.env` must contain working database
credentials. If `.env` does not exist, copy `backend/.env.example` to
`backend/.env`, then replace its placeholder values. Never commit or share `.env`.

## 1. Open PowerShell in the backend directory

From the repository root:

```powershell
cd backend
```

The prompt should end with:

```text
TAGAD\backend>
```

If it already ends with `TAGAD\backend>`, do not run `cd backend` again.

## 2. Create the virtual environment

Run this only if `backend\venv` does not exist:

```powershell
py -m venv venv
```

The virtual environment is ignored by Git, so every developer must create their
own copy.

## 3. Install backend dependencies

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Using the virtual environment's Python directly avoids PowerShell activation and
execution-policy problems.

## 4. Apply database migrations

```powershell
.\venv\Scripts\python.exe manage.py migrate
```

Complete this step before creating an account so the required database tables
exist.

## 5. Create the Django superuser

```powershell
.\venv\Scripts\python.exe manage.py createsuperuser
```

Django will request a username, email address, and password. Use a unique email
address and a private password. The password must:

- Contain at least 12 characters
- Contain an uppercase letter
- Contain a lowercase letter
- Contain a number
- Contain a symbol
- Not be common or too similar to the user's personal information

The password is hidden while typing. This is normal.

## 6. Start Django

```powershell
.\venv\Scripts\python.exe manage.py runserver
```

Open the following address:

```text
http://127.0.0.1:8000/admin/
```

Log in using the superuser created in the previous step.

## 7. Assign the TAGAD System Administrator role

Creating a Django superuser grants Django Admin access, but the account's TAGAD
role initially defaults to Teacher. Update it as follows:

1. In Django Admin, open **Core > Users**.
2. Select the newly created account.
3. Find the **TAGAD** section.
4. Set **Role** to **System Administrator**.
5. Set **Status** to **Active**.
6. Confirm **Staff status**, **Active**, and **Superuser status** are enabled.
7. Select **Save**.

Log out of the TAGAD frontend and sign in again so it loads the updated role.

## 8. Verify access

Verify both interfaces:

1. Open `http://127.0.0.1:8000/admin/` and confirm Django Admin loads.
2. Open the Vite frontend address, normally `http://localhost:5173` or
   `http://localhost:5174`.
3. Sign in using the same account.
4. Confirm the header displays **System Administrator**.
5. Confirm User Management and organization-wide records are accessible.

## Common problems

### `Cannot find path ...\backend\backend`

The terminal is already inside `backend`. Do not run `cd backend` again.

### `ModuleNotFoundError: No module named 'decouple'`

The wrong Python installation is being used. Install dependencies and run Django
with the virtual environment's Python:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py runserver
```

### Database connection error

Confirm PostgreSQL is running, the database exists, and these values in
`backend/.env` are correct:

```text
DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
```

Do not publish their values.

### The account can open Django Admin but appears as a Teacher in TAGAD

Repeat step 7 and assign the account's TAGAD role to System Administrator. Then
log out and sign in again.

### The password was forgotten

From `TAGAD\backend`, run:

```powershell
.\venv\Scripts\python.exe manage.py changepassword YOUR_USERNAME
```

Replace `YOUR_USERNAME` with the account's actual username.
