# Pre-Return Checklist

**Purpose**: Ensure JSON is self-consistent and correct before returning `weekly_json_path` to the main agent. The main agent reads this JSON via jq and owns all athlete-facing presentation.

## Critical Checks

- [ ] Used `suggest-run-count` recommendation (or documented override)
- [ ] Workout count in JSON matches suggest-run-count output
- [ ] Volume sum = target_volume_km (±0.1km tolerance)
- [ ] No duplicate days, all within week boundaries
- [ ] Weather advisory context reviewed (`resilio weather week`) and reflected in workout notes

## Validation Commands

```bash
# Validate schema and constraints
resilio plan validate-week --file /tmp/weekly_plan_w<N>.json

# Count workouts
jq '.weeks[0].workouts | length' /tmp/weekly_plan_w<N>.json

# Sum volume
jq '[.weeks[0].workouts[].distance_km] | add' /tmp/weekly_plan_w<N>.json

# List workouts (main agent will build presentation from this exact output)
jq '.weeks[0].workouts[] | {date, day_of_week, type: .workout_type, distance_km}' \
   /tmp/weekly_plan_w<N>.json
```

## If Any Check Fails

**FIX THE JSON** before returning to the main agent.

Common fixes:
- Workout count mismatch → Regenerate using suggest-run-count recommendation
- Volume mismatch → Adjust workout distances
- Date errors → Use `resilio dates` commands
- Duplicate days → Verify unique dates

## Why This Matters

The main agent presents your JSON structure directly to the athlete via jq. Any discrepancy in the JSON will reach the athlete unchanged.

Always verify before returning.
