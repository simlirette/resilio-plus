# Training Book Extraction — Design Spec

**Date:** 2026-04-13
**Status:** Approved
**Trigger:** 5 training books in `docs/training_books/` exist as narrative AI-coach distillations. Needed: structured, agent-actionable extractions with prescriptive rules, formulas, reference tables, and source traceability.

---

## Objective

Re-extract each of the 5 training books into a standardized, agent-actionable format. Output: `docs/backend/books/<book>-extract.md` per book + `INDEX.md`. Source files (`docs/training_books/`) are read-only inputs — not modified.

---

## Approach

**Option A — Direct restructure, one subagent per book.** Read source `.md` → extract into 6-section format → commit. Sequential (one book at a time). INDEX produced as a 6th task after all 5 extractions.

**Citations:** Reference by named table/section (e.g., `Daniels Table 5.1`, `Pfitzinger §4.3`) — source files contain no page numbers. This is traceable without physical books.

---

## File Map

| File | Action |
|---|---|
| `docs/backend/books/daniels-running-formula-extract.md` | Create |
| `docs/backend/books/pfitzinger-advanced-marathoning-extract.md` | Create |
| `docs/backend/books/pfitzinger-faster-road-racing-extract.md` | Create |
| `docs/backend/books/fitzgerald-8020-extract.md` | Create |
| `docs/backend/books/pierce-first-extract.md` | Create |
| `docs/backend/books/INDEX.md` | Create |

Source files (read-only):
- `docs/training_books/daniel_running_formula.md`
- `docs/training_books/advanced_marathoning_pete_pfitzinger.md`
- `docs/training_books/faster_road_racing_pete_pfitzinger.md`
- `docs/training_books/80_20_matt_fitzgerald.md`
- `docs/training_books/run_less_run_faster_bill_pierce.md`

---

## Standard Extraction Format

Each `*-extract.md` file follows this exact structure:

```markdown
# [Titre complet] — Agent Extract

**Source:** [auteur, titre complet, éditeur, année, édition]
**Domain:** Running — [sous-domaine: zones / periodization / TID / race-specific]
**Agent cible:** Running Coach (principalement); Head Coach (règles de sécurité)

---

## 1. Concepts fondamentaux
- Bullet concis par concept — pas de paraphrase molle
- Chaque bullet = un concept autonome, actionnable

## 2. Formules et calculs
| Formule | Inputs | Output | Notes |

## 3. Tables de référence
| Zone/Seuil | Valeur | Unité | Condition |

## 4. Règles prescriptives
- IF [condition observable] THEN [action prescrite] `[ref: §X / Table Y]`
- Forme stricte IF/THEN uniquement — zéro nuance floue
- Si non exprimable en IF/THEN → section 1

## 5. Contre-indications et cas limites
- Situations où la règle générale ne s'applique pas
- Seuils de sécurité (blessure, surmenage, maladie)
- Population exclue du modèle (débutants absolus si applicable)

## 6. Références sources
| Concept | Référence livre |
```

### Section 4 rules

- Form: `IF [observable condition] THEN [prescribed action]` — no hedging, no "may", no "consider"
- Each rule ends with a bracketed source reference: `[ref: Table 5.1]`, `[ref: §4]`, `[ref: Ch.7]`
- Rules that conflict across books are kept verbatim in each book's file — conflicts resolved in INDEX.md

---

## Books: Domain Summary

| File | Book | Author | Primary Domain |
|---|---|---|---|
| `daniel_running_formula.md` | Daniels' Running Formula | Jack Daniels, 3rd ed. | VDOT, training zones (E/M/T/I/R), phase structure |
| `advanced_marathoning_pete_pfitzinger.md` | Advanced Marathoning | Pfitzinger & Douglas, 2nd ed. | Marathon periodization, LT, volume progression |
| `faster_road_racing_pete_pfitzinger.md` | Faster Road Racing | Pfitzinger & Latter, 2015 | 5K–HM race-specific training, lactate, economy |
| `80_20_matt_fitzgerald.md` | 80/20 Running | Matt Fitzgerald, 2014 | Training intensity distribution, polarized TID |
| `run_less_run_faster_bill_pierce.md` | Run Less Run Faster | Pierce, Murr & Moss (FIRST) | 3-run/week quality model, cross-training |

---

## INDEX.md Structure

`docs/backend/books/INDEX.md` is produced last. Contains:

### 1. Coverage matrix
Table: concept rows × book columns (✅ / — / ⚠️ conflict).

### 2. JSON integration candidates
List of numeric thresholds and zone definitions suitable for `.bmad-core/data/`:
- Which `.json` file they belong to (existing or new)
- Example value
- Source book

### 3. Agent prompt candidates
List of IF/THEN rules suitable for `backend/app/agents/prompts.py`:
- Which agent (Running Coach / Head Coach)
- The rule text
- Source book + reference

INDEX does NOT duplicate content from extract files — it references them with file path + 1-line summary per concept.

---

## Invariants

- `docs/training_books/` files are read-only — not modified
- No new Python files, no migrations, no pytest changes
- One atomic commit per book extraction
- Section 4 rules are strictly IF/THEN — no soft language
- Conflicting rules across books are preserved verbatim in each extract; conflicts flagged in INDEX.md
- `docs/backend/books/` directory created by first task

---

## Out of Scope

- Lifting, swimming, cycling books — not available
- Actual JSON updates — INDEX identifies candidates only; updates are a separate task (Partie 3)
- Actual prompt updates — INDEX identifies candidates only; updates are a separate task (Partie 1B)
- VDOT lookup tables (too large for markdown — reference only)
