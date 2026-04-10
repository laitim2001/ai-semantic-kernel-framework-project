# Rollback Guide

Emergency procedures if the merge causes problems.

---

## Safety Net Overview

```
Protection Layer 1: backup/main-before-poc-merge branch
                    → git reset --hard to this = undo everything

Protection Layer 2: git merge --abort
                    → Cancel merge DURING conflict resolution

Protection Layer 3: PoC worktree unchanged
                    → ai-semantic-kernel-poc-team/ still has original code

Protection Layer 4: Remote poc/agent-team branch
                    → Always available on origin
```

---

## Scenario 1: Merge Conflict During Step 4

**Probability**: Near zero (main has 0 new commits). But if it happens:

```bash
# Option A: Abort the merge entirely
git merge --abort
# → Returns to exactly where you were before the merge command
# → Nothing is lost, nothing is changed

# Option B: Resolve conflicts manually
git status
# Shows files with conflicts (marked "both modified")

# Open each conflicted file, look for:
# <<<<<<< HEAD
# (main version)
# =======
# (poc version)
# >>>>>>> poc/agent-team

# Choose which version to keep, remove the markers
# Then:
git add <resolved-file>
git commit  # Completes the merge
```

---

## Scenario 2: Merge Completed But Something is Wrong

**Before pushing** (safest):

```bash
# Undo the merge completely
git reset --hard backup/main-before-poc-merge

# Verify
git log -1 --oneline
# Should show the old main commit, not the merge commit

# main is now exactly as it was before the merge
```

---

## Scenario 3: Already Pushed But Need to Revert

**After pushing** (more careful approach):

```bash
# Option A: Revert the merge commit (creates a NEW commit that undoes the merge)
git revert -m 1 HEAD
# -m 1 means "keep the main branch side"
# This creates a new commit that reverses all PoC changes
git push origin main

# Option B: If you're the only user, force push (destructive)
# WARNING: Only if no one else has pulled the merge
# git reset --hard backup/main-before-poc-merge
# git push --force origin main
```

**Recommended**: Option A (revert) is always safer than force push.

---

## Scenario 4: Backend Won't Start After Merge

```bash
# Don't panic — this is a dependency/config issue, not a merge issue

# Check error message:
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Common fixes:
pip install -r requirements.txt          # Missing dependency
pip install qdrant-client                # Specifically if qdrant missing

# If nothing works, rollback:
git reset --hard backup/main-before-poc-merge
```

---

## Scenario 5: Frontend Broken After Merge

```bash
# Check vite config:
grep "target" frontend/vite.config.ts
# If it shows 8044 instead of 8000, the pre-merge fix was missed

# Quick fix without rollback:
# Edit frontend/vite.config.ts: change 8044 → 8000
# No need to rollback the entire merge for this

# If page shows errors:
cd frontend
rm -rf node_modules
npm install
npm run dev
```

---

## When to Rollback vs When to Fix Forward

| Situation | Action |
|-----------|--------|
| Backend import error | **Fix forward**: install missing package |
| Frontend proxy wrong port | **Fix forward**: edit vite.config.ts |
| Pages other than PoC are broken | **Investigate first**, then decide |
| Multiple unexplained failures | **Rollback**: `git reset --hard backup/main-before-poc-merge` |
| Data corruption or security concern | **Rollback immediately** |

---

## Key Principle

The backup branches (`backup/main-before-poc-merge` and `backup/poc-agent-team-v4-final`) are your insurance policy. **Do NOT delete them** until you are 100% confident the merge is successful and verified. They cost nothing to keep.
