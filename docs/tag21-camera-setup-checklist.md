# TAG-21 Camera Setup CRUD Checklist

## Scope

- [x] Add Camera Setup to the existing Classes page.
- [x] Configure database records only; defer CCTV streams and AI inference.

## Database and API

- [x] Restrict positions to Front, Left, and Right.
- [x] Allow only one camera per classroom position.
- [x] Enforce case-insensitive camera-name uniqueness within a classroom.
- [x] Add list, create, retrieve, update, and delete endpoints.
- [x] Apply the camera constraints migration to PostgreSQL.
- [x] Protect cameras used by session history from deletion.

## Permissions

- [x] System Administrators manage cameras across organizations.
- [x] Organization Administrators manage cameras only in their organization.
- [x] Teachers see cameras for assigned classes but cannot modify them.
- [x] Unauthenticated users cannot access camera APIs.
- [x] Mutations require CSRF protection and create audit logs.

## Frontend

- [x] Load real camera records and counts.
- [x] Add administrator-only create, edit, and delete controls.
- [x] Add classroom, position, status, and name fields.
- [x] Display validation, confirmation, empty, loading, and error states.

## Verification

- [x] Focused camera and class-management tests pass.
- [x] Full backend regression suite passes.
- [x] Django system and migration checks pass.
- [x] Frontend production build passes.
- [x] Real PostgreSQL CRUD and permission smoke flow passes without leftover data.

## Next

- Connect the Dashboard's basic counts and recent-session list to real database data.
