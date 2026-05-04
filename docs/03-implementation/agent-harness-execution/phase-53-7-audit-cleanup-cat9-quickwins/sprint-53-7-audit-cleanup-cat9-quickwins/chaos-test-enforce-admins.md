# Chaos Test — `enforce_admins` Verification (AI-22)

**Sprint**: 53.7 / Day 2 / US-3
**Date executed**: 2026-05-04
**Tester**: laitim2001 (repo owner / admin)
**Closes**: AI-22 (52.6 carryover; deferred via 53.2.5 + 53.6 to 53.7)

---

## Goal

Verify branch protection policy on `main` actually enforces what the
configuration claims:

1. **Required status checks** block PRs that have not gone green on every
   listed context
2. **`enforce_admins=true`** prevents admin (repo owner / org admin) from
   bypassing rule 1 with `gh pr merge --admin`

This is the chaos pillar of the solo-dev policy adopted in Sprint 53.2 —
without confidence that admin bypass actually fails, the policy reduces to
"please don't bypass it" which is not a real safeguard.

## Setup

- main HEAD pre-test: `f4a1425f` (Sprint 53.6 merge)
- Branch protection state (post Sprint 53.7 Day 2 PATCH):
  - `enforce_admins`: true
  - `required_approving_review_count`: 0 (solo-dev policy)
  - `required_status_checks.strict`: true
  - `required_status_checks.contexts`: 5 entries
    1. `Lint + Type Check + Test (with PostgreSQL 16)` (Backend CI)
    2. `Backend E2E Tests` (E2E Tests)
    3. `E2E Test Summary` (E2E Tests)
    4. `v2-lints` (V2 Lint)
    5. `Frontend E2E (chromium headless)` (Playwright E2E — added 53.7)

## Procedure

1. Branch from main: `git checkout -b chore/chaos-test-enforce-admins`
2. Add intentional CI fail: `backend/tests/unit/test_chaos_dummy_53_7.py`
   asserting `1 == 2` (will fail Backend CI's pytest job).
3. Push + open PR #75 with `[CHAOS TEST DO NOT MERGE]` title prefix.
4. Attempt non-admin merge while CI pending → expect block.
5. Attempt admin merge with `--admin` flag → **expect block (the key test).**
6. Document outcomes; close PR + delete branch.

## Outcomes

### Step 4 — non-admin merge attempt (CI pending)

```
$ gh pr merge 75 --merge
X Pull request laitim2001/.../pull/75 is not mergeable: the base branch
  policy prohibits the merge.
To have the pull request merged after all the requirements have been met,
add the `--auto` flag.
To use administrator privileges to immediately merge the pull request, add
the `--admin` flag.
exit=0
```

✅ **Blocked as expected.** Non-admin merge respects required checks.

### Step 5 — admin merge attempt (CI pending — KEY TEST)

```
$ gh pr merge 75 --merge --admin
GraphQL: 5 of 5 required status checks have not succeeded: 3 expected.
(mergePullRequest)
exit=0
```

✅ **CRITICAL EVIDENCE — Blocked.** GitHub's GraphQL API explicitly states
"5 of 5 required status checks have not succeeded: 3 expected"; the request
was rejected at the API layer because `enforce_admins=true` removes admin's
ability to bypass `required_status_checks`.

The "3 expected" hint refers to PR-time checks that had not yet been
queued (E2E Tests workflow paths-filter likely deferred them); this does
not change the block — once `enforce_admins=true`, all 5 contexts must
report success regardless of the admin flag.

## Conclusion

Branch protection policy is **actually enforced**:

| Rule | Verified |
|------|----------|
| `required_status_checks` blocks merge when contexts not green | ✅ Step 4 |
| `enforce_admins=true` blocks `gh pr merge --admin` bypass | ✅ Step 5 |

The solo-dev policy adopted in Sprint 53.2 (review_count=0 +
enforce_admins=true + 4 active CI checks → 5 since 53.7) provides genuine
protection; admin cannot accidentally or deliberately ship red code to main.

## Cleanup

```
$ gh pr close 75 --delete-branch
$ git push origin :chore/chaos-test-enforce-admins   # if remote not auto-deleted
```

main HEAD post-cleanup: `f4a1425f` (unchanged — chaos branch never merged).

## Notes

- This test should be re-run after any future change to branch protection
  config, especially if `enforce_admins` toggles or `required_status_checks`
  changes shape (e.g. switch from contexts list to checks app_id).
- A documentation reference is added to
  `docs/03-implementation/agent-harness-planning/13-deployment-and-devops.md`
  §Branch Protection so the verification procedure is discoverable.
- AI-22 originated in Sprint 52.6 retrospective Q4 (Action item #22) and
  was carried through 53.2.5 and 53.6 before landing in 53.7's audit-cycle
  bundle.
