# Knowledge JSON Files — Reference

All files in `docs/knowledge/`. Consumed by coaching agents via prompt injection or tool retrieval.
Schema version: 1.0. Validated by `tests/backend/test_knowledge_jsons.py`.

---

## Coverage Table

| File | Agent | Rules | Last Updated | Source Books | Key Formulas |
|---|---|---|---|---|---|
| `biking_coach_power_rules.json` | Biking Coach | 15 | 2026-04-13 | Coggan & Allen | FTP×0.95; CTL=EWMA42; ATL=EWMA7; TSB=CTL-ATL; Z1-Z7 %FTP |
| `head_coach_acwr_rules.json` | Head Coach | 10 | 2026-04-13 | — | ACWR=EWMA7/EWMA28; safe 0.8-1.3; caution 1.3-1.5; danger >1.5 |
| `head_coach_interference_rules.json` | Head Coach | 10 | 2026-04-13 | — | Strength→Endurance order; 6h gap; AMPK/mTOR window 0-6h |
| `lifting_coach_volume_rules.json` | Lifting Coach | 12 | 2026-04-13 | Israetel et al. | MEV 8-10 sets/wk; MAV 15-20; MRV 25+; DUP 3/8/15 rep rotation |
| `nutrition_coach_fueling_rules.json` | Nutrition Coach | 12 | 2026-04-13 | Jeukendrup 2011 | 1.6-2.2g protein/kg; 3-12g carbs/kg by day type; 30-90g carbs/h intra |
| `recovery_coach_hrv_rules.json` | Recovery Coach | 11 | 2026-04-13 | — | RMSSD: >20ms=OK; 15-20ms=reduce 15%; <15ms×2=rest; <10ms=veto |
| `recovery_coach_sleep_cns_rules.json` | Recovery Coach | 11 | 2026-04-13 | — | 8-9h target; <6h=modify; CNS window 48-72h post-heavy lift |
| `running_coach_tid_rules.json` | Running Coach | 20 | 2026-04-13 | All 5 books | VDOT→paces; 80/20 TID; 10% volume cap; long run ≤29% or 22mi |
| `swimming_coach_biomechanics_rules.json` | Swimming Coach | 10 | 2026-04-13 | Wakayoshi 1992 | CSS=(D400-D200)/(T400-T200); SWOLF=strokes+seconds; Z1-Z4 |

---

## Schema

All files conform to `docs/knowledge/schemas/common_rule.schema.json`.

Required envelope fields: `schema_version`, `target_agent`, `language`, `last_updated`, `extracted_rules`

Required rule fields: `rule_name`, `category`, `condition`, `action`, `formula_or_value`, `priority`, `confidence`, `source`, `applies_to`

- `priority`: `high | medium | low`
- `confidence`: `strong | moderate | weak`
- `formula_or_value`: never `"N/A"` — must be specific

---

## Validation

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

90 parametrized tests (10 types × 9 files). All must pass before merging any knowledge JSON change.

---

## Adding a New Rule

1. Open the target file in `docs/knowledge/`
2. Add rule with all required fields (use existing rules as template)
3. Ensure `formula_or_value` is not `"N/A"` — use a specific value, range, or formula
4. Run `pytest tests/backend/test_knowledge_jsons.py -k "<filename_fragment>" -v`
5. Commit: `feat(knowledge): add <rule_name> to <filename>`

## Adding a New Knowledge JSON File

1. Create file in `docs/knowledge/` following the common schema envelope
2. Create matching schema in `docs/knowledge/schemas/`
3. Add filename to `JSON_FILES` list in `tests/backend/test_knowledge_jsons.py`
4. Add row to coverage table above
5. Run full test suite
