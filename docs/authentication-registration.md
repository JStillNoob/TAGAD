# Authentication: registration and password policy

This document records the TAG-12 registration decisions implemented by the
`POST /api/auth/register/` endpoint.

The Vue frontend exposes this flow at `/register`. The form requests a CSRF
cookie before submitting and returns the new user to the login page after a
successful account creation.

## First organization setup

Registration requires an active organization. On an empty installation:

1. Run `python manage.py createsuperuser` from the `backend` directory.
2. Sign in at `/admin/`.
3. Create an active organization and give its code to the registering user.
4. The user enters that code on `/register` and receives the `teacher` role.

## Registration flow

- Public registration creates an active user with the `teacher` role. Privileged
  roles must be assigned through an administrative workflow.
- Required fields are `username`, `email`, `first_name`, `last_name`,
  `organization_code`, `password`, and `password_confirmation`.
- `middle_name` and `contact_no` are optional.
- The organization code must identify an active organization.
- Usernames and email addresses cannot duplicate an existing account when
  compared case-insensitively. Email addresses are stored in lowercase and the
  database also enforces case-insensitive uniqueness for non-empty values.
- A successful request returns HTTP 201 and the new user's non-secret profile
  fields. Passwords and password confirmation are never returned.
- Registration does not log the user in. The user must complete the login flow
  separately so later CAPTCHA and two-factor checks cannot be bypassed.
- Invalid requests return HTTP 400 with errors keyed by field. No user is
  created when validation fails.
- Registration POST requests require a valid CSRF token.

## Password policy

Registration uses Django's configured password validation framework. Passwords
must be at least 12 characters and must not be too similar to the user's
attributes, commonly used, or entirely numeric.

Passwords are passed to Django's `create_user()` API, which hashes them through
the configured password hasher. Application code must never store or log a raw
password.
