"""
Pipeline: run prefix_codes then make_matrix in one step.

Usage:  python3 process_modules.py <input_file> <output_file>
        Intermediate flattened data is written to <input_file>.flat.tsv.
"""

import sys
from pathlib import Path

import prefix_codes
import make_matrix


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    intermediate = str(Path(input_file).with_suffix(".flat.tsv"))

    prefix_codes.process_file(input_file, intermediate)
    make_matrix.process_file(intermediate, output_file)
