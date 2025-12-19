# Code Quality Rules

> Standards for maintaining code quality across the project.

## Python (Backend)

### Formatting
- **Formatter**: Black (line-length: 100)
- **Import Sorter**: isort (profile: black)
- **Type Checker**: mypy (strict mode)
- **Linter**: flake8

### Quick Commands
```bash
cd backend && black . && isort . && flake8 . && mypy .
```

### Requirements
- Type hints on all public functions
- Docstrings on all public classes/functions
- No unused imports
- No commented-out code in commits

## TypeScript (Frontend)

### Formatting
- **Formatter**: Prettier
- **Linter**: ESLint

### Quick Commands
```bash
cd frontend && npm run lint && npm run build
```

### Requirements
- Explicit types (avoid `any`)
- Interface for all component props
- No unused variables
- No console.log in production code

## Test Coverage

- Minimum: **80%** coverage
- New features MUST include unit tests
- Never delete tests to make CI pass

## Code Review Checklist

- [ ] Code follows project style guides
- [ ] All tests pass
- [ ] No security vulnerabilities
- [ ] No breaking changes without migration plan
- [ ] Documentation updated if needed
