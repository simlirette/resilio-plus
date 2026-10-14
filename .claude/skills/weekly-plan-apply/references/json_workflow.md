# Apply Skill — What you need to know about the JSON

## This skill does not create plans

The JSON file already exists at the path in the approval state.
Your job is to validate and persist it. Do not inspect or modify workout content.

## The three commands

```bash
# 1. Validate
resilio plan validate-week --file <APPROVED_FILE>

# 2. Persist
resilio plan populate --from-json <APPROVED_FILE> --validate
# The changed week is synchronized to Google Calendar automatically.
# Confirm data.calendar_sync.ok is true; do not run a separate sync command.

# 3. Confirm (workouts must be non-empty)
resilio plan week --week <WEEK_NUMBER>
```

If `resilio plan populate` fails, return the full CLI output in a blocking checklist.
Do not attempt to fix the JSON.

If the plan succeeds but `data.calendar_sync.ok` is false, the plan is already
persisted. Report the Calendar failure and do not populate the week again.

## What a valid file looks like

The file contains an explicit `workouts` array (not `workout_pattern`). This was
validated and approved upstream. Trust it.
