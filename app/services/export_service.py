from app.db import get_db_session
from app.models import Assessment, JournalEntry
from app.report_engine import generate_pdf_report
import csv
import os
import json
from io import StringIO


# -----------------------------
# DATA COLLECTION
# -----------------------------
def collect_user_data(user_id, start_date=None, end_date=None):
    session = get_db_session()

    query_assess = session.query(Assessment).filter_by(user_id=user_id)
    query_journal = session.query(JournalEntry).filter_by(user_id=user_id)

    if start_date:
        query_assess = query_assess.filter(Assessment.date >= start_date)
        query_journal = query_journal.filter(JournalEntry.date >= start_date)

    if end_date:
        query_assess = query_assess.filter(Assessment.date <= end_date)
        query_journal = query_journal.filter(JournalEntry.date <= end_date)

    assessments = query_assess.all()
    journals = query_journal.all()

    session.close()

    return {"assessments": assessments, "journals": journals}


# -----------------------------
# JSON EXPORT
# -----------------------------
def export_as_json(data):
    serializable = {
        "assessments": [
            {"date": str(a.date), "score": a.score}
            for a in data["assessments"]
        ],
        "journals": [
            {"date": str(j.date), "text": j.text}
            for j in data["journals"]
        ],
    }
    return json.dumps(serializable, indent=2)


# -----------------------------
# CSV EXPORT
# -----------------------------
def export_as_csv(data):
    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["Type", "Date", "Value", "Notes"])

    for a in data["assessments"]:
        writer.writerow(["Assessment", str(a.date), a.score, ""])

    for j in data["journals"]:
        writer.writerow(["Journal", str(j.date), "", j.text])

    return output.getvalue()


# -----------------------------
# PDF EXPORT
# -----------------------------
def export_as_pdf(data, file_path):
    generate_pdf_report(data, file_path)


# -----------------------------
# MASTER CONTROLLER (MAIN ENTRY)
# -----------------------------
def export_user_data(user_id, format_type="csv", start_date=None, end_date=None):
    data = collect_user_data(user_id, start_date, end_date)

    if format_type == "csv":
        return export_as_csv(data)

    elif format_type == "json":
        return export_as_json(data)

    elif format_type == "pdf":
        os.makedirs("exports", exist_ok=True)
        file_path = f"exports/user_{user_id}_report.pdf"
        export_as_pdf(data, file_path)
        return file_path

    else:
        raise ValueError("Unsupported format")
