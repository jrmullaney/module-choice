"""
Unit tests for the module choice pipeline.
Run with:  python3 -m pytest test_pipeline.py -v
       or: python3 -m unittest test_pipeline -v
"""

import os
import sqlite3
import tempfile
import unittest

from prefix_codes import extract_codes, prefix_code, process_file as prefix_process
from make_matrix import process_file as make_matrix
from merge_year import merge
from recode_modules import read_lookup, recode_matrix
from process_requisites import process_file as process_requisites
from process_credits import process_file as process_credits
from validate_choices import validate_choices
from build_db import SCHEMA


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


# ---------------------------------------------------------------------------
# process_requisites
# ---------------------------------------------------------------------------

class TestProcessRequisites(unittest.TestCase):

    def setUp(self):
        self.out = tempfile.NamedTemporaryFile(suffix=".tsv", delete=False).name

    def tearDown(self):
        if os.path.exists(self.out):
            os.unlink(self.out)

    def _run(self, requisite_content, lookup_content):
        req = write_tmp(requisite_content)
        lookup = write_tmp(lookup_content)
        try:
            process_requisites(req, lookup, self.out)
        finally:
            os.unlink(req)
            os.unlink(lookup)
        rows = [line.split("\t") for line in read_tmp(self.out).splitlines()]
        return rows

    def test_digit_module_gets_mps_prefix(self):
        rows = self._run(
            "213\n"
            "104\n",
            "PHY104\tMPS118\n",
        )
        modules = [r[0] for r in rows[1:]]
        self.assertIn("MPS213", modules)

    def test_digit_prereq_gets_phy_then_looked_up(self):
        rows = self._run(
            "213\n"
            "104\n",
            "PHY104\tMPS118\n",
        )
        self.assertEqual(rows[1], ["MPS213", "MPS118"])

    def test_letter_prereq_looked_up(self):
        rows = self._run(
            "222\n"
            "MAS108\n",
            "MAS108\tMPS125\n",
        )
        self.assertEqual(rows[1], ["MPS222", "MPS125"])

    def test_empty_prereq_skipped(self):
        rows = self._run(
            "213\t227\n"
            "104\t\n",
            "PHY104\tMPS118\n",
        )
        # Only the non-empty pair should appear
        self.assertEqual(len(rows), 2)  # header + 1 pair

    def test_duplicate_pairs_deduplicated(self):
        rows = self._run(
            "213\t213\n"
            "104\t104\n",
            "PHY104\tMPS118\n",
        )
        self.assertEqual(len(rows), 2)  # header + 1 unique pair

    def test_header_row_present(self):
        rows = self._run("213\n104\n", "PHY104\tMPS118\n")
        self.assertEqual(rows[0], ["module", "related_module"])

    def test_prereq_not_in_lookup_skipped(self):
        # PHY999 not in lookup — pair should be skipped
        rows = self._run("213\n999\n", "PHY104\tMPS118\n")
        self.assertEqual(len(rows), 1)  # header only


# ---------------------------------------------------------------------------
# process_credits
# ---------------------------------------------------------------------------

class TestProcessCredits(unittest.TestCase):

    def setUp(self):
        self.out = tempfile.NamedTemporaryFile(suffix=".tsv", delete=False).name

    def tearDown(self):
        if os.path.exists(self.out):
            os.unlink(self.out)

    def _run(self, credits_content, lookup_content):
        cred = write_tmp(credits_content)
        lookup = write_tmp(lookup_content)
        try:
            process_credits(cred, lookup, self.out)
        finally:
            os.unlink(cred)
            os.unlink(lookup)
        rows = [line.split("\t") for line in read_tmp(self.out).splitlines()]
        return rows

    def test_digit_code_gets_mps_prefix(self):
        rows = self._run("213\n20\n", "PHY213\tMPS213\n")
        self.assertEqual(rows[1][0], "MPS213")

    def test_credit_value_preserved(self):
        rows = self._run("213\n20\n", "PHY213\tMPS213\n")
        self.assertEqual(rows[1][1], "20")

    def test_letter_code_unchanged(self):
        rows = self._run("CMB124\n10\n", "MPY101\tCMB124\n")
        self.assertEqual(rows[1][0], "CMB124")

    def test_header_row_present(self):
        rows = self._run("213\n20\n", "PHY213\tMPS213\n")
        self.assertEqual(rows[0], ["module", "credits"])

    def test_empty_cells_skipped(self):
        rows = self._run("213\t\n20\t\n", "PHY213\tMPS213\n")
        self.assertEqual(len(rows), 2)  # header + 1 entry

    def test_multiple_modules(self):
        rows = self._run(
            "213\t222\n"
            "20\t10\n",
            "PHY213\tMPS213\nPHY222\tMPS222\n",
        )
        self.assertEqual(len(rows), 3)  # header + 2 entries


