from reportlab.pdfgen import canvas
import os
import datetime


def generate_export_pdf(data, file_path):
    c = canvas.Canvas(file_path)
    y = 800

    c.setFont("Helvetica-Bold", 16)
    c.drawString(180, y, "SoulSense – User Export Report")
    y -= 40

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Generated at: {datetime.datetime.now()}")
    y -= 30

    # Scores
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Assessments")
    y -= 20
    c.setFont("Helvetica", 11)

    for s in data["scores"]:
        c.drawString(60, y, f"{s.timestamp} | Score: {s.total_score} | Sentiment: {s.sentiment_score}")
        y -= 18
        if y < 60:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = 800

    y -= 20

    # Journals
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Journal Entries")
    y -= 20
    c.setFont("Helvetica", 11)

    for j in data["journals"]:
        c.drawString(60, y, f"{j.entry_date} | {j.content[:70]}")
        y -= 18
        if y < 60:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = 800

    c.save()
