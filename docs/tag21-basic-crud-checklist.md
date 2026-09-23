# TAG-21 Basic CRUD — Classes Checklist

## Scope

- [x] Replace hard-coded Classes page data with Classroom and Subject APIs.
- [x] Keep CCTV processing, camera configuration, student records, and engagement analytics out of this loop.
- [x] Keep TAG-29 unassigned until its intended scope is provided.

## Classroom CRUD

- [x] List classrooms within the user's permitted organization scope.
- [x] Create and edit room code, building, capacity, and organization.
- [x] Validate positive capacity and case-insensitive room-code uniqueness.
- [x] Delete only empty classrooms; protect classrooms with subjects or cameras.

## Subject CRUD

- [x] List subjects within the user's permitted scope.
- [x] Create and edit subject code, name, classroom, and assigned teacher.
- [x] Require the assigned teacher to belong to the classroom's organization.
- [x] Validate case-insensitive subject-code uniqueness.
- [x] Delete only subjects without classroom-session history.

## Roles and security

- [x] System Administrators can manage classrooms and subjects across organizations.
- [x] Organization Administrators can manage classrooms and subjects only in their organization.
- [x] Teachers can view only their assigned subjects and cannot mutate data.
- [x] Unauthenticated users cannot access the APIs.
- [x] CRUD mutations require CSRF protection and create audit logs.

## Frontend

- [x] Display real database-backed summary statistics.
- [x] Display real subjects and classroom information.
- [x] Provide administrator-only create/edit/delete controls.
- [x] Provide loading, empty, confirmation, validation, and error states.

## Verification

- [x] New backend tests pass.
- [x] Existing regression tests pass.
- [x] Django checks and migration checks pass.
- [x] Frontend production build passes.
- [x] Live API/browser smoke flow passes without leaving test data.

## Next loop

- Camera setup CRUD as the non-AI foundation for the future CCTV integration.
