"""
Process a two-row credits file into a long-format TSV suitable for database import.

Input file format (tab-separated, two rows):
  Row 1: module codes
  Row 2: credit values

Processing rules:
  Row 1: digit-only codes get MPS prefix; letter-starting codes are checked
         against the new codes in the lookup table and warned if absent.
  Row 2: values are kept as-is.

Output format (tab-separated, with header):
  module  credits

Usage:  python3 process_credits.py <input_file> <lookup_file> <output_file>
"""

import csv
import sys


def read_new_codes(lookup_path: str) -> set[str]:
    """Return the set of new codes (column 2) from the lookup table."""
    new_codes = set()
    with open(lookup_path, newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        for row in reader:
            if len(row) >= 2 and row[1].strip():
                new_codes.add(row[1].strip())
    return new_codes


def apply_prefix(code: str, prefix: str = "MPS") -> str:
    stripped = code.strip()
    if stripped and stripped[0].isdigit():
        return prefix + stripped
    return stripped


def process_file(input_path: str, lookup_path: str, output_path: str) -> None:
    new_codes = read_new_codes(lookup_path)

    with open(input_path, newline="") as fh:
        rows = [line.rstrip("\n").split("\t") for line in fh.readlines()]

    if len(rows) != 2:
        print(f"ERROR: expected 2 rows, got {len(rows)}")
        sys.exit(1)

    modules_raw = rows[0]
    credits_raw = rows[1]

    if len(modules_raw) != len(credits_raw):
        print(f"ERROR: row 1 has {len(modules_raw)} columns, row 2 has {len(credits_raw)}")
        sys.exit(1)

    pairs = []
    for mod_raw, credit_raw in zip(modules_raw, credits_raw):
        mod_raw = mod_raw.strip()
        credit_raw = credit_raw.strip()

        if not mod_raw or not credit_raw:
            continue

        module = apply_prefix(mod_raw)

        if not mod_raw[0].isdigit() and module not in new_codes:
            print(f"WARNING: '{module}' not found in lookup new codes")

        pairs.append((module, credit_raw))

    with open(output_path, "w", newline="") as fh:
        fh.write("module\tcredits\n")
        for module, credits in pairs:
            fh.write(f"{module}\t{credits}\n")

    print(f"{len(pairs)} modules written to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    process_file(sys.argv[1], sys.argv[2], sys.argv[3])
