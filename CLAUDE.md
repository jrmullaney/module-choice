# ModuleChoice Project

**GitHub (pipeline)**: https://github.com/jrmullaney/module-choice
**GitHub (web app)**: https://github.com/jrmullaney/module-choice-app

A data pipeline and web app for streamlining student module choices at university. Admins validate student module choices against prerequisites, corequisites, and antirequisites without manual checking.

---

## Pipeline repo (`module-choice`) — legacy

This repo contains the data pipeline only. The web app has moved to `module-choice-app`.

### Pipeline scripts

| Script | Purpose |
|---|---|
| `prefix_codes.py` | Prepend prefix (default `PHY`, pass `--prefix MPS` etc.) to codes that don't start with a letter; expand comma-separated codes to one per column; ignores `Placement Yr` and `F` |
| `make_matrix.py` | Build initial student × module presence matrix (0/1) from a flat TSV |
| `merge_year.py` | Merge a new year's flat TSV into an existing matrix; 1s never become 0s; new students/columns added |
| `recode_modules.py` | Rename matrix columns via a lookup table (old→new); ORs columns that merge; reports codes missing from lookup |
| `run_pipeline.sh` | Full pipeline: prefix all three years → make matrix from AY23-24 → merge AY24-25 → recode → merge AY25-26 |
| `test_pipeline.py` | Unit tests for all scripts (`python3 -m unittest test_pipeline -v`) — 60 tests |

### Data files

- `Data/Input/AY23-24.txt`, `AY24-25.txt`, `AY25-26.txt` — raw tab-separated module choice data
- `module_lookup.txt` — maps old PHY codes to new MPS codes (superseded by `modules.txt` in `module-choice-app`)
- `credits_processed.txt` — module codes with credit values (superseded by `modules.txt` in `module-choice-app`)
- `Data/Processed/AY25-26_processed.txt` — current output: cumulative student × module presence matrix (copied to `module-choice-app/Data/Students/module_matrix.txt` for DB builds)
- `Data/Requisites/` — processed prerequisite, corequisite, and antirequisite files

### Module code conventions

- AY23-24 and AY24-25: numeric-only codes prefixed with `PHY` (e.g. `129` → `PHY129`)
- AY25-26: university renamed all modules; numeric-only codes prefixed with `MPS`; existing codes remapped via `module_lookup.txt`

---

## Web app repo (`module-choice-app`)

Local path: `/Users/ph1jxm/Documents/Work/Teaching/ModuleChoiceApp`
Deployed at: `mps-module-choice.up.railway.app` (Railway, Postgres)

### Data files

- `Data/Students/module_matrix.txt` — cumulative student × module presence matrix (gitignored; copy from pipeline repo before rebuilding DB)
- `Data/Modules/modules.txt` — module data: `oldcode`, `newcode`, `credits`, `title` (merged from `module_lookup.txt` + `credits_processed.txt`)
- `Data/Requisites/` — prerequisite, corequisite, and antirequisite files

### Key files

- `build_db.py` — builds the Postgres database from processed files; drops and recreates all tables on each run; defaults: `--matrix Data/Students/module_matrix.txt`, `--modules Data/Modules/modules.txt`
- `validate_choices.py` — validates a student's proposed choices against all rules; checks antirequisites bidirectionally
- `app.py` — Flask app; `DATABASE_URL` from environment; `APP_PASSWORD` for login; `SECRET_KEY` for sessions

### Running locally

```
LC_ALL='en_US.UTF-8' /opt/homebrew/opt/postgresql@16/bin/postgres -D /opt/homebrew/var/postgresql@16
DATABASE_URL=postgresql://localhost/module_choice python3 app.py
```

Rebuild DB locally: `DATABASE_URL=postgresql://localhost/module_choice python3 build_db.py`

### Database schema

`students`, `modules` (code, credits, title), `enrolments`, `prerequisites`, `corequisites`, `antirequisites`, `module_aliases` (new→old code mappings), `choices` (student responses with status), `expected_respondents`, `programmes`, `programme_modules` (with `level`)

### Validation rules

1. Module not already taken (enrolments)
2. Prerequisites met (enrolments)
3. No antirequisites in enrolments *or* current year's choices (checked bidirectionally)
4. Corequisites in enrolments *or* current year's choices
5. Total credits ≤ 120

### Web app routes

| Route | Purpose |
|---|---|
| `/` | Home — Check Options form, Check Status and Bulk Upload links, student lookup |
| `/modules` | Modules admin page — list, edit, add modules |
| `/expected` | Check Status — upload expected respondents, view/export status, re-validate all |
| `/student/<id>` | Student record — current choices + enrolment history; add/edit/override/delete choices |
| `/bulk` | Bulk upload TSV for multi-student validation |
| `/help` | Help page |

### Templates

`base.html`, `index.html`, `modules.html`, `expected.html`, `student.html`, `bulk.html`, `help.html`, `login.html`

---

## Planned next steps

1. ~~**Login**~~ ✅ Flask-Login, single shared password via `APP_PASSWORD` env var
2. ~~**Hosting**~~ ✅ Deployed to Railway; Postgres on Railway
3. ~~**Move data files to module-choice-app**~~ ✅ `module_matrix.txt` in `Data/Students/`; `modules.txt` in `Data/Modules/`
4. ~~**Module titles**~~ ✅ `title` column in `modules` table; displayed throughout the app
5. ~~**Admin pages**~~ ✅ Modules page: view, edit, add, archive modules (clear credits to archive)
6. ~~**Old/new module code cross-reference**~~ ✅ `module_aliases` table; PHY codes shown slash-separated in student records and modules page
7. **New students in expected list**: if a student appears in the expected respondents upload but has no record in `students`, clicking their ID currently 404s. Instead, show a limited student page (choices + Add module only). When they first add a choice, create a minimal `students` record (student_id only, no programme). Year rollover then incorporates them normally. Requires: update student route for missing students, update `validate_choices` (currently raises ValueError for unknown students), update `student.html` to hide enrolment history for new students.
8. **Year rollover**: once all choices approved, a button copies approved `choices` into `enrolments` and clears `choices` for the new year; show confirmation summary first; warn if any choices are still pending/rejected
8. **Semester data**: add `semester` column to `modules` table; add per-semester credit balance check to `validate_choices.py` (warn if autumn/spring credit difference > 20; year-long modules excluded)
9. **Programme/core module data**: upload core modules per programme per level; add validation check that all core modules are selected
