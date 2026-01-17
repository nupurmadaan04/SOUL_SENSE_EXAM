import logging
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend
import matplotlib.pyplot as plt
import io
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PDFReportGenerator:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.styles = getSampleStyleSheet()
        self.elements: List[Any] = []
        
        # Custom styles
        self.styles.add(ParagraphStyle(
            name='CenterTitle',
            parent=self.styles['Heading1'],
            alignment=1, # Center
            spaceAfter=20
        ))
        self.styles.add(ParagraphStyle(
            name='JustifiedBody',
            parent=self.styles['Normal'],
            alignment=4, # Justify
            spaceAfter=12
        ))

    def generate(self, username: str, score_data: Dict[str, Any], insights: List[str], sentiment_score: float) -> bool:
        """
        Generate the PDF report.
        
        Args:
            username (str): The user's name
            score_data (dict): Dictionary containing score details (total, breakdown)
            insights (list): List of AI insight strings
            sentiment_score (float): The sentiment analysis score
        """
        try:
            # Title
            self.elements.append(Paragraph("Soul Sense - Emotional Intelligence Report", self.styles['CenterTitle']))
            self.elements.append(Spacer(1, 0.2 * inch))
            
            # User Info Table
            data = [
                ["Name:", username],
                ["Date:", datetime.now().strftime("%Y-%m-%d %H:%M")],
                ["Total Score:", f"{score_data.get('total_score', 0)} / {score_data.get('max_score', 100)}"]
            ]
            
            t = Table(data, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
                ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            self.elements.append(t)
            self.elements.append(Spacer(1, 0.3 * inch))
            
            # Score Visualization (Chart)
            chart_img = self._create_chart(score_data['total_score'], score_data['max_score'], sentiment_score)
            if chart_img:
                self.elements.append(Image(chart_img, width=6*inch, height=3*inch))
                self.elements.append(Spacer(1, 0.3 * inch))

            # Executive Summary (Interpretation)
            self.elements.append(Paragraph("Executive Summary", self.styles['Heading2']))
            summary = self._get_interpretation(score_data['total_score'], score_data['max_score'])
            self.elements.append(Paragraph(summary, self.styles['JustifiedBody']))
            
            # Sentiment Analysis Section
            self.elements.append(Paragraph("Emotional Sentiment Analysis", self.styles['Heading2']))
            sentiment_text = f"Your emotional sentiment score is {sentiment_score:.1f} (Scale: -100 to +100)."
            if sentiment_score > 20:
                sentiment_text += " This indicates a generally positive and optimistic outlook."
            elif sentiment_score < -20:
                sentiment_text += " This suggests you may be experiencing some negative emotions or stress."
            else:
                sentiment_text += " This indicates a balanced and neutral emotional state."
            self.elements.append(Paragraph(sentiment_text, self.styles['JustifiedBody']))

            # AI Insights
            if insights:
                self.elements.append(Paragraph("AI-Driven Insights & Recommendations", self.styles['Heading2']))
                for insight in insights:
                    # Clean up insight text if needed
                    text = insight.strip()
                    if not text.startswith("•"):
                        text = "• " + text
                    self.elements.append(Paragraph(text, self.styles['JustifiedBody']))

            # Disclaimer
            self.elements.append(Spacer(1, 0.5 * inch))
            self.elements.append(Paragraph("Disclaimer: This tool is for educational purposes only and not a substitute for professional psychological advice.", self.styles['Italic']))

            # Build PDF
            doc = SimpleDocTemplate(self.filename, pagesize=letter)
            doc.build(self.elements)
            logger.info(f"PDF Report generated successfully: {self.filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}", exc_info=True)
            return False

    def _create_chart(self, score: float, max_score: float, sentiment: float) -> Optional[io.BytesIO]:
        """Create a matplotlib chart and return it as a BytesIO object"""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
            
            # EQ Score Gauge-like Bar
            percentage = (score / max_score) * 100 if max_score > 0 else 0
            ax1.bar(['Your EQ'], [percentage], color='#4CAF50')
            ax1.set_ylim(0, 100)
            ax1.set_title(f"EQ Score: {percentage:.1f}%")
            ax1.set_ylabel("Score %")
            
            # Sentiment Bar
            color = 'green' if sentiment > 0 else 'red'
            ax2.bar(['Sentiment'], [sentiment], color=color)
            ax2.set_ylim(-100, 100)
            ax2.axhline(0, color='black', linewidth=0.8)
            ax2.set_title(f"Sentiment: {sentiment:.1f}")
            
            img_data = io.BytesIO()
            plt.savefig(img_data, format='png', bbox_inches='tight', dpi=100)
            img_data.seek(0)
            plt.close(fig)
            return img_data
        except Exception as e:
            logger.error(f"Error creating chart for PDF: {e}")
            return None

    def _get_interpretation(self, score: float, max_score: float) -> str:
        """Generate a text interpretation of the score"""
        percentage = (score / max_score) * 100 if max_score > 0 else 0
        
        if percentage >= 80:
            return (f"Your score of {score}/{max_score} ({percentage:.1f}%) is Excellent. "
                    "You demonstrate high emotional intelligence, with strong self-awareness "
                    "and empathy skills. You are likely well-equipped to handle stress and "
                    "navigate complex social situations effectively.")
        elif percentage >= 65:
            return (f"Your score of {score}/{max_score} ({percentage:.1f}%) is Good. "
                    "You have a solid foundation of emotional intelligence. While you handle "
                    "most situations well, there may be specific areas where practicing "
                    "mindfulness or active listening could further enhance your skills.")
        elif percentage >= 50:
            return (f"Your score of {score}/{max_score} ({percentage:.1f}%) is Average. "
                    "You have a basic understanding of emotions but may struggle in high-pressure "
                    "situations. Focusing on self-regulation and empathy exercises can help "
                    "you improve.")
        else:
            return (f"Your score of {score}/{max_score} ({percentage:.1f}%) suggests room for improvement. "
                    "You might find it challenging to identify or manage emotions. "
                    "Consider dedication time to emotional awareness practices and seek "
                    "feedback from trusted friends or mentors.")


def generate_pdf_report(username: str, score: float, max_score: float, percentage: float, age: int, responses: List[int], questions: List[Any], sentiment_score: Optional[float] = None, filepath: Optional[str] = None) -> str:
    """
    Wrapper function to generate PDF report.
    This is the function imported by results.py.
    """
    try:
        if filepath:
            filename = filepath
            # Ensure directory exists if user picked a folder that doesn't exist (unlikely but safe)
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        else:
            # Create output directory if it doesn't exist
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, "reports")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate unique filename with absolute path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_dir, f"EQ_Report_{username}_{timestamp}.pdf")
        
        # Prepare score data
        score_data = {
            'total_score': score,
            'max_score': max_score,
            'percentage': percentage
        }
        
        # Generate insights based on responses
        insights = []
        if percentage >= 80:
            insights.append("Your emotional intelligence is excellent! Continue practicing mindfulness.")
            insights.append("You demonstrate strong self-awareness and empathy skills.")
        elif percentage >= 65:
            insights.append("Good emotional awareness with potential for growth.")
            insights.append("Consider practicing active listening to enhance empathy.")
        elif percentage >= 50:
            insights.append("Focus on recognizing emotional triggers in daily situations.")
            insights.append("Practice self-regulation through breathing exercises.")
        else:
            insights.append("Start with basic emotion identification exercises.")
            insights.append("Consider journaling to track emotional patterns.")
        
        # Create and generate report
        generator = PDFReportGenerator(filename)
        success = generator.generate(
            username,
            score_data,
            insights,
            sentiment_score or 0
        )
        
        if success:
            return filename
        else:
            raise Exception("PDF generation failed")
            
    except Exception as e:
        logger.error(f"Error in generate_pdf_report: {e}")
        raise