# ---------------------------------------------------------------------------
# validate_choices
# ---------------------------------------------------------------------------

def make_test_db(students, modules, enrolments, prerequisites=None,
                 corequisites=None, antirequisites=None):
    """Build an in-memory SQLite database and return its path (a temp file)."""
    import tempfile
    db_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO modules VALUES (?,?)", modules)
    con.executemany("INSERT INTO students (student_id) VALUES (?)", [(s,) for s in students])
    con.executemany("INSERT INTO enrolments VALUES (?,?)", enrolments)
    if prerequisites:
        con.executemany("INSERT INTO prerequisites VALUES (?,?)", prerequisites)
    if corequisites:
        con.executemany("INSERT INTO corequisites VALUES (?,?)", corequisites)
    if antirequisites:
        con.executemany("INSERT INTO antirequisites VALUES (?,?)", antirequisites)
    con.commit()
    con.close()
    return db_path


class TestValidateChoices(unittest.TestCase):

    def _result(self, db, student, modules):
        return validate_choices(db, student, modules)

    def _status(self, result, module):
        return next(r for r in result["modules"] if r["module_code"] == module)

    def test_approved_module_with_no_restrictions(self):
        db = make_test_db(
            students=["S1"],
            modules=[("MPS101", 20)],
            enrolments=[],
        )
        try:
            result = self._result(db, "S1", ["MPS101"])
            self.assertEqual(self._status(result, "MPS101")["status"], "approved")
        finally:
            os.unlink(db)

    def test_already_taken_rejected(self):
        db = make_test_db(
            students=["S1"],
            modules=[("MPS101", 20)],
            enrolments=[("S1", "MPS101")],
        )
        try:
            result = self._result(db, "S1", ["MPS101"])
            self.assertEqual(self._status(result, "MPS101")["status"], "rejected")
        finally:
            os.unlink(db)

    def test_prerequisite_not_met_rejected(self):
        db = make_test_db(
            students=["S1"],
            modules=[("MPS101", 20), ("MPS201", 20)],
            enrolments=[],
            prerequisites=[("MPS201", "MPS101")],
        )
        try:
            result = self._result(db, "S1", ["MPS201"])
            self.assertEqual(self._status(result, "MPS201")["status"], "rejected")
        finally:
            os.unlink(db)

    def test_prerequisite_met_approved(self):
        db = make_test_db(
            students=["S1"],
            modules=[("MPS101", 20), ("MPS201", 20)],
            enrolments=[("S1", "MPS101")],
            prerequisites=[("MPS201", "MPS101")],
        )
        try:
            result = self._result(db, "S1", ["MPS201"])
            self.assertEqual(self._status(result, "MPS201")["status"], "approved")
        finally:
            os.unlink(db)

    def test_antirequisite_history_clash_rejected(self):
        db = make_test_db(
            students=["S1"],
            modules=[("MPS101", 20), ("MPS102", 20)],
            enrolments=[("S1", "MPS101")],
            antirequisites=[("MPS101", "MPS102")],
        )
        try:
            result = self._result(db, "S1", ["MPS102"])
            self.assertEqual(self._status(result, "MPS102")["status"], "rejected")
        finally:
            os.unlink(db)

    def test_antirequisite_current_choices_clash_rejected(self):
        db = make_test_db(
            students=["S1"],
            modules=[("MPS101", 20), ("MPS102", 20)],
            enrolments=[],
            antirequisites=[("MPS101", "MPS102")],
        )
        try:
            result = self._result(db, "S1", ["MPS101", "MPS102"])
            statuses = {r["module_code"]: r["status"] for r in result["modules"]}
            # At least one of the pair must be rejected
            self.assertIn("rejected", statuses.values())
        finally:
            os.unlink(db)

    def test_corequisite_satisfied_by_enrolment(self):
        db = make_test_db(
            students=["S1"],
            modules=[("MPS101", 20), ("MPS201", 20)],
            enrolments=[("S1", "MPS101")],
            corequisites=[("MPS201", "MPS101")],
        )
        try:
            result = self._result(db, "S1", ["MPS201"])
            self.assertEqual(self._status(result, "MPS201")["status"], "approved")
        finally:
            os.unlink(db)

    def test_corequisite_satisfied_by_current_choice(self):
        db = make_test_db(
            students=["S1"],
            modules=[("MPS101", 20), ("MPS201", 20)],
            enrolments=[],
            corequisites=[("MPS201", "MPS101")],
        )
        try:
            result = self._result(db, "S1", ["MPS101", "MPS201"])
            self.assertEqual(self._status(result, "MPS201")["status"], "approved")
        finally:
            os.unlink(db)

    def test_corequisite_not_satisfied_rejected(self):
        db = make_test_db(
            students=["S1"],
            modules=[("MPS101", 20), ("MPS201", 20)],
            enrolments=[],
            corequisites=[("MPS201", "MPS101")],
        )
        try:
            result = self._result(db, "S1", ["MPS201"])
            self.assertEqual(self._status(result, "MPS201")["status"], "rejected")
        finally:
            os.unlink(db)

    def test_credit_total_correct(self):
        db = make_test_db(
            students=["S1"],
            modules=[("MPS101", 20), ("MPS102", 10)],
            enrolments=[],
        )
        try:
            result = self._result(db, "S1", ["MPS101", "MPS102"])
            self.assertEqual(result["total_credits"], 30)
        finally:
            os.unlink(db)

    def test_credit_limit_exceeded_flagged(self):
        modules = [(f"MPS{i}", 20) for i in range(1, 8)]  # 7 x 20 = 140 credits
        db = make_test_db(
            students=["S1"],
            modules=modules,
            enrolments=[],
        )
        try:
            result = self._result(db, "S1", [m[0] for m in modules])
            self.assertTrue(result["credit_limit_exceeded"])
        finally:
            os.unlink(db)

    def test_credit_limit_not_exceeded(self):
        modules = [(f"MPS{i}", 20) for i in range(1, 7)]  # 6 x 20 = 120 credits
        db = make_test_db(
            students=["S1"],
            modules=modules,
            enrolments=[],
        )
        try:
            result = self._result(db, "S1", [m[0] for m in modules])
            self.assertFalse(result["credit_limit_exceeded"])
        finally:
            os.unlink(db)

    def test_unknown_module_rejected(self):
        db = make_test_db(students=["S1"], modules=[], enrolments=[])
        try:
            result = self._result(db, "S1", ["MPS999"])
            self.assertIn("MPS999", result["unknown_modules"])
            self.assertEqual(self._status(result, "MPS999")["status"], "rejected")
        finally:
            os.unlink(db)

    def test_unknown_student_raises(self):
        db = make_test_db(students=[], modules=[("MPS101", 20)], enrolments=[])
        try:
            with self.assertRaises(ValueError):
                self._result(db, "NOBODY", ["MPS101"])
        finally:
            os.unlink(db)

    def test_credits_shown_per_module(self):
        db = make_test_db(
            students=["S1"],
            modules=[("MPS101", 20)],
            enrolments=[],
        )
        try:
            result = self._result(db, "S1", ["MPS101"])
            self.assertEqual(self._status(result, "MPS101")["credits"], 20)
        finally:
            os.unlink(db)


if __name__ == "__main__":
    unittest.main()
