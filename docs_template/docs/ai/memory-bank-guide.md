# Memory Bank Guide

## Overview

This project uses a "Memory Bank" pattern where the AI agent maintains structured knowledge in `docs/ai/` to preserve context across sessions. The Memory Bank is the **changing** project knowledge—what the agent has learned, decided, planned, and tracked during active development. Static configuration, code, and documentation live in their normal locations.

## File Structure

```
docs/ai/
├── memory-bank-guide.md     # This file (structure and rules)
├── architecture.md          # Technical decisions and system design
├── current-task.md          # Active task tracking
├── decisions.md             # Current active decisions
├── decisions-archive.md     # Completed decisions (archived)
├── issue-inventory.md       # Master list of all known issues
├── known-issues.md          # Currently active known issues
├── known-issues-archive.md  # Resolved issues (archived)
├── plans.md                 # Current active plans
├── plans-archive.md         # Completed plans (archived)
├── backlog.md               # Prioritized task backlog
├── api-rate-limits.md       # API rate limit documentation
└── tasks/                   # Completed task records
    └── YYYY-MM-DD-short-name.md
```

## Update Timing

### Every Session Start
- Read `current-task.md` to resume context
- Read `decisions.md` for active decisions
- Read `known-issues.md` for active blockers

### During Work
- Update `current-task.md` as progress is made
- Add new decisions to `decisions.md` when made
- Log new issues to `known-issues.md` when discovered

### Session End / Task Completion
- Archive completed decisions to `decisions-archive.md`
- Archive resolved issues to `known-issues-archive.md`
- Archive completed plans to `plans-archive.md`
- Write task record to `tasks/YYYY-MM-DD-short-name.md`
- Update `current-task.md` to reflect completion

## Archive Rules

### When to Archive
- A decision is finalized and no longer being debated
- An issue is resolved and verified
- A plan is completed or cancelled
- `decisions.md`, `known-issues.md`, or `plans.md` grows beyond manageable size

### Archive Format
- Move the completed entry to the corresponding `-archive.md` file
- Keep a brief reference in the active file: `→ archived in decisions-archive.md`
- Archive entries are append-only; never modify past archive entries

### Archive File Naming
- `decisions-archive.md` — completed design decisions
- `known-issues-archive.md` — resolved issues
- `plans-archive.md` — completed or cancelled plans

## Long-running Agent Tasks

For tasks that span multiple sessions or require ongoing tracking:

1. Create a task file in `tasks/` with the `YYYY-MM-DD-short-name.md` naming convention
2. Update the task file as work progresses across sessions
3. Mark the task as complete when finished
4. Reference the task file from `current-task.md` while active

## Recovery After Interruption

If a session is interrupted or the agent loses context:

1. Read `current-task.md` first to understand the last active work
2. Check `known-issues.md` for any unresolved blockers
3. Review `decisions.md` for any pending decisions
4. Check `tasks/` for the most recent task files to understand recent work
5. Resume from the last verified checkpoint
