from fpdf import FPDF
import datetime
import os
from reportlab.pdfgen import canvas
def generate_pdf_report(username, stats):
    """
    Generates a professional PDF assessment report.
    """
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(200, 10, "SoulSense AI Progress Report", ln=True, align='C')
    pdf.ln(10)
    
    # User Info
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"User: {username}", ln=True)
    pdf.cell(200, 10, f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(5)
    
    # Analysis Results
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, "Emotional Analysis Results", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Sentiment Score: {stats['avg_sentiment']}", ln=True)
    pdf.cell(200, 10, f"Current Status: {stats['status']}", ln=True)
    pdf.cell(200, 10, f"Entries Analyzed: {stats['count']}", ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.multi_cell(0, 10, "Disclaimer: This report is AI-generated and intended for self-awareness purposes only.")

    # Save logic
    file_name = f"{username}_report.pdf"
    pdf.output(file_name)
    return os.path.abspath(file_name)

    #this is for genrate_pdf_report
    


def generate_pdf_report(data, file_path):
    c = canvas.Canvas(file_path)

    y = 800
    c.setFont("Helvetica", 12)

    c.drawString(200, y, "User Emotional Health Report")
    y -= 40

    # Assessments
    c.drawString(50, y, "Assessments:")
    y -= 20

    for a in data["assessments"]:
        line = f"{a.date}  |  Score: {a.score}"
        c.drawString(60, y, line)
        y -= 20

    y -= 20

    # Journals
    c.drawString(50, y, "Journal Entries:")
    y -= 20

    for j in data["journals"]:
        text_line = f"{j.date}  |  {j.text[:60]}"
        c.drawString(60, y, text_line)
        y -= 20

        if y < 50:  # new page if space finished
            c.showPage()
            c.setFont("Helvetica", 12)
            y = 800

    c.save()
