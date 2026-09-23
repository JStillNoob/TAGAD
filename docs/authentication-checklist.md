# Authentication implementation checklist

- [x] TAG-12 — Define and document user registration
- [x] TAG-13 — Implement secure password hashing
- [x] TAG-14 — Implement and test the password policy
- [x] TAG-15 — Implement session authentication and route protection
- [x] TAG-16 — Implement CSRF-safe logout and session destruction
- [x] Add a simple teacher registration form
- [x] Add admin forms for initial organization and user setup
- [x] Create the initial `system_admin` superuser
- [x] Add a staff-only Admin Console entry using the existing login session
- [x] Create the first active organization in the configured database
- [x] Run a real-browser registration/login/logout smoke test
- [ ] TAG-17 — Implement CAPTCHA *(deferred)*
- [ ] TAG-18 — Implement two-factor authentication (2FA) *(deferred)*
- [ ] TAG-19 — Implement OAuth authentication *(deferred)*
- [ ] Complete production deployment security configuration and review **(next)**

## Current verification evidence

- Django test suite: 33 tests passing
- Django system check: passing
- Migration drift check: no changes detected
- Vue production build: passing
- Live Vite-to-Django CSRF and registration error flow: passing
- Live application-login to Django-admin single sign-on: passing

Update this checklist and its verification evidence after each authentication
engineering loop.
