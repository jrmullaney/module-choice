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
| `test_pipeline.py` | Unit tests for all scripts (`python3 -m unittest test_pipeline -v`) |

## Data files

- `AY23-24.txt`, `AY24-25.txt`, `AY25-26.txt` — raw tab-separated module choice data
- `module_lookup.txt` — maps old codes to new codes for the AY25-26 rename (tab-separated, old code in col 0, new code in col 1)
- `AY25-26_processed.txt` — current output: cumulative student × module presence matrix

## Module code conventions

- AY23-24 and AY24-25: numeric-only codes prefixed with `PHY` (e.g. `129` → `PHY129`)
- AY25-26: university renamed all modules; numeric-only codes prefixed with `MPS`; existing codes remapped via `module_lookup.txt`

## Planned next steps

1. **Requisite data**: prerequisites, corequisites, and antirequisites need to be assembled — doesn't exist in machine-readable form yet. Suggested input format: spreadsheet with columns `module`, `type` (pre/co/anti), `related_module`
2. **SQLite database**: normalised schema — `students`, `modules`, `enrolments` (from matrix), `prerequisites`, `corequisites`, `antirequisites`, `choices` (pending validation)
3. **Validation logic**: for each proposed choice check:
   - Not already taken (enrolments)
   - Prerequisites met (enrolments)
   - No antirequisites in enrolments *or* current year's choices
   - Corequisites in enrolments *or* current year's choices
4. **Web-app**: admins enter/upload student choices; system validates against rules; no backend knowledge required
