from app.db import get_session
from app.models import Score, JournalEntry
from app.report_engine import generate_export_pdf
import csv
import os
import json
from io import StringIO


# -----------------------------
# DATA COLLECTION
# -----------------------------
def collect_user_data(user_id, start_date=None, end_date=None):
    session = get_session()

    # Score = Assessment
    query_scores = session.query(Score).filter_by(user_id=user_id)
    query_journals = session.query(JournalEntry).filter_by(user_id=user_id)

    if start_date:
        query_scores = query_scores.filter(Score.timestamp >= start_date)
        query_journals = query_journals.filter(JournalEntry.entry_date >= start_date)

    if end_date:
        query_scores = query_scores.filter(Score.timestamp <= end_date)
        query_journals = query_journals.filter(JournalEntry.entry_date <= end_date)

    scores = query_scores.all()
    journals = query_journals.all()

    session.close()

    return {"scores": scores, "journals": journals}


# -----------------------------
# JSON EXPORT
# -----------------------------
def export_as_json(data):
    serializable = {
        "assessments": [
            {
                "timestamp": s.timestamp,
                "total_score": s.total_score,
                "sentiment_score": s.sentiment_score,
            }
            for s in data["scores"]
        ],
        "journals": [
            {
                "date": j.entry_date,
                "text": j.content,
                "sentiment": j.sentiment_score,
            }
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

    for s in data["scores"]:
        writer.writerow(["Assessment", s.timestamp, s.total_score, s.sentiment_score])

    for j in data["journals"]:
        writer.writerow(["Journal", j.entry_date, "", j.content])

    return output.getvalue()


# -----------------------------
# PDF EXPORT
# -----------------------------
def export_as_pdf(data, file_path):
    generate_export_pdf(data, file_path)


# -----------------------------
# MAIN CONTROLLER
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
