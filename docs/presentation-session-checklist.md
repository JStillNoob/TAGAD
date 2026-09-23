# Presentation and Classroom Session Foundation

- [x] Accept PDF and PPTX uploads.
- [x] Validate extension, MIME type, file signature, upload size, expanded PPTX size, and slide count.
- [x] Preserve the original uploaded file in private application storage.
- [x] Display PDFs through an authenticated same-origin preview.
- [x] Convert PPTX to PDF using LibreOffice or Microsoft PowerPoint.
- [x] Record pending, processing, ready, and failed conversion states and errors.
- [x] Generate ordered slide records and protected slide images.
- [x] Preview a presentation before starting a session.
- [x] Load role-scoped subjects, presentations, and active camera configurations.
- [x] Start sessions with or without camera selections.
- [x] Persist the session date, start time, camera links, and initial slide event.
- [x] Persist slide navigation and restore the last displayed slide.
- [x] End sessions and store the end time.
- [x] Show real recent sessions and resume the signed-in user's ongoing session.
- [x] Enforce teacher, organization-admin, and system-admin data boundaries.
- [x] Require authentication and CSRF protection for mutations.
- [x] Remove simulated engagement, alert, face-tracking, and camera-feed data.
- [x] Clearly label CCTV/AI hardware integration as pending.
- [x] Verify real Microsoft PowerPoint conversion.
- [x] Verify PDF/PPTX upload and session lifecycle against PostgreSQL with cleanup.
- [x] Run all backend tests, Django checks, migration checks, dependency checks, frontend build, and live HTTP checks.

## Deferred until hardware and AI models are available

- [ ] Connect physical CCTV feeds.
- [ ] Add camera health and stream testing.
- [ ] Run face and engagement detection models.
- [ ] Generate real-time engagement summaries and alerts.
