"""
Step 1: Prepend a prefix to module codes that don't start with a letter, and
        expand comma-separated codes into individual tab-separated columns.

Input:  tab-separated file where:
          column 0  — student ID
          columns 1+ — module code fields (one or more comma-separated codes per cell)

Output: tab-separated file where:
          column 0  — student ID
          columns 1+ — one module code per column (no commas)

Usage:  python3 prefix_codes.py <input_file> <output_file> [--prefix PREFIX]
        PREFIX defaults to PHY if not specified.
        If output_file is omitted, the input file is overwritten.
"""

import sys

IGNORE = {"Placement Yr", "F"}


def prefix_code(code: str, prefix: str = "PHY") -> str:
    stripped = code.strip()
    if stripped and stripped[0].isdigit():
        return prefix + stripped
    return stripped


def extract_codes(cell: str, prefix: str = "PHY") -> list[str]:
    return [
        prefix_code(part, prefix)
        for part in cell.split(",")
        if part.strip() and part.strip() not in IGNORE
    ]


def process_file(input_path: str, output_path: str, prefix: str = "PHY") -> None:
    with open(input_path, "r", newline="") as fh:
        lines = fh.readlines()

    output_lines = []
    for line in lines:
        fields = line.rstrip("\n").split("\t")
        if not fields[0].strip():
            continue
        codes = []
        for cell in fields[1:]:
            codes.extend(extract_codes(cell, prefix))
        output_lines.append("\t".join([fields[0].strip()] + codes) + "\n")

    with open(output_path, "w", newline="") as fh:
        fh.writelines(output_lines)

    print(f"{len(output_lines)} rows written to {output_path}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    prefix = "PHY"
    for i, a in enumerate(sys.argv[1:]):
        if a == "--prefix" and i + 2 < len(sys.argv):
            prefix = sys.argv[i + 2]

    if len(args) < 1:
        print(__doc__)
        sys.exit(1)

    input_file = args[0]
    output_file = args[1] if len(args) > 1 else args[0]
    process_file(input_file, output_file, prefix)
