---
name: weekly-plan-apply
description: Applies an approved weekly plan JSON to the plan store after validation. Use only after athlete approval is recorded by the main agent.
disable-model-invocation: false
context: fork
allowed-tools: Bash, Read, Write
argument-hint: "approved_file=<path>"
---

# Weekly Plan Apply (Executor)

## SCOPE LOCK

This skill's ONLY job is to validate and persist a pre-approved JSON.
It does NOT generate, redesign, re-present, or re-evaluate workout content.

**Prohibited actions:**
- Do NOT re-generate or re-design any workout
- Do NOT write to any `/tmp/weekly_plan_*.json` file
- Do NOT re-present the full training schedule
- Do NOT call `resilio plan generate-week` or any plan-creation command
- Do NOT return `athlete_prompt` — approval is already recorded upstream

If you find yourself writing workout content or re-presenting a schedule, STOP.
You are in the wrong workflow. Return a blocking checklist immediately.

## Preconditions (block if missing)
- Approved weekly JSON file path provided in arguments
- Approval recorded in approvals state (week number + file path)

If missing, return a blocking checklist and stop.

## Workflow

Copy this checklist and check off each step as you complete it:

```
Apply Progress:
- [ ] Step 1: Verify approval state
- [ ] Step 2: Validate payload
- [ ] Step 3: Apply (populate)
- [ ] Step 3.5: Push lifting to Hevy (if strength sessions)
- [ ] Step 4: Confirm workouts persisted
```

**Step 1 — Verify approval state:**
```bash
resilio approvals status
```
Confirm `weekly_approval.week_number` and `weekly_approval.approved_file` match
the provided payload path. If they don't match, return a blocking checklist and stop.

**Step 2 — Validate payload:**
```bash
resilio plan validate-week --file <APPROVED_FILE>
```
If validation fails (exit code ≠ 0), include the full error output in a blocking
checklist. Do NOT attempt to fix the JSON — return the error to the main agent.

**Step 3 — Apply:**
```bash
resilio plan populate --from-json <APPROVED_FILE> --validate
```
If this fails (exit code ≠ 0), include the full error output in a blocking checklist.
The command automatically synchronizes the changed week to Google Calendar. Check
`data.calendar_sync.ok` in the response. If it is `false`, the plan is already
saved: return a blocking checklist for the Calendar failure and do NOT populate
the week again.

<!-- lifting:sp4 -->
**Step 3.5 — Hevy program push (ONLY on a program change):**
```bash
resilio lift push --week <WEEK_NUMBER>
```
Skip this step for a normal week. Hevy routines ("Resilio" folder, one per session:
Upper A, Legs, Upper B, Arms) stay fixed for the mesocycle (~3-4 months) because Hevy
tracks progress per routine. Run it only when the main agent's arguments say the athlete
approved a program change (new mesocycle or an exercise swap). If it fails
(`error_type` config/auth/rate_limit/api_error), the plan is already saved:
return a blocking checklist with the error and `next_steps`. Do NOT re-populate.

**Step 4 — Confirm workouts persisted:**
```bash
resilio plan week --week <WEEK_NUMBER>
```
Verify the `workouts` array in the response is non-empty. If it is empty, populate
did not succeed — return a blocking checklist with the plan week output.

## References (load only if needed)
- JSON workflow: `references/json_workflow.md`

## Output

Return EXACTLY:
- `applied_file`: path of the file that was applied
- `week_number`: the week that was populated

Do NOT return `weekly_json_path`. Do NOT return `athlete_prompt`.
If blocked: return `blocking_checklist` with the specific failure and CLI output.
