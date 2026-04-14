# Knowledge JSON Files — Reference

All files in `docs/knowledge/`. Consumed by coaching agents via prompt injection or tool retrieval.
Schema version: 1.0. Validated by `tests/backend/test_knowledge_jsons.py`.

---

## Coverage Table

| File | Agent | Rules | Last Updated | Source Books | Key Formulas |
|---|---|---|---|---|---|
| `biking_coach_power_rules.json` | Biking Coach | 18 | 2026-04-14 | Coggan & Allen | FTP×0.95; CTL=EWMA42; ATL=EWMA7; TSB=CTL-ATL; Z1-Z7 %FTP; TSS thresholds |
| `head_coach_acwr_rules.json` | Head Coach | 17 | 2026-04-14 | Daniels; Pfitz-Adv | ACWR=EWMA7/EWMA28; monotony=avg/SD; strain=total×monotony; compound HRV+ACWR flag |
| `head_coach_interference_rules.json` | Head Coach | 15 | 2026-04-14 | Pfitz-Adv; FIRST | Strength→Endurance order; 6h gap; AMPK/mTOR window 0-6h; taper MEV |
| `lifting_coach_volume_rules.json` | Lifting Coach | 17 | 2026-04-14 | Israetel et al. | MEV 8-10 sets/wk; MAV 15-20; MRV 25+; DUP 3/8/15; 2×/wk frequency; deload 4-6wk |
| `nutrition_coach_fueling_rules.json` | Nutrition Coach | 18 | 2026-04-14 | Pfitz-Adv | 1.6-2.2g protein/kg; 3-12g carbs/kg by day type; 30-90g carbs/h intra; 8-12g/kg race-week |
| `recovery_coach_hrv_rules.json` | Recovery Coach | 17 | 2026-04-14 | — | RMSSD: >20ms=OK; 15-20ms=reduce 15%; <15ms×2=rest; <10ms=veto; HRV-guided VO2max +3.7 |
| `recovery_coach_sleep_cns_rules.json` | Recovery Coach | 17 | 2026-04-14 | Pfitz-Adv; Daniels | 8-9h target; 5-6h=5-10% reduction; <5h=critical; CNS 48-72h post-lift; post-marathon 9-10h |
| `running_coach_tid_rules.json` | Running Coach | 29 | 2026-04-14 | All 5 books | VDOT→paces; 80/20 TID; 10% volume cap; Daniels 4-phase; FIRST 3-run; Pfitz GA pace |
| `swimming_coach_biomechanics_rules.json` | Swimming Coach | 16 | 2026-04-14 | Wakayoshi 1992 | CSS=(D400-D200)/(T400-T200); SWOLF=strokes+seconds; Z1-Z4; 15m dolphin kick |

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
