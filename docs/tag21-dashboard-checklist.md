# TAG-21 Dashboard Database Integration Checklist

- [x] Show the authenticated user's real name and time-based greeting.
- [x] Replace mock cards with role-scoped classroom, subject, camera, and today's-session counts.
- [x] Load the five most recent accessible classroom sessions.
- [x] Show real session date, duration, status, and engagement when stored.
- [x] Aggregate today's stored engagement and alert records.
- [x] Show an explicit no-data state instead of fabricated engagement values.
- [x] Add dashboard loading, empty, error, and retry states.
- [x] Restrict the dashboard API to authenticated users.
- [x] Test system-admin, organization-admin, and teacher data boundaries.
- [x] Run the complete backend test suite and Django checks.
- [x] Build the production frontend.
- [x] Smoke-test the endpoint against PostgreSQL without leaving test records.
- [x] Verify the live frontend and backend routes.

## Next

- [ ] Manually review the dashboard while signed in as each available role.
- [ ] Commit and push the completed TAG-21 dashboard work.
- [ ] Build the presentation upload and classroom-session foundation.
