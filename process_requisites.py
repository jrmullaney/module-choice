"""
Process a two-row requisite file into a long-format TSV suitable for database import.

Input file format (tab-separated, two rows):
  Row 1: module codes (the modules in question)
  Row 2: related module codes (prerequisites, corequisites, or antirequisites)

Processing rules:
  Row 1: digit-only codes get MPS prefix; letter-starting codes are checked
         against the new codes in the lookup table and warned if absent.
  Row 2: digit-only codes get PHY prefix; all codes are then converted to
         MPS via the lookup table; codes not in the lookup are warned about.

Output format (tab-separated, one pair per row):
  module  related_module

Usage:  python3 process_requisites.py <input_file> <lookup_file> <output_file>
"""

import csv
import sys


def read_lookup(path: str) -> tuple[dict[str, str], set[str]]:
    """Return (old_to_new, new_codes) from the lookup table."""
    old_to_new = {}
    new_codes = set()
    with open(path, newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        for row in reader:
            if len(row) < 2:
                continue
            old_field = row[0].strip()
            new_code = row[1].strip()
            if new_code:
                new_codes.add(new_code)
            for code in old_field.splitlines():
                code = code.strip()
                if code:
                    old_to_new[code] = new_code
    return old_to_new, new_codes


def apply_prefix(code: str, prefix: str) -> str:
    stripped = code.strip()
    if stripped and stripped[0].isdigit():
        return prefix + stripped
    return stripped


def process_file(input_path: str, lookup_path: str, output_path: str) -> None:
    old_to_new, new_codes = read_lookup(lookup_path)

    with open(input_path, newline="") as fh:
        rows = [line.rstrip("\n").split("\t") for line in fh.readlines()]

    if len(rows) != 2:
        print(f"ERROR: expected 2 rows, got {len(rows)}")
        sys.exit(1)

    modules_raw = rows[0]
    related_raw = rows[1]

    if len(modules_raw) != len(related_raw):
        print(f"ERROR: row 1 has {len(modules_raw)} columns, row 2 has {len(related_raw)}")
        sys.exit(1)

    # Validate row 1 letter-starting codes against new_codes in lookup
    for code in modules_raw:
        code = code.strip()
        if code and not code[0].isdigit() and code not in new_codes:
            print(f"WARNING: row 1 code '{code}' not found in lookup new codes")

    pairs = []
    lookup_warnings = set()

    for mod_raw, rel_raw in zip(modules_raw, related_raw):
        mod_raw = mod_raw.strip()
        rel_raw = rel_raw.strip()

        if not mod_raw or not rel_raw:
            continue

        module = apply_prefix(mod_raw, "MPS")

        # Apply PHY prefix to digit-only row 2 codes, then look up
        related_prefixed = apply_prefix(rel_raw, "PHY")
        related = old_to_new.get(related_prefixed)
        if related is None:
            if related_prefixed not in lookup_warnings:
                print(f"WARNING: prerequisite '{related_prefixed}' not found in lookup table")
                lookup_warnings.add(related_prefixed)
            continue

        pairs.append((module, related))

    # Deduplicate while preserving order
    seen = set()
    unique_pairs = []
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            unique_pairs.append(pair)

    with open(output_path, "w", newline="") as fh:
        fh.write("module\trelated_module\n")
        for module, related in unique_pairs:
            fh.write(f"{module}\t{related}\n")

    print(f"{len(unique_pairs)} relationships written to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    process_file(sys.argv[1], sys.argv[2], sys.argv[3])
