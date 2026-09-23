# TAG-20 User Management Checklist

Source: `ACM_Alegado_Mizal_Lloren_final (3).pdf`, especially sections 1.4, 2.1.4, 2.1.5, and the Users data dictionary.

## Confirmed roles

- System Administrator: manages the entire platform, organizations, and system configuration.
- Organization Administrator: manages teachers and organization-owned resources within one organization.
- Teacher: conducts sessions and reviews analytics; cannot manage user accounts.

## Permission rules

- [x] System Administrators can view and manage accounts across organizations.
- [x] Organization Administrators can view and manage Teacher accounts only in their own organization.
- [x] Teachers and unauthenticated visitors cannot access user-management APIs or screens.
- [x] Organization Administrators cannot assign administrator roles or move users between organizations.
- [x] Administrators cannot deactivate or change the access role of their own account.

## TAG-25 — User CRUD operations

- [x] List users within the signed-in administrator's permitted scope.
- [x] Create users with a securely hashed password and the existing password policy.
- [x] View user profile information required for administration.
- [x] Edit identity, contact, organization, role, and status within permission boundaries.
- [x] Deactivate accounts instead of physically deleting records, preserving reports and audit history.
- [x] Reactivate an inactive account when permitted.
- [x] Validate case-insensitive username and email uniqueness.
- [x] Record account creation, update, deactivation, and reactivation in system logs.

## TAG-26 — Roles and permissions

- [x] Add backend permissions and organization-scoped querysets.
- [x] Add role-aware frontend route protection.
- [x] Show User Management navigation only to System and Organization Administrators.
- [x] Restrict role and organization form choices based on the signed-in administrator.

## Verification loop

- [x] Backend authorization and CRUD tests pass.
- [x] Existing authentication regression tests pass.
- [x] Django system checks and migration checks pass.
- [x] Frontend production build passes.
- [x] End-to-end administrator and forbidden-user flows pass.

## Explicitly deferred

- TAG-17 CAPTCHA
- TAG-18 Two-factor authentication
- TAG-19 OAuth authentication
