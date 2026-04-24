"""
Build the SQLite database from processed pipeline output files.

Creates the schema and populates it from:
  - The presence matrix (enrolments)
  - Credits file
  - Prerequisite, corequisite, and antirequisite files

Usage:  python3 build_db.py [options]

Options:
  --matrix       PATH   presence matrix (default: Data/Processed/AY25-26_processed.txt)
  --credits      PATH   processed credits file (default: Data/Processed/credits_processed.txt)
  --prereqs      PATH   processed prerequisites file (default: Data/Requisites/pre-requisites_processed.txt)
  --coreqs       PATH   processed corequisites file (default: Data/Requisites/co-requisites_processed.txt)
  --antireqs     PATH   processed antirequisites file (default: Data/Requisites/anti-requisites_processed.txt)
  --db           PATH   output database file (default: module_choice.db)
"""

import argparse
import csv
import sqlite3


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS programmes (
    programme_code  TEXT PRIMARY KEY,
    programme_name  TEXT
);

CREATE TABLE IF NOT EXISTS students (
    student_id      TEXT PRIMARY KEY,
    programme_code  TEXT REFERENCES programmes(programme_code)
);

CREATE TABLE IF NOT EXISTS modules (
    module_code     TEXT PRIMARY KEY,
    credits         INTEGER
);

CREATE TABLE IF NOT EXISTS enrolments (
    student_id      TEXT REFERENCES students(student_id),
    module_code     TEXT REFERENCES modules(module_code),
    PRIMARY KEY (student_id, module_code)
);

CREATE TABLE IF NOT EXISTS prerequisites (
    module_code     TEXT REFERENCES modules(module_code),
    requires        TEXT REFERENCES modules(module_code),
    PRIMARY KEY (module_code, requires)
);

CREATE TABLE IF NOT EXISTS corequisites (
    module_code     TEXT REFERENCES modules(module_code),
    requires        TEXT REFERENCES modules(module_code),
    PRIMARY KEY (module_code, requires)
);

CREATE TABLE IF NOT EXISTS antirequisites (
    module_code     TEXT REFERENCES modules(module_code),
    conflicts_with  TEXT REFERENCES modules(module_code),
    PRIMARY KEY (module_code, conflicts_with)
);

CREATE TABLE IF NOT EXISTS programme_modules (
    programme_code  TEXT REFERENCES programmes(programme_code),
    module_code     TEXT REFERENCES modules(module_code),
    level           INTEGER,
    PRIMARY KEY (programme_code, module_code)
);

CREATE TABLE IF NOT EXISTS choices (
    choice_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id        TEXT REFERENCES students(student_id),
    module_code       TEXT REFERENCES modules(module_code),
    status            TEXT DEFAULT 'pending',
    rejection_reason  TEXT
);
"""


def read_tsv(path: str) -> list[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def read_matrix(path: str) -> tuple[list[str], dict[str, list[str]]]:
    """Return (module_codes, {student_id: [module_codes where value=1]})."""
    with open(path, newline="") as fh:
        lines = fh.readlines()
    header = lines[0].rstrip("\n").split("\t")
    module_codes = header[1:]
    enrolments = {}
    for line in lines[1:]:
        fields = line.rstrip("\n").split("\t")
        student_id = fields[0]
        taken = [module_codes[i] for i, v in enumerate(fields[1:]) if v.strip() == "1"]
        enrolments[student_id] = taken
    return module_codes, enrolments


def build(matrix_path, credits_path, prereqs_path, coreqs_path, antireqs_path, db_path):
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)

    # Collect all module codes from all sources so the modules table is complete
    _, enrolments = read_matrix(matrix_path)
    credits_rows = read_tsv(credits_path)
    prereq_rows = read_tsv(prereqs_path)
    coreq_rows = read_tsv(coreqs_path)
    antireq_rows = read_tsv(antireqs_path)

    credits_map = {r["module"]: int(r["credits"]) for r in credits_rows}

    all_codes = set(credits_map.keys())
    for rows in (prereq_rows, coreq_rows, antireq_rows):
        for r in rows:
            all_codes.add(r["module"])
            all_codes.add(r["related_module"])
    for taken in enrolments.values():
        all_codes.update(taken)

    # Populate modules
    con.executemany(
        "INSERT OR IGNORE INTO modules (module_code, credits) VALUES (?, ?)",
        [(code, credits_map.get(code)) for code in sorted(all_codes)],
    )

    # Populate students
    con.executemany(
        "INSERT OR IGNORE INTO students (student_id) VALUES (?)",
        [(sid,) for sid in enrolments],
    )

    # Populate enrolments
    con.executemany(
        "INSERT OR IGNORE INTO enrolments (student_id, module_code) VALUES (?, ?)",
        [(sid, mod) for sid, mods in enrolments.items() for mod in mods],
    )

    # Populate requisite tables
    con.executemany(
        "INSERT OR IGNORE INTO prerequisites (module_code, requires) VALUES (?, ?)",
        [(r["module"], r["related_module"]) for r in prereq_rows],
    )
    con.executemany(
        "INSERT OR IGNORE INTO corequisites (module_code, requires) VALUES (?, ?)",
        [(r["module"], r["related_module"]) for r in coreq_rows],
    )
    con.executemany(
        "INSERT OR IGNORE INTO antirequisites (module_code, conflicts_with) VALUES (?, ?)",
        [(r["module"], r["related_module"]) for r in antireq_rows],
    )

    con.commit()
    con.close()

    print(f"Database built: {db_path}")
    print(f"  {len(all_codes)} modules")
    print(f"  {len(enrolments)} students")
    print(f"  {sum(len(v) for v in enrolments.values())} enrolments")
    print(f"  {len(prereq_rows)} prerequisites")
    print(f"  {len(coreq_rows)} corequisites")
    print(f"  {len(antireq_rows)} antirequisites")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the module choice SQLite database.")
    parser.add_argument("--matrix",   default="Data/Processed/AY25-26_processed.txt")
    parser.add_argument("--credits",  default="credits_processed.txt")
    parser.add_argument("--prereqs",  default="Data/Requisites/pre-requisites_processed.txt")
    parser.add_argument("--coreqs",   default="Data/Requisites/co-requisites_processed.txt")
    parser.add_argument("--antireqs", default="Data/Requisites/anti-requisites_processed.txt")
    parser.add_argument("--db",       default="module_choice.db")
    args = parser.parse_args()

    build(args.matrix, args.credits, args.prereqs, args.coreqs, args.antireqs, args.db)
