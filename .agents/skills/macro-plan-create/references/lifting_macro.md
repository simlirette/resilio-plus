# Lifting Blocks in the Macro Plan

Read when the athlete has `lifting` in their profile. Methodology: `docs/coaching/lifting_methodology.md`.

After the macro plan exists, store lifting blocks aligned with the running phases:

```bash
resilio lift profile get          # goal, gym days, split
resilio lift volume --week-start <LAST_MONDAY>   # current hard sets per muscle (starting point)
resilio lift blocks set --file /tmp/lifting_blocks.json
resilio lift blocks get
```

`/tmp/lifting_blocks.json`:

```json
[
  {"start_week": 1, "end_week": 3, "focus": "hypertrophy", "sessions_per_week": 3,
   "weekly_sets": {"chest": 10, "back": 12, "shoulders": 8, "biceps": 6, "triceps": 6,
                   "quads": 6, "hamstrings": 6, "glutes": 4, "core": 6},
   "notes": "Start near MEV; +1-2 sets/muscle/week for upper body."},
  {"start_week": 4, "end_week": 4, "focus": "deload", "sessions_per_week": 3,
   "weekly_sets": {"chest": 6, "back": 7, "quads": 4, "hamstrings": 4}, "notes": "Aligned with running recovery week."}
]
```

## Rules

- Deload block at least every 4 weeks (resilio-plus rule), placed on the running recovery week.
- Plan the DUP zone rotation per block (e.g. weeks 1–3 Upper A heavy / Upper B light, next block swapped).

- Lifting deloads land on the running recovery weeks.
- `hypertrophy_athletic` with a running test/race ahead: upper body MEV→MAV across the block;
  lower body near MEV (hybrid MRV is low). Final 1–2 weeks before a race/test → `maintenance`
  (≈ ⅓ volume, keep loads, no new exercises, no legs within 72 h of the test).
- `sessions_per_week` must fit `gym_days` (+ optional days).
- Keep the athlete's split labels (`lifting.split`) so the weekly plan reuses them.
- Include the block table in the macro review document next to the running phases.
