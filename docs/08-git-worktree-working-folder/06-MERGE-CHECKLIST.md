# Merge Checklist

Print this and check off each item as you go.

---

## Pre-Merge Fixes (in PoC worktree)

- [ ] Fix 1: `frontend/vite.config.ts` — change port 8044 → 8000
- [ ] Fix 2: `backend/requirements.txt` — add `qdrant-client>=1.7.0`
- [ ] Commit fixes in PoC worktree
- [ ] Verify: `grep "8044" frontend/vite.config.ts` returns nothing
- [ ] Verify: `grep "qdrant-client" backend/requirements.txt` returns entry

## Merge Execution (in main project directory)

- [ ] Step 0: `git log poc/agent-team..main --oneline | wc -l` = 0
- [ ] Step 1: PoC worktree `git status` = clean
- [ ] Step 2: `git branch backup/main-before-poc-merge main`
- [ ] Step 2: `git branch backup/poc-agent-team-v4-final poc/agent-team`
- [ ] Step 3: `git checkout main`
- [ ] Step 3: `git pull origin main`
- [ ] Step 4: `git merge poc/agent-team --no-ff` (with commit message)
- [ ] Step 4: No conflicts? (Expected: yes, zero conflicts)
- [ ] Step 5: `git log -1` shows merge commit
- [ ] Step 5: `ls backend/src/integrations/poc/` shows 9 files
- [ ] Step 5: `grep "target" frontend/vite.config.ts` shows port 8000
- [ ] Step 6: `git push origin main`

## Post-Merge Verification

- [ ] Phase 1: Static checks pass (see 04-POST-MERGE-VERIFICATION.md)
- [ ] Phase 2: Backend starts without errors on port 8000
- [ ] Phase 3: Frontend starts, http://localhost:3005/agent-team-test loads
- [ ] Phase 4: At least 1 functional test passes (any mode)
- [ ] Phase 5: Main chat page still works (no regression)

## Sign-Off

- [ ] All checks passed
- [ ] Date: ____________
- [ ] Notes: ____________________________________________
