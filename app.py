"""
Flask web app for student module choice validation.

Routes:
  GET  /              — home page
  POST /validate      — single-student validation
  GET  /bulk          — bulk upload form
  POST /bulk          — process uploaded TSV
  GET  /student/<id>  — student enrolment history

Usage:
  conda activate ModuleChoice
  python3 app.py
"""

import csv
import io
import os
import sqlite3

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from validate_choices import validate_choices

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

DB_PATH = os.environ.get("DB_PATH", "module_choice.db")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/validate", methods=["GET", "POST"])
def validate():
    if request.method == "GET":
        return render_template("validate.html")

    student_id = request.form.get("student_id", "").strip()
    modules_raw = request.form.get("modules", "").strip()

    if not student_id or not modules_raw:
        flash("Please enter both a student ID and at least one module code.", "warning")
        return render_template("validate.html", student_id=student_id, modules_raw=modules_raw)

    modules = [m.strip().upper() for m in modules_raw.replace(",", " ").split() if m.strip()]

    try:
        result = validate_choices(DB_PATH, student_id, modules)
    except ValueError as exc:
        flash(str(exc), "danger")
        return render_template("validate.html", student_id=student_id, modules_raw=modules_raw)

    return render_template("validate.html", student_id=student_id, modules_raw=modules_raw, result=result)


@app.route("/bulk", methods=["GET", "POST"])
def bulk():
    if request.method == "GET":
        return render_template("bulk.html")

    uploaded = request.files.get("file")
    if not uploaded or uploaded.filename == "":
        flash("Please select a file to upload.", "warning")
        return render_template("bulk.html")

    try:
        content = uploaded.read().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content), delimiter="\t")
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    except Exception as exc:
        flash(f"Could not read file: {exc}", "danger")
        return render_template("bulk.html")

    if not rows:
        flash("The uploaded file appears to be empty.", "warning")
        return render_template("bulk.html")

    results = []
    errors = []

    for i, row in enumerate(rows, start=1):
        if not row:
            continue
        student_id = row[0].strip()
        modules = [c.strip().upper() for c in row[1:] if c.strip()]
        if not student_id:
            continue
        if not modules:
            errors.append(f"Row {i}: student {student_id} has no module codes")
            continue
        try:
            res = validate_choices(DB_PATH, student_id, modules)
            results.append({"student_id": student_id, "result": res})
        except ValueError as exc:
            errors.append(f"Row {i}: {exc}")

    if not results and not errors:
        flash("No valid rows found in the file.", "warning")
        return render_template("bulk.html")

    return render_template("bulk.html", results=results, errors=errors)


@app.route("/search")
def search():
    student_id = request.args.get("student_id", "").strip()
    if not student_id:
        return redirect(url_for("index"))
    con = sqlite3.connect(DB_PATH)
    found = con.execute(
        "SELECT 1 FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    con.close()
    if not found:
        return redirect(url_for("index", student_id=student_id, error="not_found"))
    return redirect(url_for("student", student_id=student_id))


@app.route("/student/<student_id>")
def student(student_id):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    row = con.execute(
        "SELECT student_id FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    if not row:
        con.close()
        abort(404)

    enrolments = con.execute(
        """SELECT e.module_code, m.credits
           FROM enrolments e
           LEFT JOIN modules m ON m.module_code = e.module_code
           WHERE e.student_id = ?
           ORDER BY e.module_code""",
        (student_id,),
    ).fetchall()

    total_credits = sum(r["credits"] or 0 for r in enrolments)
    con.close()

    return render_template(
        "student.html",
        student_id=student_id,
        enrolments=enrolments,
        total_credits=total_credits,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
