"""
Step 2: Build a student × module presence matrix from flattened module data.

Input:  tab-separated file where:
          column 0  — student ID
          columns 1+ — one module code per column

Output: tab-separated grid where:
          row 0     — header: StudentID, then one column per unique module code (sorted)
          rows 1+   — student ID, then 1/0 for each module code

Usage:  python3 make_matrix.py <input_file> <output_file>
        If output_file is omitted, the input file is overwritten.
"""

import sys


def process_file(input_path: str, output_path: str) -> None:
    with open(input_path, "r", newline="") as fh:
        lines = fh.readlines()

    rows = []
    for line in lines:
        fields = line.rstrip("\n").split("\t")
        if not fields[0].strip():
            continue
        student_id = fields[0].strip()
        codes = [f for f in fields[1:] if f.strip()]
        rows.append((student_id, codes))

    all_codes = sorted({code for _, codes in rows for code in codes})

    output_lines = ["\t".join(["StudentID"] + all_codes) + "\n"]
    for student_id, codes in rows:
        taken = set(codes)
        values = [str(int(code in taken)) for code in all_codes]
        output_lines.append("\t".join([student_id] + values) + "\n")

    with open(output_path, "w", newline="") as fh:
        fh.writelines(output_lines)

    print(f"{len(rows)} students, {len(all_codes)} unique module codes -> {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file
    process_file(input_file, output_file)
