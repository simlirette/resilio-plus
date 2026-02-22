# Pre-Presentation Checklist

**Purpose**: Prevent presentation-JSON discrepancies before returning to the main agent.

## Critical Checks

- [ ] Used `suggest-run-count` recommendation (or documented override)
- [ ] Workout count in JSON matches presented count
- [ ] Volume sum = target_volume_km (±0.1km tolerance)
- [ ] No duplicate days, all within week boundaries
- [ ] Presentation derived from jq output above — each workout's date, day, and
      distance_km in the verbal summary matches jq output exactly (not from memory)
- [ ] Weather advisory context reviewed (`resilio weather week`) and reflected in notes

## Validation Commands

```bash
# Validate schema and constraints
resilio plan validate-week --file /tmp/weekly_plan_w<N>.json

# Count workouts
jq '.weeks[0].workouts | length' /tmp/weekly_plan_w<N>.json

# Sum volume
jq '[.weeks[0].workouts[].distance_km] | add' /tmp/weekly_plan_w<N>.json

# List dates and distances (must match verbal presentation exactly)
jq '.weeks[0].workouts[] | {date, day_of_week, type: .workout_type, distance_km}' \
   /tmp/weekly_plan_w<N>.json
```

## If Any Check Fails

**FIX THE JSON** before presenting to the main agent.

Common fixes:
- Workout count mismatch → Regenerate using suggest-run-count recommendation
- Volume mismatch → Adjust workout distances
- Date errors → Use `resilio dates` commands
- Duplicate days → Verify unique dates

## Why This Matters

Presentation-JSON mismatches erode athlete trust. The main agent presents YOUR JSON structure - any discrepancy will reach the athlete.

Always verify before returning.
