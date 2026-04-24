# ModuleChoice Project

**GitHub**: https://github.com/jrmullaney/module-choice

A data pipeline and (planned) web-app for streamlining student module choices at university. Admins need to validate student module choices against prerequisites, corequisites, and antirequisites without manual checking.

## Pipeline scripts

| Script | Purpose |
|---|---|
| `prefix_codes.py` | Prepend prefix (default `PHY`, pass `--prefix MPS` etc.) to codes that don't start with a letter; expand comma-separated codes to one per column; ignores `Placement Yr` and `F` |
| `make_matrix.py` | Build initial student × module presence matrix (0/1) from a flat TSV |
| `merge_year.py` | Merge a new year's flat TSV into an existing matrix; 1s never become 0s; new students/columns added |
| `recode_modules.py` | Rename matrix columns via a lookup table (old→new); ORs columns that merge; reports codes missing from lookup |
| `run_pipeline.sh` | Full pipeline: prefix all three years → make matrix from AY23-24 → merge AY24-25 → recode → merge AY25-26 |
| `test_pipeline.py` | Unit tests for all scripts (`python3 -m unittest test_pipeline -v`) — 60 tests |

## Data files

- `Data/Input/AY23-24.txt`, `AY24-25.txt`, `AY25-26.txt` — raw tab-separated module choice data
- `module_lookup.txt` — maps old codes to new codes for the AY25-26 rename (tab-separated, old code in col 0, new code in col 1)
- `credits_processed.txt` — module codes with credit values (lives in base directory alongside module_lookup.txt)
- `Data/Processed/AY25-26_processed.txt` — current output: cumulative student × module presence matrix
- `Data/Requisites/` — processed prerequisite, corequisite, and antirequisite files

## Module code conventions

- AY23-24 and AY24-25: numeric-only codes prefixed with `PHY` (e.g. `129` → `PHY129`)
- AY25-26: university renamed all modules; numeric-only codes prefixed with `MPS`; existing codes remapped via `module_lookup.txt`

## Database

- `build_db.py` — builds `module_choice.db` (SQLite) from processed files
- `validate_choices.py` — validates a student's proposed choices against all rules
- Schema: `students`, `modules` (with credits), `enrolments`, `prerequisites`, `corequisites`, `antirequisites`, `choices`, `programmes`, `programme_modules` (with `level`), 

## Validation rules

1. Module not already taken (enrolments)
2. Prerequisites met (enrolments)
3. No antirequisites in enrolments *or* current year's choices
4. Corequisites in enrolments *or* current year's choices
5. Total credits ≤ 120
6. **TODO**: Semester balance check — modules are autumn, spring, or year-long; year-long modules are excluded from the check (they contribute equally to both semesters). Warn if the difference between autumn credits and spring credits exceeds 20. Semester data not yet available — needs adding to `modules` table (e.g. `semester TEXT` — 'autumn', 'spring', 'year') and balance check logic in `validate_choices.py`.

## Programmes

- `programmes` table and `programme_modules` table (module_code, level) are in the schema, ready for data
- Each student has a `programme_code` in the `students` table
- Core module data not yet available — to be uploaded when ready

## Planned next steps

1. **Semester data**: add `semester` column to `modules` table; add per-semester credit limit check to `validate_choices.py`
2. **Programme/core module data**: upload core modules per programme per level; add validation check that all core modules are selected
3. **Web-app**: admins enter/upload student choices; system validates against rules; no backend knowledge required
