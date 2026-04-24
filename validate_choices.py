"""
Validate a student's proposed module choices against the database rules.

Checks (in order):
  1. Module not already taken
  2. All prerequisites met (from enrolments)
  3. No antirequisites conflict (enrolments or current choices)
  4. All corequisites satisfied (enrolments or current choices)
  5. Total credits of approved choices do not exceed 120

Usage:  python3 validate_choices.py <db> <student_id> <module1> [module2 ...]

Example:
  python3 validate_choices.py module_choice.db 230209417 MPS213 MPS222 MPS361
"""

import sqlite3
import sys


def validate_choices(db_path: str, student_id: str, proposed: list[str]) -> dict:
    """
    Validate proposed module choices for a student.

    Returns a dict:
      {
        "modules": [{"module_code": ..., "status": "approved"|"rejected", "reason": ...}, ...],
        "total_credits": int,
        "credit_limit_exceeded": bool,
        "unknown_modules": [...]   # codes not found in the database
      }
    """
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    # Verify student exists
    student = con.execute(
        "SELECT student_id FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    if not student:
        con.close()
        raise ValueError(f"Student '{student_id}' not found in database")

    # Check for unknown module codes
    proposed_set = set(proposed)
    known = {
        row["module_code"]
        for row in con.execute(
            f"SELECT module_code FROM modules WHERE module_code IN ({','.join('?'*len(proposed))})",
            proposed,
        )
    }
    unknown = sorted(proposed_set - known)

    # Student's historical enrolments
    enrolments = {
        row["module_code"]
        for row in con.execute(
            "SELECT module_code FROM enrolments WHERE student_id = ?", (student_id,)
        )
    }

    results = []

    for module in proposed:
        if module in unknown:
            results.append({
                "module_code": module,
                "status": "rejected",
                "reason": "Module not found in database",
            })
            continue

        status = "approved"
        reason = None

        # Rule 1: already taken
        if module in enrolments:
            status, reason = "rejected", "Already taken"

        # Rule 2: prerequisites must be in enrolments
        if status == "approved":
            prereqs = {
                row["requires"]
                for row in con.execute(
                    "SELECT requires FROM prerequisites WHERE module_code = ?", (module,)
                )
            }
            missing = prereqs - enrolments
            if missing:
                status = "rejected"
                reason = f"Prerequisites not met: {', '.join(sorted(missing))}"

        # Rule 3: antirequisites must not be in enrolments or current choices
        if status == "approved":
            antireqs = {
                row["conflicts_with"]
                for row in con.execute(
                    "SELECT conflicts_with FROM antirequisites WHERE module_code = ?", (module,)
                )
            }
            # Check both directions
            antireqs |= {
                row["module_code"]
                for row in con.execute(
                    "SELECT module_code FROM antirequisites WHERE conflicts_with = ?", (module,)
                )
            }
            antireqs.discard(module)
            history_clash = antireqs & enrolments
            current_clash = antireqs & proposed_set - {module}
            if history_clash:
                status = "rejected"
                reason = f"Conflicts with previously taken: {', '.join(sorted(history_clash))}"
            elif current_clash:
                status = "rejected"
                reason = f"Conflicts with another current choice: {', '.join(sorted(current_clash))}"

        # Rule 4: corequisites must be in enrolments or current choices
        if status == "approved":
            coreqs = {
                row["requires"]
                for row in con.execute(
                    "SELECT requires FROM corequisites WHERE module_code = ?", (module,)
                )
            }
            missing_co = coreqs - enrolments - proposed_set
            if missing_co:
                status = "rejected"
                reason = f"Corequisites not satisfied: {', '.join(sorted(missing_co))}"

        # Look up credits for this module
        credits_row = con.execute(
            "SELECT credits FROM modules WHERE module_code = ?", (module,)
        ).fetchone()
        credits = credits_row["credits"] if credits_row else None

        results.append({"module_code": module, "status": status, "reason": reason, "credits": credits})

    # Rule 5: total credits of approved choices
    total_credits = sum(r["credits"] or 0 for r in results if r["status"] == "approved")

    con.close()

    return {
        "modules": results,
        "total_credits": total_credits,
        "credit_limit_exceeded": total_credits > 120,
        "unknown_modules": unknown,
    }


def print_results(student_id: str, result: dict) -> None:
    print(f"\nValidation results for student {student_id}")
    print("-" * 50)
    for r in result["modules"]:
        mark = "✓" if r["status"] == "approved" else "✗"
        credits_str = f"({r['credits']} credits)" if r["credits"] is not None else "(credits unknown)"
        line = f"  {mark} {r['module_code']} {credits_str}"
        if r["reason"]:
            line += f"  —  {r['reason']}"
        print(line)
    print("-" * 50)
    print(f"  Total credits (approved): {result['total_credits']}")
    if result["credit_limit_exceeded"]:
        print("  WARNING: credit total exceeds 120")
    if result["unknown_modules"]:
        print(f"  Unknown module codes: {', '.join(result['unknown_modules'])}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    db = sys.argv[1]
    student = sys.argv[2]
    modules = sys.argv[3:]

    result = validate_choices(db, student, modules)
    print_results(student, result)
