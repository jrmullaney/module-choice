"""
Unit tests for the module choice pipeline.
Run with:  python3 -m pytest test_pipeline.py -v
       or: python3 -m unittest test_pipeline -v
"""

import os
import tempfile
import unittest

from prefix_codes import extract_codes, prefix_code, process_file as prefix_process
from make_matrix import process_file as make_matrix
from merge_year import merge
from recode_modules import read_lookup, recode_matrix


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_tmp(content: str) -> str:
    """Write content to a named temp file and return its path."""
    fh = tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False)
    fh.write(content)
    fh.close()
    return fh.name


def read_tmp(path: str) -> str:
    with open(path) as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# prefix_codes
# ---------------------------------------------------------------------------

class TestPrefixCode(unittest.TestCase):

    def test_digit_start_gets_default_prefix(self):
        self.assertEqual(prefix_code("129"), "PHY129")

    def test_digit_start_gets_custom_prefix(self):
        self.assertEqual(prefix_code("129", prefix="MPS"), "MPS129")

    def test_letter_start_unchanged(self):
        self.assertEqual(prefix_code("EEE123"), "EEE123")

    def test_already_prefixed_unchanged(self):
        self.assertEqual(prefix_code("PHY129"), "PHY129")

    def test_empty_string_unchanged(self):
        self.assertEqual(prefix_code(""), "")

    def test_long_numeric_code(self):
        self.assertEqual(prefix_code("21004"), "PHY21004")


class TestExtractCodes(unittest.TestCase):

    def test_single_numeric_code(self):
        self.assertEqual(extract_codes("129"), ["PHY129"])

    def test_comma_separated_codes(self):
        self.assertEqual(extract_codes("111, 119"), ["PHY111", "PHY119"])

    def test_mixed_codes(self):
        self.assertEqual(extract_codes("EEE123, 104"), ["EEE123", "PHY104"])

    def test_placement_yr_ignored(self):
        self.assertEqual(extract_codes("Placement Yr"), [])

    def test_f_ignored(self):
        self.assertEqual(extract_codes("F"), [])

    def test_empty_cell(self):
        self.assertEqual(extract_codes(""), [])

    def test_custom_prefix(self):
        self.assertEqual(extract_codes("129, EEE123", prefix="MPS"), ["MPS129", "EEE123"])

    def test_whitespace_preserved_around_codes(self):
        result = extract_codes("  111 ,  119  ")
        self.assertEqual(result, ["PHY111", "PHY119"])


class TestPrefixProcessFile(unittest.TestCase):

    def setUp(self):
        self.out = tempfile.NamedTemporaryFile(suffix=".tsv", delete=False).name

    def tearDown(self):
        for path in [self.out]:
            if os.path.exists(path):
                os.unlink(path)

    def test_basic_processing(self):
        inp = write_tmp("230209417\t129\t11006\t111, 119\n")
        try:
            prefix_process(inp, self.out)
            result = read_tmp(self.out)
            self.assertEqual(result, "230209417\tPHY129\tPHY11006\tPHY111\tPHY119\n")
        finally:
            os.unlink(inp)

    def test_letter_codes_unchanged(self):
        inp = write_tmp("230209417\tEEE123\tMPY101\n")
        try:
            prefix_process(inp, self.out)
            result = read_tmp(self.out)
            self.assertEqual(result, "230209417\tEEE123\tMPY101\n")
        finally:
            os.unlink(inp)

    def test_ignored_values_dropped(self):
        inp = write_tmp("220167000\tPlacement Yr\n")
        try:
            prefix_process(inp, self.out)
            result = read_tmp(self.out)
            self.assertEqual(result, "220167000\n")
        finally:
            os.unlink(inp)

    def test_custom_prefix(self):
        inp = write_tmp("230209417\t129\tEEE123\n")
        try:
            prefix_process(inp, self.out, prefix="MPS")
            result = read_tmp(self.out)
            self.assertEqual(result, "230209417\tMPS129\tEEE123\n")
        finally:
            os.unlink(inp)


# ---------------------------------------------------------------------------
# make_matrix
# ---------------------------------------------------------------------------

class TestMakeMatrix(unittest.TestCase):

    def setUp(self):
        self.out = tempfile.NamedTemporaryFile(suffix=".tsv", delete=False).name

    def tearDown(self):
        if os.path.exists(self.out):
            os.unlink(self.out)

    def _run(self, content):
        inp = write_tmp(content)
        try:
            make_matrix(inp, self.out)
        finally:
            os.unlink(inp)
        rows = [line.split("\t") for line in read_tmp(self.out).splitlines()]
        return rows

    def test_header_sorted(self):
        rows = self._run(
            "111111\tPHY130\tPHY111\n"
            "222222\tPHY111\tPHY119\n"
        )
        self.assertEqual(rows[0], ["StudentID", "PHY111", "PHY119", "PHY130"])

    def test_presence_values(self):
        rows = self._run(
            "111111\tPHY111\tPHY130\n"
            "222222\tPHY111\tPHY119\n"
        )
        # Header: StudentID, PHY111, PHY119, PHY130
        self.assertEqual(rows[0], ["StudentID", "PHY111", "PHY119", "PHY130"])
        # Student 111111: PHY111=1, PHY119=0, PHY130=1
        self.assertEqual(rows[1], ["111111", "1", "0", "1"])
        # Student 222222: PHY111=1, PHY119=1, PHY130=0
        self.assertEqual(rows[2], ["222222", "1", "1", "0"])

    def test_student_with_no_modules(self):
        rows = self._run("111111\n")
        # Header has no module columns; student row has only ID
        self.assertEqual(rows[0], ["StudentID"])
        self.assertEqual(rows[1], ["111111"])


