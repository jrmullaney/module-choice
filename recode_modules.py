"""
Rename module codes in a presence matrix using a lookup table.

Codes not present in the lookup are left unchanged. If two old codes map to
the same new code, their columns are merged with OR (1 wins over 0).

Usage:  python3 recode_modules.py <matrix_file> <lookup_file> <output_file>

        matrix_file  — tab-separated presence matrix
        lookup_file  — tab-separated file: old_code<TAB>new_code
                       (multi-line quoted old codes are supported)
        output_file  — where to write the recoded matrix
"""

import csv
import sys
from collections import defaultdict


def read_lookup(path: str) -> dict[str, str]:
    """Return {old_code: new_code}. Handles multi-line old-code entries."""
    lookup = {}
    with open(path, newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        for row in reader:
            if len(row) < 2:
                continue
            old_field = row[0].strip()
            new_code = row[1].strip()
            for code in old_field.splitlines():
                code = code.strip()
                if code:
                    lookup[code] = new_code
    return lookup


def recode_matrix(matrix_path: str, lookup_path: str, output_path: str) -> None:
    lookup = read_lookup(lookup_path)

    with open(matrix_path, "r", newline="") as fh:
        lines = fh.readlines()

    header = lines[0].rstrip("\n").split("\t")
    old_codes = header[1:]
    new_codes = [lookup.get(code, code) for code in old_codes]

    # Map each unique new code to all old column indices that feed into it
    new_code_to_old_indices = defaultdict(list)
    for i, new_code in enumerate(new_codes):
        new_code_to_old_indices[new_code].append(i)

    unique_new_codes = sorted(new_code_to_old_indices.keys())

    output_lines = ["\t".join(["StudentID"] + unique_new_codes) + "\n"]

    for line in lines[1:]:
        fields = line.rstrip("\n").split("\t")
        student_id = fields[0]
        old_values = [int(v) for v in fields[1:]]

        # OR together any columns that merge into the same new code
        new_row = {
            new_code: str(max(
                (old_values[i] for i in indices if i < len(old_values)),
                default=0
            ))
            for new_code, indices in new_code_to_old_indices.items()
        }
        output_lines.append("\t".join([student_id] + [new_row[c] for c in unique_new_codes]) + "\n")

    with open(output_path, "w", newline="") as fh:
        fh.writelines(output_lines)

    renamed = sum(1 for old, new in zip(old_codes, new_codes) if old != new)
    merged = len(old_codes) - len(unique_new_codes)
    not_in_lookup = sorted(code for code in old_codes if code not in lookup)

    if not_in_lookup:
        print(f"WARNING: {len(not_in_lookup)} code(s) not found in lookup table (left unchanged):")
        for code in not_in_lookup:
            print(f"  {code}")
    else:
        print("All codes found in lookup table.")

    print(f"{renamed} codes renamed, {len(old_codes) - renamed} unchanged, {merged} columns merged")
    print(f"Matrix: {len(lines) - 1} students x {len(unique_new_codes)} modules -> {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    recode_matrix(sys.argv[1], sys.argv[2], sys.argv[3])
