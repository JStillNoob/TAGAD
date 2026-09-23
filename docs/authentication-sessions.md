# Authentication: sessions and logout

This document records the TAG-15 and TAG-16 session-authentication behavior.

## API flow

1. The client requests `GET /api/auth/csrf/` to receive a CSRF cookie.
2. The client sends `POST /api/auth/login/` with `identity`, `password`, and the
   CSRF token in the `X-CSRFToken` header. Identity may be an email address or
   username and is matched case-insensitively.
3. Successful authentication creates a server-side Django session and returns
   the user's non-secret profile. Invalid credentials always return the same
   HTTP 401 response.
4. The client checks `GET /api/auth/me/` when restoring a browser session.
5. The client sends `POST /api/auth/logout/` with the current CSRF token. Django
   flushes the session and the endpoint returns HTTP 204.

Both Django's `is_active` flag and the TAGAD `status` field must be active. A
user linked to an organization also requires that organization to be active.
The active-user middleware flushes an existing session as soon as either the
account or its organization is deactivated.

## Protection rules

- Django's session and authentication middleware populate `request.user`.
- Django REST Framework endpoints require an authenticated session by default.
  Public endpoints must opt in explicitly with `AllowAny`.
- Login and logout are CSRF-protected. Logout is POST-only.
- The Vue router verifies `/api/auth/me/` before entering application routes and
  redirects unauthenticated visitors to `/` with their intended path preserved.
- The frontend reads the CSRF cookie immediately before every state-changing
  request because Django rotates the token after login.
- The authenticated profile exposes `can_access_admin`, derived from active
  staff status. The frontend displays **Admin Console** only when this value is
  true; Django still performs the authoritative permission check.
- During development, Vite proxies `/admin/` and `/static/admin/` to Django so
  the main application and Django admin reuse the same session cookie.

## Local development

Run Django with `DEBUG=True` at `http://127.0.0.1:8000` and Vite normally.
Vite proxies `/api` requests to Django so browser sessions remain same-origin.
When debug mode is off, session and CSRF cookies default to secure-only and
must be served over HTTPS.

The development origins `http://localhost:5173` and `http://127.0.0.1:5173`
are trusted automatically in debug mode. Set `CSRF_TRUSTED_ORIGINS` to a
comma-separated list of HTTPS frontend origins in other environments.
