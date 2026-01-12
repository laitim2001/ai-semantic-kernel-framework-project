# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI service. Main code lives in `backend/src/`, tests in `backend/tests/`, migrations in `backend/alembic/`, and runtime config in `backend/config/`.
- `frontend/`: React + Vite app. Source in `frontend/src/`, static assets in `frontend/public/`, and Playwright tests in `frontend/e2e/`.
- `docs/`: Product and architecture documentation (BMAD method folders).
- `deploy/`, `infrastructure/`, `monitoring/`, `scripts/`: Environment, infra, and ops tooling.

## Build, Test, and Development Commands
- `docker-compose up -d`: Start PostgreSQL, Redis, and RabbitMQ.
- `uvicorn main:app --reload --port 8000` (from `backend/`): Run the API locally.
- `npm run dev` (from `frontend/`): Run the UI locally.
- `npm run build` (from `frontend/`): Production build.
- `pytest` (from `backend/`): Run backend tests.
- `npm test` (from `frontend/`): Run UI unit tests (Vitest).
- `npm run test:e2e` (from `frontend/`): Run Playwright E2E tests.

## Coding Style & Naming Conventions
- Python: Black + isort (line length 100). Type checks via mypy. Class names `PascalCase`, functions `snake_case`, constants `UPPER_SNAKE_CASE`, private helpers `_leading_underscore`. Use Google-style docstrings.
- TypeScript/React: ESLint and TypeScript strict mode. Components `PascalCase`, event handlers `camelCase`, and file names `kebab-case` (e.g., `workflow-editor.tsx`).

## Testing Guidelines
- Pytest is configured for `backend/tests/` with `test_*.py` files and `Test*` classes. Coverage enforces 80% minimum (see `backend/pyproject.toml`).
- Frontend tests use Vitest; coverage via `npm run test:coverage`. E2E flows live in `frontend/e2e/` and run with Playwright.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `type(scope): subject` (e.g., `feat(workflow): add parallel execution`). Keep subject concise; use footers to reference issues or breaking changes.
- Branching follows Git Flow: `feature/`, `bugfix/`, and `hotfix/` from `develop`.
- PRs should include a clear summary, linked issues, and screenshots for UI changes. Expect at least one approval and green CI before merge.

## Security & Configuration Tips
- Copy `.env.example` to `.env` and keep secrets local. Update `.env.example` when new config is required; never commit real keys.