# ---------------------------------------------------------------------------
# merge_year
# ---------------------------------------------------------------------------

class TestMergeYear(unittest.TestCase):

    def setUp(self):
        self.out = tempfile.NamedTemporaryFile(suffix=".tsv", delete=False).name

    def tearDown(self):
        for path in [self.out]:
            if os.path.exists(path):
                os.unlink(path)

    def _merge(self, matrix_content, flat_content):
        matrix = write_tmp(matrix_content)
        flat = write_tmp(flat_content)
        try:
            merge(matrix, flat, self.out)
        finally:
            os.unlink(matrix)
            os.unlink(flat)
        rows = [line.split("\t") for line in read_tmp(self.out).splitlines()]
        return rows

    def test_returning_student_gains_new_module(self):
        rows = self._merge(
            "StudentID\tPHY111\tPHY130\n111111\t1\t0\n",
            "111111\tPHY130\n",
        )
        header = rows[0]
        student = dict(zip(header, rows[1]))
        self.assertEqual(student["PHY111"], "1")
        self.assertEqual(student["PHY130"], "1")

    def test_ones_never_become_zeros(self):
        rows = self._merge(
            "StudentID\tPHY111\tPHY130\n111111\t1\t1\n",
            "111111\tPHY130\n",   # PHY111 not in new year
        )
        header = rows[0]
        student = dict(zip(header, rows[1]))
        self.assertEqual(student["PHY111"], "1")

    def test_new_student_added(self):
        rows = self._merge(
            "StudentID\tPHY111\n111111\t1\n",
            "999999\tPHY111\n",
        )
        ids = [r[0] for r in rows[1:]]
        self.assertIn("999999", ids)

    def test_new_module_added_as_column(self):
        rows = self._merge(
            "StudentID\tPHY111\n111111\t1\n",
            "111111\tPHY130\n",
        )
        self.assertIn("PHY130", rows[0])

    def test_existing_student_gets_zero_for_new_module_they_didnt_take(self):
        rows = self._merge(
            "StudentID\tPHY111\n111111\t1\n",
            "999999\tPHY130\n",
        )
        header = rows[0]
        s1 = dict(zip(header, rows[1]))
        self.assertEqual(s1.get("PHY130", "0"), "0")


# ---------------------------------------------------------------------------
# recode_modules
# ---------------------------------------------------------------------------

class TestReadLookup(unittest.TestCase):

    def test_basic_lookup(self):
        inp = write_tmp("PHY111\tMPS119\nPHY130\tMPS107\n")
        try:
            lookup = read_lookup(inp)
        finally:
            os.unlink(inp)
        self.assertEqual(lookup["PHY111"], "MPS119")
        self.assertEqual(lookup["PHY130"], "MPS107")

    def test_multiline_old_code(self):
        # Two old codes in one quoted field, both map to same new code
        inp = write_tmp('"MLT107A\nMLT107B"\tLAS198\n')
        try:
            lookup = read_lookup(inp)
        finally:
            os.unlink(inp)
        self.assertEqual(lookup["MLT107A"], "LAS198")
        self.assertEqual(lookup["MLT107B"], "LAS198")


class TestRecodeMatrix(unittest.TestCase):

    def setUp(self):
        self.out = tempfile.NamedTemporaryFile(suffix=".tsv", delete=False).name

    def tearDown(self):
        if os.path.exists(self.out):
            os.unlink(self.out)

    def _recode(self, matrix_content, lookup_content):
        matrix = write_tmp(matrix_content)
        lookup = write_tmp(lookup_content)
        try:
            recode_matrix(matrix, lookup, self.out)
        finally:
            os.unlink(matrix)
            os.unlink(lookup)
        rows = [line.split("\t") for line in read_tmp(self.out).splitlines()]
        return rows

    def test_code_renamed(self):
        rows = self._recode(
            "StudentID\tPHY111\n111111\t1\n",
            "PHY111\tMPS119\n",
        )
        self.assertIn("MPS119", rows[0])
        self.assertNotIn("PHY111", rows[0])

    def test_code_not_in_lookup_preserved(self):
        rows = self._recode(
            "StudentID\tPHY111\tEEE123\n111111\t1\t1\n",
            "PHY111\tMPS119\n",
        )
        self.assertIn("EEE123", rows[0])

    def test_two_old_codes_merge_with_or(self):
        # PHY111 -> MPS119, PHY119 -> MPS119: student has PHY111=1, PHY119=0 -> MPS119=1
        rows = self._recode(
            "StudentID\tPHY111\tPHY119\n111111\t1\t0\n",
            "PHY111\tMPS119\nPHY119\tMPS119\n",
        )
        header = rows[0]
        student = dict(zip(header, rows[1]))
        self.assertEqual(student["MPS119"], "1")

    def test_or_merge_both_zero(self):
        rows = self._recode(
            "StudentID\tPHY111\tPHY119\n111111\t0\t0\n",
            "PHY111\tMPS119\nPHY119\tMPS119\n",
        )
        header = rows[0]
        student = dict(zip(header, rows[1]))
        self.assertEqual(student["MPS119"], "0")


if __name__ == "__main__":
    unittest.main()
