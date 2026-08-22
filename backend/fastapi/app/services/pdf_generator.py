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
        self.elements: List[Any] = []
        
    def generate(self, username: str, score_data: Dict[str, Any], insights: List[str], responses: List[int], questions: List[Any], sentiment_score: float, deep_dives: List[Any] = None) -> bool:
        """
        Generate the PDF report with Soul Sense branding.
        """
        try:
            # Setup styles (matching ExportService)
            styles = getSampleStyleSheet()
            
            # Custom Styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                textColor=colors.HexColor('#0F172A'),
                spaceAfter=30,
                alignment=1 # Center
            )
            
            h2_style = ParagraphStyle(
                'CustomH2',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#3B82F6'),
                spaceBefore=20,
                spaceAfter=10,
                borderPadding=5,
                borderColor=colors.HexColor('#E2E8F0'),
                borderWidth=0,
                allowWidows=0
            )
            
            normal_style = styles['Normal']
            normal_style.fontSize = 11
            normal_style.spaceAfter = 8
            normal_style.alignment = 4 # Justify

            # --- CONTENT ---
            
            # Title Page area (Header handled by on_page)
            self.elements.append(Spacer(1, 1*inch))
            self.elements.append(Paragraph("Assessment Result", title_style))
            self.elements.append(Spacer(1, 0.5*inch))
            
            # User Info Grid
            info_data = [
                ["Participant", username],
                ["Date", datetime.now().strftime("%B %d, %Y")],
                ["Time", datetime.now().strftime("%I:%M %p")],
                ["Assessment Type", "Emotional Intelligence (EQ)"]
            ]
            
            t_info = Table(info_data, colWidths=[2*inch, 4*inch])
            t_info.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8FAFC')),
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#475569')),
                ('PADDING', (0,0), (-1,-1), 10),
            ]))
            self.elements.append(t_info)
            self.elements.append(Spacer(1, 0.5 * inch))
            
            # Score Visualization
            # Note: We kept the logic to create the chart
            chart_img = self._create_chart(score_data['total_score'], score_data['max_score'], sentiment_score)
            if chart_img:
                self.elements.append(Image(chart_img, width=6.5*inch, height=3.5*inch))
                self.elements.append(Spacer(1, 0.3 * inch))

            # Interpretation
            self.elements.append(Paragraph("Executive Summary", h2_style))
            summary = self._get_interpretation(score_data['total_score'], score_data['max_score'])
            
            # Wrap summary in a nice box
            t_summary = Table([[Paragraph(summary, normal_style)]], colWidths=[6*inch])
            t_summary.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F9FF')), # Light blue
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BAE6FD')),
                ('PADDING', (0,0), (-1,-1), 12),
            ]))
            self.elements.append(t_summary)
            
            # Sentiment Section
            self.elements.append(Paragraph("Emotional Sentiment Analysis", h2_style))
            sentiment_text = f"Your emotional sentiment score is <b>{sentiment_score:.1f}</b> (Scale: -100 to +100)."
            if sentiment_score > 20:
                sentiment_text += " This indicates a generally positive and optimistic outlook."
            elif sentiment_score < -20:
                sentiment_text += " This suggests you may be experiencing some negative emotions or stress."
            else:
                sentiment_text += " This indicates a balanced and neutral emotional state."
            
            self.elements.append(Paragraph(sentiment_text, normal_style))
            self.elements.append(Spacer(1, 0.2*inch))

            # --- DEEP DIVE INSIGHTS ---
            if deep_dives:
                self.elements.append(Paragraph("Deep Dive Insights", h2_style))
                self.elements.append(Paragraph("Detailed breakdown of specific emotional metrics based on your responses:", normal_style))
                self.elements.append(Spacer(1, 10))
                
                # Header
                dd_header = [['Category', 'Score', 'Rating']]
                dd_rows = []
                
                for dd in deep_dives:
                    cat_name = dd.assessment_type.replace('_', ' ').title()
                    score_display = f"{int(dd.total_score)}/100" 
                    
                    rating = "N/A"
                    text_color = colors.black
                    
                    # Simple heuristic 
                    if dd.total_score >= 70:
                        rating = "High"
                        text_color = colors.HexColor('#DC2626') if 'anxiety' in dd.assessment_type or 'depression' in dd.assessment_type else colors.HexColor('#16A34A')
                    elif dd.total_score >= 40:
                        rating = "Moderate"
                        text_color = colors.HexColor('#CA8A04')
                    else:
                        rating = "Low"
                        text_color = colors.HexColor('#16A34A') if 'anxiety' in dd.assessment_type or 'depression' in dd.assessment_type else colors.HexColor('#DC2626')
                        
                    dd_rows.append([cat_name, score_display, rating])

                t_deep = Table(dd_header + dd_rows, colWidths=[3*inch, 1.5*inch, 1.5*inch])
                t_deep.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                    ('PADDING', (0,0), (-1,-1), 8),
                    ('ALIGN', (1,0), (-1,-1), 'CENTER'),
                    ('ALIGN', (0,0), (0,-1), 'LEFT'),
                ]))
                self.elements.append(t_deep)
                self.elements.append(Spacer(1, 20))

            # AI Insights
            if insights:
                self.elements.append(Paragraph("Actionable Insights", h2_style))
                
                # Format insights as a styled list/table
                insight_data = []
                for insight in insights:
                     text = insight.strip()
                     if text.startswith("•"): text = text[1:].strip()
                     insight_data.append(["•", Paragraph(text, normal_style)])
                     
                t_insights = Table(insight_data, colWidths=[0.3*inch, 5.7*inch])
                t_insights.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#3B82F6')), # Blue bullets
                    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ]))
                self.elements.append(t_insights)

            # Disclaimer
            self.elements.append(Spacer(1, 0.5 * inch))
            disclaimer = Paragraph("Disclaimer: This tool is for educational purposes only and not a substitute for professional psychological advice.", 
                                 ParagraphStyle('Disc', parent=normal_style, fontSize=8, textColor=colors.grey, alignment=1))
            self.elements.append(disclaimer)

            # Build PDF with Header/Footer
            doc = SimpleDocTemplate(
                self.filename, 
                pagesize=letter,
                rightMargin=72, leftMargin=72,
                topMargin=72, bottomMargin=72
            )
            
            doc.build(self.elements, onFirstPage=self._on_page, onLaterPages=self._on_page)
            logger.info(f"PDF Report generated successfully: {self.filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}", exc_info=True)
            return False


    def _on_page(self, canvas, doc):
        """Draw Header and Footer"""
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.grey)
        
        # Footer - Page Number
        page_num = canvas.getPageNumber()
        canvas.drawCentredString(letter[0]/2, 0.5*inch, f"Page {page_num}")
        
        # Footer - Brand
        canvas.drawRightString(letter[0]-0.8*inch, 0.5*inch, "Soul Sense | Assessment Report")
        
        # Header line
        canvas.setStrokeColor(colors.HexColor('#E2E8F0'))
        canvas.line(0.8*inch, letter[1]-0.8*inch, letter[0]-0.8*inch, letter[1]-0.8*inch)
        
        # Optional: Add Logo Placeholder Text
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(colors.HexColor('#0F172A'))
        canvas.drawString(0.8*inch, letter[1]-0.6*inch, "Soul Sense")
        
        canvas.restoreState()


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


def generate_pdf_report(username: str, score: float, max_score: float, percentage: float, age: int, responses: List[int], questions: List[Any], sentiment_score: Optional[float] = None, filepath: Optional[str] = None, deep_dives: List[Any] = None) -> str:
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
            username=username,
            score_data=score_data,
            insights=insights,
            responses=responses,
            questions=questions,
            sentiment_score=sentiment_score or 0,
            deep_dives=deep_dives
        )
        
        if success:
            return filename
        else:
            raise Exception("PDF generation failed")
            
    except Exception as e:
        logger.error(f"Error in generate_pdf_report: {e}")
        raise
