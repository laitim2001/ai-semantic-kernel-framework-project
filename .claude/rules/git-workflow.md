# Git Workflow Rules

> Standards for version control and collaboration.

## Commit Message Format

```
<type>(<scope>): <description>

[optional body]

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

### Types
| Type | Use For |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change (no feature/fix) |
| `test` | Adding/updating tests |
| `chore` | Maintenance tasks |

### Scopes
- `api`, `domain`, `infra`, `frontend`
- `agents`, `workflows`, `executions`
- `sprint-N` for sprint-related changes

### Examples
```
feat(agents): Add capability matching algorithm
fix(api): Handle null response in workflow execution
docs: Update API documentation for v1.1
refactor(domain): Extract state machine to separate module
test(agents): Add unit tests for agent service
chore: Update dependencies
```

## Branch Strategy

```
main                    # Production-ready code
├── feature/xxx         # New features
├── fix/xxx             # Bug fixes
└── refactor/xxx        # Refactoring
```

### Naming Convention
- `feature/add-agent-handoff`
- `fix/workflow-timeout-error`
- `refactor/extract-state-machine`

## Before Commit

1. Run tests: `pytest` / `npm run test`
2. Run linting: `black . && flake8 .` / `npm run lint`
3. Check for sensitive data
4. Review changes: `git diff --staged`

## Prohibited Actions

- ❌ Force push to `main`
- ❌ Commit secrets or credentials
- ❌ Commit large binary files
- ❌ Commit generated files (build/, dist/, __pycache__/)
- ❌ Commit incomplete features to main
