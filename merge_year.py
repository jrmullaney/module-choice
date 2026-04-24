"""
Merge a flattened year file into an existing presence matrix.

Run prefix_codes.py on each raw year file first, then use this script to
merge the result into the matrix.

Rules:
  - 0 -> 1 allowed (student took a new module)
  - 1 -> 0 never happens (historical record is preserved)
  - New module codes are added as extra columns (existing students get 0)
  - New students are added as extra rows

Usage:  python3 merge_year.py <existing_matrix> <flat_year_file> <output_file>

        existing_matrix  — tab-separated presence matrix (e.g. AY23-24_processed.txt)
        flat_year_file   — flattened output from prefix_codes.py (e.g. AY24-25.flat.tsv)
        output_file      — where to write the merged matrix
"""

import sys


def read_matrix(path: str) -> tuple[list[str], dict[str, dict[str, int]]]:
    """Read an existing matrix. Returns (module codes, {student_id: {code: 0/1}})."""
    with open(path, "r", newline="") as fh:
        lines = fh.readlines()

    header = lines[0].rstrip("\n").split("\t")
    module_codes = header[1:]

    matrix = {}
    for line in lines[1:]:
        fields = line.rstrip("\n").split("\t")
        student_id = fields[0]
        matrix[student_id] = {
            code: int(val)
            for code, val in zip(module_codes, fields[1:])
        }

    return module_codes, matrix


def read_flat_year(path: str) -> dict[str, set[str]]:
    """Read a flattened year file. Returns {student_id: set of module codes}."""
    with open(path, "r", newline="") as fh:
        lines = fh.readlines()

    students = {}
    for line in lines:
        fields = line.rstrip("\n").split("\t")
        if not fields[0].strip():
            continue
        student_id = fields[0].strip()
        students[student_id] = {f for f in fields[1:] if f.strip()}

    return students


def merge(matrix_path: str, flat_year_path: str, output_path: str) -> None:
    existing_codes, matrix = read_matrix(matrix_path)
    new_year = read_flat_year(flat_year_path)

    all_new_codes = {code for codes in new_year.values() for code in codes}
    all_codes = sorted(set(existing_codes) | all_new_codes)

    returning = len(set(new_year) & set(matrix))
    n_new_students = len(set(new_year) - set(matrix))
    n_new_cols = len(set(all_codes) - set(existing_codes))

    for student_id, codes in new_year.items():
        if student_id not in matrix:
            matrix[student_id] = {}
        for code in codes:
            matrix[student_id][code] = 1

    output_lines = ["\t".join(["StudentID"] + all_codes) + "\n"]
    for student_id, row in matrix.items():
        values = [str(row.get(code, 0)) for code in all_codes]
        output_lines.append("\t".join([student_id] + values) + "\n")

    with open(output_path, "w", newline="") as fh:
        fh.writelines(output_lines)

    print(f"{returning} returning students, {n_new_students} new students")
    print(f"{n_new_cols} new module codes added")
    print(f"Matrix: {len(matrix)} students x {len(all_codes)} modules -> {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    merge(sys.argv[1], sys.argv[2], sys.argv[3])
