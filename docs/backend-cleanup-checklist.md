# Backend Cleanup Checklist

- [x] Add `backend/venv/` to `.gitignore`.
- [x] Remove the virtual environment from Git tracking without deleting it locally.
- [x] Add pinned Python dependencies in `backend/requirements.txt`.
- [x] Add a secret-free `backend/.env.example`.
- [x] Move backend tests into `core/tests/`.
- [x] Separate authentication and user-management tests.
- [x] Confirm all 82 tests are still discovered and passing.
- [x] Confirm Django system checks pass.
- [x] Confirm no migration changes are required.
- [x] Confirm installed Python dependencies are consistent.
- [x] Confirm models, migrations, and database data were untouched.

## Next

- [ ] Review the staged virtual-environment removals and cleanup files with `git status`.
- [ ] Commit and push the repository cleanup together with the completed dashboard work, or use separate commits if preferred.
- [ ] Later, split `views.py` and `serializers.py` by feature.
- [ ] Later, reorganize non-authentication API URL prefixes.
