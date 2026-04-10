# Merge Steps — Detailed Commands

All commands run in the **main project directory**:
`C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project`

---

## Prerequisites

- [ ] Pre-merge fixes applied and committed (see `02-PRE-MERGE-FIXES.md`)
- [ ] PoC worktree has no uncommitted changes
- [ ] You have read and understood this document

---

## Step 0: Understand Current State

```bash
cd /c/Users/Chris/Downloads/ai-semantic-kernel-framework-project

# What branch am I on?
git branch --show-current
# Expected: feature/phase-42-deep-integration (or similar)

# How many PoC commits will be merged?
git log main..poc/agent-team --oneline | wc -l
# Expected: ~92 (90 original + 2 pre-merge fixes)

# Confirm main has no new commits
git log poc/agent-team..main --oneline | wc -l
# Expected: 0
```

**STOP if**: `poc/agent-team..main` shows commits > 0. That means main has moved forward and you need a different merge strategy.

---

## Step 1: Ensure PoC Branch is Clean

```bash
# Check PoC worktree status
cd /c/Users/Chris/Downloads/ai-semantic-kernel-poc-team
git status
# Expected: "nothing to commit, working tree clean"

# If there are uncommitted changes, commit them first!

# Go back to main project
cd /c/Users/Chris/Downloads/ai-semantic-kernel-framework-project
```

---

## Step 2: Create Safety Backup Branches

```bash
# Backup main's current state
git branch backup/main-before-poc-merge main

# Backup PoC's current state
git branch backup/poc-agent-team-v4-final poc/agent-team

# Verify backups exist
git branch | grep backup
# Should show both backup branches
```

**What this does**: Creates two snapshot branches that are NEVER modified. Even if everything goes wrong, you can always `git reset --hard backup/main-before-poc-merge` to undo.

---

## Step 3: Switch to main Branch

```bash
# First, stash any current work if needed
git stash list  # check if you have stashes

# Switch to main
git checkout main

# Pull latest (in case remote has updates)
git pull origin main

# Confirm you're on main
git branch --show-current
# Expected: main
```

**IMPORTANT**: If `git checkout main` fails because of uncommitted changes on your current branch, you can:
```bash
git stash push -m "work-in-progress before merge"
git checkout main
```

---

## Step 4: Merge (the actual merge)

```bash
git merge poc/agent-team --no-ff -m "$(cat <<'EOF'
feat: merge PoC Agent Team V4 — Orchestrator + Subagent + Agent Team

PoC validated: 4 execution modes, 10-agent E2E test passed, 84% CC parity.

New architecture (CC source-code inspired):
- Mode D: 6-step deterministic orchestrator pipeline (L4+L5+L6)
- Mode A: Subagent via ConcurrentBuilder (L7)
- Mode B: Agent Team with SharedTaskList + parallel WorkLoop (L9)
- Mode C: Hybrid — LLM decides subagent vs team

New modules:
- backend/src/integrations/poc/ (9 files — core engine)
- backend/src/integrations/memory/ (context_budget, extraction, consolidation)
- backend/src/integrations/orchestration/ (transcript, approval, resume)
- frontend AgentTeamTestPage + useOrchestratorSSE

90 files changed, ~16,800 lines added.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Expected output**:
```
Merge made by the 'ort' strategy.
 90 files changed, 16858 insertions(+), 552 deletions(-)
 create mode 100644 backend/src/integrations/poc/agent_work_loop.py
 create mode 100644 backend/src/integrations/poc/approval_gate.py
 ... (many new files)
```

**If you see CONFLICT**: See `05-ROLLBACK-GUIDE.md` section "Handling Merge Conflicts". (Very unlikely since main has 0 new commits.)

---

## Step 5: Verify the Merge

```bash
# Check merge commit exists
git log -1 --oneline
# Should show your merge commit message

# Check file count matches expectation
git diff backup/main-before-poc-merge..main --stat | tail -1
# Expected: ~90 files changed, ~16858 insertions(+), ~552 deletions(-)

# Spot-check key files exist
ls backend/src/integrations/poc/
# Should show: agent_work_loop.py, approval_gate.py, etc.

ls frontend/src/pages/AgentTeamTestPage.tsx
# Should exist

# Check vite proxy is correct (port 8000)
grep "target" frontend/vite.config.ts
# Expected: target: 'http://localhost:8000',
```

---

## Step 6: Push to Remote

```bash
# Push main to origin
git push origin main

# Verify
git log origin/main -1 --oneline
# Should show your merge commit
```

---

## Step 7: Clean Up (Optional, AFTER verification)

Only do this after you've verified everything works (see `04-POST-MERGE-VERIFICATION.md`):

```bash
# Delete backup branches (optional — they cost nothing to keep)
# git branch -d backup/main-before-poc-merge
# git branch -d backup/poc-agent-team-v4-final

# Switch back to your working branch
git checkout feature/phase-42-deep-integration

# Rebase onto updated main (to get PoC changes)
# git rebase main
# WARNING: only do this if you understand rebase. Alternative:
# git merge main  (safer, creates merge commit)
```

---

## Quick Reference: What to Type

If everything is clean and you just want the commands:

```bash
cd /c/Users/Chris/Downloads/ai-semantic-kernel-framework-project
git branch backup/main-before-poc-merge main
git branch backup/poc-agent-team-v4-final poc/agent-team
git checkout main
git pull origin main
git merge poc/agent-team --no-ff -m "feat: merge PoC Agent Team V4"
git log -1 --oneline
git push origin main
```
