import json
import csv
import io
import zipfile
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.db import safe_db_context
from app.models import User, JournalEntry, Score, AssessmentResult, SatisfactionRecord, UserSession

logger = logging.getLogger(__name__)

class ExportService:
    @staticmethod
    def export_data(user_id: int, export_format: str, options: Dict[str, Any]) -> bytes:
        """
        Main entry point for data export.
        
        Args:
            user_id: The ID of the user request export.
            export_format: 'json', 'csv', or 'pdf'.
            options: Dictionary filtering options.
            
        Returns:
            bytes: The file content as a byte string.
        """
        data = ExportService._get_export_data(user_id, options)
        
        if export_format == 'json':
            return ExportService._format_json(data)
        elif export_format == 'csv':
            return ExportService._format_csv(data)
        elif export_format == 'pdf':
            return ExportService._format_pdf(data, user_id)
        else:
            raise ValueError(f"Unsupported format: {export_format}")

    @staticmethod
    def _get_export_data(user_id: int, options: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch COMPREHENSIVE data based on options."""
        data = {}
        start_date = options.get('start_date')
        end_date = options.get('end_date')

        with safe_db_context() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # --- 1. Profile Data (Comprehensive) ---
            if options.get('include_profile', True):
                pf = user.personal_profile
                mf = user.medical_profile
                sf = user.strengths
                ep = user.emotional_patterns
                
                # Helper to safely load JSON strings
                def safe_json(val):
                    try: return json.loads(val) if val else []
                    except: return val

                # Personal Profile
                personal_data = {}
                if pf:
                    personal_data = {
                        "occupation": pf.occupation,
                        "education": pf.education,
                        "marital_status": pf.marital_status,
                        "hobbies": pf.hobbies,
                        "bio": pf.bio,
                        "life_events": safe_json(pf.life_events),
                        "email": pf.email,
                        "phone": pf.phone,
                        "date_of_birth": pf.date_of_birth,
                        "gender": pf.gender,
                        "address": pf.address,
                        "society_contribution": pf.society_contribution,
                        "life_pov": pf.life_pov,
                        "high_pressure_events": pf.high_pressure_events
                    }

                # Medical Profile
                medical_data = {}
                if mf:
                    medical_data = {
                        "blood_type": mf.blood_type,
                        "allergies": mf.allergies,
                        "medications": mf.medications,
                        "medical_conditions": mf.medical_conditions,
                        "surgeries": mf.surgeries,
                        "therapy_history": mf.therapy_history,
                        "ongoing_health_issues": mf.ongoing_health_issues,
                        "emergency_contact_name": mf.emergency_contact_name,
                        "emergency_contact_phone": mf.emergency_contact_phone
                    }

                # Strengths
                strengths_data = {}
                if sf:
                    strengths_data = {
                        "top_strengths": safe_json(sf.top_strengths),
                        "areas_for_improvement": safe_json(sf.areas_for_improvement),
                        "current_challenges": safe_json(sf.current_challenges),
                        "learning_style": sf.learning_style,
                        "communication_preference": sf.communication_preference,
                        "comm_style": sf.comm_style,
                        "sharing_boundaries": safe_json(sf.sharing_boundaries),
                        "goals": sf.goals
                    }

                # Emotional Patterns
                emotional_data = {}
                if ep:
                    emotional_data = {
                        "common_emotions": safe_json(ep.common_emotions),
                        "emotional_triggers": ep.emotional_triggers,
                        "coping_strategies": ep.coping_strategies,
                        "preferred_support": ep.preferred_support
                    }

                data['profile'] = {
                    "username": user.username,
                    "created_at": user.created_at,
                    "last_login": user.last_login,
                    "personal": personal_data,
                    "medical": medical_data,
                    "strengths": strengths_data,
                    "emotional_patterns": emotional_data
                }

            # --- 2. Journal & Wellbeing (Comprehensive) ---
            if options.get('include_journal', True):
                query = session.query(JournalEntry).filter(
                    JournalEntry.user_id == user_id, 
                    JournalEntry.is_deleted == False
                )
                
                if start_date: query = query.filter(JournalEntry.entry_date >= start_date)
                if end_date: query = query.filter(JournalEntry.entry_date <= end_date)
                    
                entries = query.all()
                data['journal'] = [{
                    "id": e.id,
                    "date": e.entry_date,
                    "content": e.content,
                    "sentiment_score": e.sentiment_score,
                    "emotional_patterns": e.emotional_patterns,
                    "tags": e.tags,
                    # Wellbeing Metrics
                    "sleep_hours": e.sleep_hours,
                    "sleep_quality": e.sleep_quality,
                    "energy_level": e.energy_level,
                    "work_hours": e.work_hours,
                    "screen_time_minutes": e.screen_time_mins,
                    "stress_level": e.stress_level,
                    "stress_triggers": e.stress_triggers,
                    "daily_schedule": e.daily_schedule,
                    "privacy_level": e.privacy_level,
                    "word_count": e.word_count
                } for e in entries]

            # --- 3. Assessments & Scores (Comprehensive) ---
            if options.get('include_assessments', True):
                # EQ Scores
                scores_query = session.query(Score).filter(Score.user_id == user_id)
                if start_date: scores_query = scores_query.filter(Score.timestamp >= start_date)
                if end_date: scores_query = scores_query.filter(Score.timestamp <= end_date)
                
                data['eq_scores'] = [{
                    "timestamp": s.timestamp,
                    "total_score": s.total_score,
                    "sentiment_score": s.sentiment_score,
                    "reflection": s.reflection_text,
                    "is_rushed": s.is_rushed,
                    "is_inconsistent": s.is_inconsistent,
                    "age_at_test": s.age
                } for s in scores_query.all()]
                
                # Assessment Results
                assess_query = session.query(AssessmentResult).filter(
                    AssessmentResult.user_id == user_id,
                    AssessmentResult.is_deleted == False
                )
                if start_date: assess_query = assess_query.filter(AssessmentResult.timestamp >= start_date)
                if end_date: assess_query = assess_query.filter(AssessmentResult.timestamp <= end_date)
                
                data['assessments'] = [{
                    "type": a.assessment_type,
                    "timestamp": a.timestamp,
                    "total_score": a.total_score,
                    "details": a.details
                } for a in assess_query.all()]
                
                # Satisfaction Records
                sat_query = session.query(SatisfactionRecord).filter(SatisfactionRecord.user_id == user_id)
                if start_date: sat_query = sat_query.filter(SatisfactionRecord.timestamp >= start_date)
                if end_date: sat_query = sat_query.filter(SatisfactionRecord.timestamp <= end_date)
                
                data['satisfaction'] = [{
                    "timestamp": s.timestamp,
                    "category": s.satisfaction_category,
                    "score": s.satisfaction_score,
                    "positives": s.positive_factors,
                    "negatives": s.negative_factors,
                    "suggestions": s.improvement_suggestions,
                    "context": s.context
                } for s in sat_query.all()]
                
                # Responses (Individual Answers to Questions) - Can be large
                from app.models import Response
                resp_query = session.query(Response).join(UserSession, Response.session_id == UserSession.session_id).filter(UserSession.user_id == user_id)
                if start_date: resp_query = resp_query.filter(Response.timestamp >= start_date)
                if end_date: resp_query = resp_query.filter(Response.timestamp <= end_date)
                
                data['question_responses'] = [{
                    "question_id": r.question_id,
                    "response_value": r.response_value,
                    "timestamp": r.timestamp,
                    "age_group": r.age_group
                } for r in resp_query.all()]
                
            # --- 4. Settings & Technical Data (Always include if Profile is checked) ---
            if options.get('include_profile', True):
                from app.models import UserSettings, UserSyncSetting
                
                # App Settings
                settings = session.query(UserSettings).filter(UserSettings.user_id == user_id).first()
                if settings:
                    data['app_settings'] = {
                        "theme": settings.theme,
                        "question_count": settings.question_count,
                        "sound_enabled": settings.sound_enabled,
                        "notifications_enabled": settings.notifications_enabled,
                        "language": settings.language,
                        "updated_at": settings.updated_at
                    }
                    
                # Sync Settings
                syncs = session.query(UserSyncSetting).filter(UserSyncSetting.user_id == user_id).all()
                data['sync_data'] = [{
                    "key": s.key,
                    "value": s.value,
                    "version": s.version,
                    "updated_at": s.updated_at
                } for s in syncs]

        return data

    @staticmethod
    def _sanitize_csv_field(value: Any) -> str:
        """Prevent Formula Injection and handle None."""
        if value is None:
            return ""
        s_value = str(value)
        if s_value.startswith(('=', '+', '-', '@')):
            return "'" + s_value
        return s_value

    @staticmethod
    def _format_json(data: Dict[str, Any]) -> bytes:
        return json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')

    @staticmethod
    def _format_csv(data: Dict[str, Any]) -> bytes:
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
            
            def write_csv(filename: str, rows: List[Dict[str, Any]]):
                if not rows: return
                buffer = io.StringIO()
                # Get all unique keys from all rows to ensure complete header
                fieldnames = set()
                for row in rows:
                    fieldnames.update(row.keys())
                
                writer = csv.DictWriter(buffer, fieldnames=sorted(list(fieldnames)))
                writer.writeheader()
                for row in rows:
                    safe = {k: ExportService._sanitize_csv_field(v) for k,v in row.items()}
                    writer.writerow(safe)
                zip_file.writestr(filename, buffer.getvalue().encode('utf-8-sig'))

            # 1. Profile CSVs
            if 'profile' in data:
                p = data['profile']
                # Create a flattening for main profile info
                flat_personal = {"username": p['username'], "created_at": p['created_at']}
                flat_personal.update(p['personal'])
                write_csv('personal_profile.csv', [flat_personal])
                
                if p.get('medical'):
                    write_csv('medical_profile.csv', [p['medical']])
                    
                if p.get('strengths'):
                    # Flatten strengths slightly? Or keep JSON fields as JSON strings
                    write_csv('strengths_profile.csv', [p['strengths']])
                    
                if p.get('emotional_patterns'):
                    write_csv('emotional_patterns.csv', [p['emotional_patterns']])
                    
                if data.get('app_settings'):
                    write_csv('app_settings.csv', [data['app_settings']])
                    
                if data.get('sync_data'):
                    write_csv('sync_data.csv', data['sync_data'])

            # 2. Journal
            if data.get('journal'):
                write_csv('journal_entries.csv', data['journal'])
                
            # 3. Scores & Responses
            if data.get('eq_scores'):
                write_csv('eq_scores.csv', data['eq_scores'])
                
            if data.get('assessments'):
                write_csv('assessments.csv', data['assessments'])
                
            if data.get('satisfaction'):
                write_csv('satisfaction_records.csv', data['satisfaction'])
                
            if data.get('question_responses'):
                 # Chunking theoretically needed if massive, but for desktop app OK
                write_csv('question_responses.csv', data['question_responses'])
                
        return zip_buffer.getvalue()

    @staticmethod
    def _format_pdf(data: Dict[str, Any], user_id: int) -> bytes:
        """PDF generation with professional visual template."""
        from reportlab.lib.units import inch
        from reportlab.platypus import PageBreak, KeepTogether
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            rightMargin=72, leftMargin=72,
            topMargin=72, bottomMargin=72
        )
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Custom Title Style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Section Header Style
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
        normal_style.fontSize = 10
        normal_style.spaceAfter = 6

        story = []
        
        # --- COVER PAGE ---
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph("Soul Sense", title_style))
        story.append(Paragraph("Personal Data Export", ParagraphStyle('SubTitle', parent=title_style, fontSize=18, textColor=colors.grey)))
        story.append(Spacer(1, 1*inch))
        
        # Meta Info Box
        meta_data = [
            ["Export Date:", datetime.now().strftime('%B %d, %Y')],
            ["User ID:", str(user_id)],
            ["Username:", data.get('profile', {}).get('username', 'N/A')],
            ["Confidentiality:", "Private & Confidential"]
        ]
        
        t_meta = Table(meta_data, colWidths=[1.5*inch, 3*inch])
        t_meta.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#475569')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(t_meta)
        story.append(PageBreak())
        
        # --- CONTENT ---
        
        # Profile Section
        if 'profile' in data:
            story.append(Paragraph("Personal Profile", h2_style))
            p = data['profile']
            
            # Define a reusable style for profile tables
            profile_style = TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8FAFC')),
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('PADDING', (0,0), (-1,-1), 8),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ])
            
            # Profile Details Grid
            details = [
                ["Occupation", p['personal'].get('occupation') or '--'],
                ["Bio", (p['personal'].get('bio') or '--')[:200] + "..."],
                ["Life Perspective", (p['personal'].get('life_pov') or '--')[:200] + "..."],
                ["Email", p['personal'].get('email') or '--'],
                ["Phone", p['personal'].get('phone') or '--']
            ]
            
            t_profile = Table(details, colWidths=[2*inch, 4*inch])
            t_profile.setStyle(profile_style)
            story.append(t_profile)
            story.append(Spacer(1, 20))
            
            # --- MEDICAL SECTION ---
            if p.get('medical'):
                story.append(Paragraph("Medical Profile", h2_style))
                m = p['medical']
                top_med = [
                    ["Blood Type", m.get('blood_type') or '--'],
                    ["Emergency Contact", f"{m.get('emergency_contact_name') or '--'} ({m.get('emergency_contact_phone') or '--'})"]
                ]
                t_top_med = Table(top_med, colWidths=[2*inch, 4*inch])
                t_top_med.setStyle(profile_style)
                story.append(t_top_med)
                story.append(Spacer(1, 10))
                
                # Detailed Medical Lists - Formatted as Table for Consistency
                med_details = []
                med_keys = [
                    ("Allergies", 'allergies'),
                    ("Conditions", 'medical_conditions'),
                    ("Medications", 'medications'),
                    ("Surgeries", 'surgeries'),
                    ("Therapy History", 'therapy_history'),
                    ("Ongoing Issues", 'ongoing_health_issues')
                ]
                
                for label, key in med_keys:
                    val = m.get(key)
                    if val:
                        med_details.append([label, str(val)[:300]]) # Limit length slightly
                
                if med_details:
                    t_med_details = Table(med_details, colWidths=[2*inch, 4*inch])
                    # Recycle style but maybe different text color for clarity? Keeping same for consistency
                    t_med_details.setStyle(TableStyle([
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8FAFC')), 
                        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                        ('PADDING', (0,0), (-1,-1), 8),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#475569')),
                    ]))
                    story.append(t_med_details)
                
                story.append(Spacer(1, 20))

            # --- STRENGTHS SECTION ---
            if p.get('strengths'):
                story.append(Paragraph("Strengths & Goals", h2_style))
                s = p['strengths']
                str_data = [
                    ["Top Strengths", str(s.get('top_strengths') or '--')],
                    ["Refinements", str(s.get('areas_for_improvement') or '--')],
                    ["Learning Style", s.get('learning_style') or '--'],
                    ["Goals", s.get('goals') or '--']
                ]
                t_str = Table(str_data, colWidths=[2*inch, 4*inch])
                t_str.setStyle(profile_style)
                story.append(t_str)
                story.append(Spacer(1, 20))

            # --- EMOTIONAL SECTION ---
            if p.get('emotional_patterns'):
                story.append(Paragraph("Emotional Wellbeing", h2_style))
                e = p['emotional_patterns']
                emo_data = [
                    ["Common Emotions", str(e.get('common_emotions') or '--')],
                    ["Triggers", e.get('emotional_triggers') or '--'],
                    ["Coping Strategies", e.get('coping_strategies') or '--'],
                    ["Preferred Support", e.get('preferred_support') or '--']
                ]
                t_emo = Table(emo_data, colWidths=[2*inch, 4*inch])
                t_emo.setStyle(profile_style)
                story.append(t_emo)
                story.append(Spacer(1, 20))

        # Journal Section
        if 'journal' in data and data['journal']:
            count = len(data['journal'])
            story.append(Paragraph(f"Journal Entries ({count})", h2_style))
            
            # Sort by date desc
            sorted_entries = sorted(data['journal'], key=lambda x: x['date'], reverse=True)
            
            # PDF LIMIT: Show full entries for top 50, mention others
            limit = 50 
            
            for e in sorted_entries[:limit]: 
                # Entry Header (Date + Sentiment)
                date_str = str(e['date'])[:10]
                sent_val = f"{e['sentiment_score']:.1f}" if e['sentiment_score'] is not None else "-"
                sleep = str(e['sleep_hours']) if e['sleep_hours'] else "-"
                stress = str(e['stress_level']) if e['stress_level'] else "-"
                
                # Header Line: Date | Sentiment | Sleep | Stress
                header_text = f"<b>{date_str}</b>  |  Mood: {sent_val}  |  Sleep: {sleep}h  |  Stress: {stress}/5"
                
                # Create a mini table for the header to look like a card title
                t_header = Table([[Paragraph(header_text, normal_style)]], colWidths=[6*inch])
                t_header.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ]))
                story.append(t_header)
                
                # Full Content Body
                content_text = (e['content'] or "").replace('\n', '<br/>')
                story.append(Paragraph(content_text, normal_style))
                story.append(Spacer(1, 12))
            
            if count > limit:
                story.append(Paragraph(f"<i>...and {count - limit} more entries included in the CSV export.</i>", normal_style))
            
            story.append(Spacer(1, 20))
            
        # Assessments Section
        if 'eq_scores' in data and data['eq_scores']:
            story.append(Paragraph("EQ Assessment History", h2_style))
            
            # Enhanced Table with Sentiment
            header = [['Date', 'Total Score', 'Sentiment', 'Age At Test']]
            rows = []
            for s in data['eq_scores']:
                 rows.append([
                     s['timestamp'][:10],
                     str(s['total_score']),
                     f"{s['sentiment_score']:.1f}" if s.get('sentiment_score') is not None else "-",
                     str(s['age_at_test'])
                 ])
                 
            t_scores = Table(header + rows, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            t_scores.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#10B981')), # Green header
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F0FDF4')]),
                ('ALIGN', (1,0), (-1,-1), 'CENTER'), # Center numbers
            ]))
            story.append(t_scores)

        # Custom Canvas for Header/Footer
        def on_page(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 9)
            canvas.setFillColor(colors.grey)
            
            # Footer - Page Number
            page_num = canvas.getPageNumber()
            canvas.drawCentredString(letter[0]/2, 0.5*inch, f"Page {page_num}")
            
            # Footer - Confidential
            canvas.drawRightString(letter[0]-0.8*inch, 0.5*inch, "Confidential Data Export")
            
            # Header line
            canvas.setStrokeColor(colors.HexColor('#E2E8F0'))
            canvas.line(0.8*inch, letter[1]-0.8*inch, letter[0]-0.8*inch, letter[1]-0.8*inch)
            
            canvas.restoreState()

        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        return buffer.getvalue()
