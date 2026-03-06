"""
Enhanced Export Service with advanced data portability features.
Migrated to Async SQLAlchemy 2.0.
"""

import os
import json
import csv
import uuid
import logging
import zipfile
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from typing import List, Optional, Tuple, Dict, Any, Set
from pathlib import Path
from sqlalchemy import select, func, case, distinct, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update, delete
from cryptography.fernet import Fernet

from ..models import (
    User, Score, JournalEntry, UserSettings,
    PersonalProfile, MedicalProfile, UserStrengths,
    UserEmotionalPatterns, SatisfactionRecord,
    AssessmentResult, Response, ExportRecord, UserSession
)
from ..utils.file_validation import sanitize_filename, validate_file_path
from ..utils.atomic import atomic_write
from ..utils.distributed_lock import require_lock

logger = logging.getLogger(__name__)


class ExportServiceV2:
    """
    Enhanced export service with comprehensive data portability features.
    """

    EXPORT_DIR = Path("exports")
    SUPPORTED_FORMATS = {'json', 'csv', 'xml', 'html', 'pdf'}
    DATA_TYPES = {
        'profile', 'journal', 'assessments', 'scores',
        'satisfaction', 'settings', 'medical', 'strengths',
        'emotional_patterns', 'responses'
    }

    @classmethod
    def ensure_export_dir(cls):
        """Ensure export directory exists."""
        cls.EXPORT_DIR.mkdir(exist_ok=True)

    @staticmethod
    def _sanitize_csv_field(field: Any) -> str:
        """Sanitize CSV fields to prevent formula injection attacks."""
        if not isinstance(field, str):
            return str(field) if field is not None else ""

        if field and field.startswith(('=', '+', '-', '@')):
            return f"'{field}"
        return field

    @classmethod
    def _get_safe_filepath(cls, username: str, ext: str) -> str:
        """Generate a safe, collision-resistant filepath."""
        cls.ensure_export_dir()

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        short_id = uuid.uuid4().hex[:8]
        safe_username = sanitize_filename(username)

        filename = f"{safe_username}_{timestamp}_{short_id}.{ext}"
        full_path = str(cls.EXPORT_DIR / filename)

        return validate_file_path(
            full_path,
            allowed_extensions=[f".{ext}"],
            base_dir=str(cls.EXPORT_DIR.resolve())
        )

    @classmethod
    @require_lock(name="export_v2_{user.id}_{format}", timeout=60)
    async def generate_export(
        cls,
        db: AsyncSession,
        user: User,
        format: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Generate an export file with advanced options (Async).
        """
        """Generate an export file with advanced options."""
        options = options or {}

        if format.lower() not in cls.SUPPORTED_FORMATS:
            raise ValueError(
                f"Invalid format '{format}'. Supported: {', '.join(cls.SUPPORTED_FORMATS)}"
            )

        export_id = uuid.uuid4().hex
        timestamp = datetime.now(UTC)

        # Fetch data based on options
        data = await cls._fetch_export_data(db, user, options)

        metadata = cls._build_metadata(user, export_id, format, options, timestamp)
        data['_export_metadata'] = metadata

        ext = format.lower()
        filepath = cls._get_safe_filepath(user.username, ext)

        try:
            if ext == 'json':
                cls._write_json(filepath, data)
            elif ext == 'csv':
                cls._write_csv(filepath, data)
            elif ext == 'xml':
                cls._write_xml(filepath, data)
            elif ext == 'html':
                cls._write_html(filepath, data)
            elif ext == 'pdf':
                cls._write_pdf(filepath, data, user)

            if options.get('encrypt', False):
                password = options.get('password')
                if password:
                    filepath = cls._encrypt_export(filepath, password)

            # Record export in database
            await cls._record_export(db, user, export_id, format, filepath, options, timestamp)

            logger.info(f"Export generated for {user.username}: {filepath}")
            return filepath, export_id

        except Exception as e:
            logger.error(f"Failed to generate export for {user.username}: {e}")
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            raise e

    @classmethod
    async def _fetch_export_data(
        cls,
        db: AsyncSession,
        user: User,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fetch user data based on export options (Async).
        """
        """Fetch user data based on export options."""
        data = {}
        data_types = set(options.get('data_types', list(cls.DATA_TYPES)))
        date_range = options.get('date_range', {})

        start_date = None
        end_date = None
        if date_range.get('start'):
            start_date = datetime.fromisoformat(date_range['start'])
        if date_range.get('end'):
            end_date = datetime.fromisoformat(date_range['end'])

        # 1. Profile Data
        if 'profile' in data_types:
            data['profile'] = await cls._fetch_profile_data(db, user)

        if 'medical' in data_types:
            data['medical'] = await cls._fetch_medical_data(db, user)

        if 'strengths' in data_types:
            data['strengths'] = await cls._fetch_strengths_data(db, user)

        if 'emotional_patterns' in data_types:
            data['emotional_patterns'] = await cls._fetch_emotional_patterns_data(db, user)

        if 'settings' in data_types:
            data['settings'] = await cls._fetch_settings_data(db, user)

        if 'journal' in data_types:
            data['journal'] = await cls._fetch_journal_data(db, user, start_date, end_date)

        if 'scores' in data_types:
            data['scores'] = await cls._fetch_scores_data(db, user, start_date, end_date)

        if 'assessments' in data_types:
            data['assessments'] = await cls._fetch_assessments_data(db, user, start_date, end_date)

        if 'satisfaction' in data_types:
            data['satisfaction'] = await cls._fetch_satisfaction_data(db, user, start_date, end_date)

        if 'responses' in data_types:
            data['responses'] = await cls._fetch_responses_data(db, user, start_date, end_date)

        return data

    @classmethod
    async def _fetch_profile_data(cls, db: AsyncSession, user: User) -> Dict[str, Any]:
        """Fetch personal profile data (Async)."""
        """Fetch personal profile data."""
        stmt = select(PersonalProfile).filter(PersonalProfile.user_id == user.id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            return {}

        return {
            'username': user.username,
            'created_at': user.created_at.isoformat() if isinstance(user.created_at, datetime) else user.created_at,
            'last_login': user.last_login.isoformat() if isinstance(user.last_login, datetime) else user.last_login,
            'occupation': profile.occupation,
            'education': profile.education,
            'marital_status': profile.marital_status,
            'hobbies': profile.hobbies,
            'bio': profile.bio,
            'email': profile.email,
            'phone': profile.phone,
            'date_of_birth': profile.date_of_birth.isoformat() if isinstance(profile.date_of_birth, datetime) else profile.date_of_birth,
            'gender': profile.gender,
            'address': profile.address,
        }

    @classmethod
    async def _fetch_medical_data(cls, db: AsyncSession, user: User) -> Dict[str, Any]:
        """Fetch medical profile data (Async)."""
        """Fetch medical profile data."""
        stmt = select(MedicalProfile).filter(MedicalProfile.user_id == user.id)
        result = await db.execute(stmt)
        medical = result.scalar_one_or_none()

        if not medical:
            return {}

        return {
            'blood_type': medical.blood_type,
            'allergies': medical.allergies,
            'medications': medical.medications,
            'medical_conditions': medical.medical_conditions,
            'surgeries': medical.surgeries,
            'therapy_history': medical.therapy_history,
            'ongoing_health_issues': medical.ongoing_health_issues,
            'emergency_contact_name': medical.emergency_contact_name,
            'emergency_contact_phone': medical.emergency_contact_phone,
        }

    @classmethod
    async def _fetch_strengths_data(cls, db: AsyncSession, user: User) -> Dict[str, Any]:
        """Fetch strengths data (Async)."""
        """Fetch strengths data."""
        stmt = select(UserStrengths).filter(UserStrengths.user_id == user.id)
        result = await db.execute(stmt)
        strengths = result.scalar_one_or_none()

        if not strengths:
            return {}

        return {
            'top_strengths': strengths.top_strengths,
            'areas_for_improvement': strengths.areas_for_improvement,
            'current_challenges': strengths.current_challenges,
            'learning_style': strengths.learning_style,
            'communication_preference': strengths.communication_preference,
            'goals': strengths.goals,
        }

    @classmethod
    async def _fetch_emotional_patterns_data(cls, db: AsyncSession, user: User) -> Dict[str, Any]:
        """Fetch emotional patterns data (Async)."""
        """Fetch emotional patterns data."""
        stmt = select(UserEmotionalPatterns).filter(UserEmotionalPatterns.user_id == user.id)
        result = await db.execute(stmt)
        patterns = result.scalar_one_or_none()

        if not patterns:
            return {}

        return {
            'common_emotions': patterns.common_emotions,
            'emotional_triggers': patterns.emotional_triggers,
            'coping_strategies': patterns.coping_strategies,
            'preferred_support': patterns.preferred_support,
        }

    @classmethod
    async def _fetch_settings_data(cls, db: AsyncSession, user: User) -> Dict[str, Any]:
        """Fetch user settings (Async)."""
        """Fetch user settings."""
        stmt = select(UserSettings).filter(UserSettings.user_id == user.id)
        result = await db.execute(stmt)
        settings = result.scalar_one_or_none()

        if not settings:
            return {}

        return {
            'theme': settings.theme,
            'question_count': settings.question_count,
            'sound_enabled': settings.sound_enabled,
            'notifications_enabled': settings.notifications_enabled,
            'language': settings.language,
        }

    @classmethod
    async def _fetch_journal_data(
        cls,
        db: AsyncSession,
        user: User,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Fetch journal entries with date filtering (Async)."""
        """Fetch journal entries with date filtering."""
        stmt = select(JournalEntry).filter(
            JournalEntry.user_id == user.id,
            JournalEntry.is_deleted == False
        )

        if start_date:
            stmt = stmt.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            stmt = stmt.filter(JournalEntry.entry_date <= end_date)

        result = await db.execute(stmt.order_by(JournalEntry.entry_date.desc()))
        stmt = stmt.order_by(JournalEntry.entry_date.desc())
        result = await db.execute(stmt)
        entries = result.scalars().all()

        return [{
            'id': e.id,
            'date': e.entry_date.isoformat() if isinstance(e.entry_date, datetime) else e.entry_date,
            'content': e.content,
            'sentiment_score': e.sentiment_score,
            'emotional_patterns': e.emotional_patterns,
            'tags': e.tags,
            'sleep_hours': e.sleep_hours,
            'stress_level': e.stress_level,
            'energy_level': e.energy_level,
        } for e in entries]

    @classmethod
    async def _fetch_scores_data(
        cls,
        db: AsyncSession,
        user: User,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Fetch assessment scores (Async)."""
        stmt = select(Score).filter(Score.user_id == user.id)
        """Fetch assessment scores."""
        stmt = select(Score).join(UserSession, Score.session_id == UserSession.session_id).filter(UserSession.user_id == user.id)

        if start_date:
            stmt = stmt.filter(Score.timestamp >= start_date)
        if end_date:
            stmt = stmt.filter(Score.timestamp <= end_date)

        result = await db.execute(stmt.order_by(Score.timestamp.desc()))
        stmt = stmt.order_by(Score.timestamp.desc())
        result = await db.execute(stmt)
        scores = result.scalars().all()

        return [{
            'timestamp': s.timestamp.isoformat() if isinstance(s.timestamp, datetime) else s.timestamp,
            'total_score': s.total_score,
            'sentiment_score': s.sentiment_score,
            'reflection_text': s.reflection_text,
            'is_rushed': s.is_rushed,
            'is_inconsistent': s.is_inconsistent,
            'age_group': s.detailed_age_group,
        } for s in scores]

    @classmethod
    async def _fetch_assessments_data(
        cls,
        db: AsyncSession,
        user: User,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Fetch assessment results (Async)."""
        stmt = select(AssessmentResult).filter(AssessmentResult.user_id == user.id)
        """Fetch assessment results."""
        stmt = select(AssessmentResult).filter(
            AssessmentResult.user_id == user.id,
            AssessmentResult.is_deleted == False
        )

        if start_date:
            stmt = stmt.filter(AssessmentResult.timestamp >= start_date)
        if end_date:
            stmt = stmt.filter(AssessmentResult.timestamp <= end_date)

        result = await db.execute(stmt.order_by(AssessmentResult.timestamp.desc()))
        stmt = stmt.order_by(AssessmentResult.timestamp.desc())
        result = await db.execute(stmt)
        assessments = result.scalars().all()

        return [{
            'type': a.assessment_type,
            'timestamp': a.timestamp.isoformat() if isinstance(a.timestamp, datetime) else a.timestamp,
            'total_score': a.total_score,
            'details': a.details,
        } for a in assessments]

    @classmethod
    async def _fetch_satisfaction_data(
        cls,
        db: AsyncSession,
        user: User,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Fetch satisfaction records (Async)."""
        """Fetch satisfaction records."""
        stmt = select(SatisfactionRecord).filter(SatisfactionRecord.user_id == user.id)

        if start_date:
            stmt = stmt.filter(SatisfactionRecord.timestamp >= start_date)
        if end_date:
            stmt = stmt.filter(SatisfactionRecord.timestamp <= end_date)

        result = await db.execute(stmt.order_by(SatisfactionRecord.timestamp.desc()))
        stmt = stmt.order_by(SatisfactionRecord.timestamp.desc())
        result = await db.execute(stmt)
        records = result.scalars().all()

        return [{
            'timestamp': r.timestamp.isoformat() if isinstance(r.timestamp, datetime) else r.timestamp,
            'category': r.satisfaction_category,
            'score': r.satisfaction_score,
            'positives': r.positive_factors,
            'negatives': r.negative_factors,
            'suggestions': r.improvement_suggestions,
        } for r in records]

    @classmethod
    async def _fetch_responses_data(
        cls,
        db: AsyncSession,
        user: User,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Fetch question responses (Async)."""
        stmt = select(Response).filter(Response.user_id == user.id)
        """Fetch question responses."""
        stmt = select(Response).join(UserSession, Response.session_id == UserSession.session_id).filter(UserSession.user_id == user.id)

        if start_date:
            stmt = stmt.filter(Response.timestamp >= start_date)
        if end_date:
            stmt = stmt.filter(Response.timestamp <= end_date)

        result = await db.execute(stmt.order_by(Response.timestamp.desc()))
        stmt = stmt.order_by(Response.timestamp.desc())
        result = await db.execute(stmt)
        responses = result.scalars().all()

        return [{
            'question_id': r.question_id,
            'response_value': r.response_value,
            'timestamp': r.timestamp.isoformat() if isinstance(r.timestamp, datetime) else r.timestamp,
            'age_group': r.age_group,
        } for r in responses]

    @classmethod
    def _build_metadata(
        cls,
        user: User,
        export_id: str,
        format: str,
        options: Dict[str, Any],
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Build export metadata for GDPR compliance."""
        return {
            'version': '2.0',
            'exported_at': timestamp.isoformat(),
            'export_id': export_id,
            'format': format,
            'user_id': user.id,
            'username': user.username,
            'date_range': options.get('date_range', {}),
            'data_types': options.get('data_types', list(cls.DATA_TYPES)),
            'is_encrypted': options.get('encrypt', False),
            'schema': 'https://soulsense.example.org/schemas/export/v2',
            'data_controller': 'Soul Sense EQ Test',
            'purpose': 'Data portability and user right to access (GDPR Article 15)',
            'data_lineage': {
                'sources': ['PostgreSQL database', 'User inputs'],
                'processing_history': ['Collected via web interface', 'Stored in database']
            }
        }

    @classmethod
    def _write_json(cls, filepath: str, data: Dict[str, Any]):
        """Write data to JSON file."""
        with atomic_write(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    @classmethod
    def _write_csv(cls, filepath: str, data: Dict[str, Any]):
        """Write data to CSV files (zipped)."""
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

            def write_csv(filename: str, rows: List[Dict[str, Any]]):
                if not rows:
                    return
                buffer = io.StringIO()
                fieldnames = set()
                for row in rows:
                    fieldnames.update(row.keys())

                writer = csv.DictWriter(buffer, fieldnames=sorted(list(fieldnames)))
                writer.writeheader()
                for row in rows:
                    safe = {k: cls._sanitize_csv_field(v) for k, v in row.items()}
                    writer.writerow(safe)
                zip_file.writestr(filename, buffer.getvalue().encode('utf-8-sig'))

            if '_export_metadata' in data:
                meta_buffer = io.StringIO()
                json.dump(data['_export_metadata'], meta_buffer, indent=2, default=str)
                zip_file.writestr('metadata.json', meta_buffer.getvalue().encode('utf-8'))

            for key, value in data.items():
                if key == '_export_metadata':
                    continue
                if isinstance(value, list):
                    write_csv(f'{key}.csv', value)
                elif isinstance(value, dict):
                    write_csv(f'{key}.csv', [value])

        with open(filepath, 'wb') as f:
            f.write(zip_buffer.getvalue())

    @classmethod
    def _write_xml(cls, filepath: str, data: Dict[str, Any]):
        """Write data to XML file."""
        root = ET.Element('SoulSenseExport')

        if '_export_metadata' in data:
            meta_elem = ET.SubElement(root, 'ExportMetadata')
            for key, value in data['_export_metadata'].items():
                child = ET.SubElement(meta_elem, key)
                if isinstance(value, (dict, list)):
                    child.text = json.dumps(value)
                else:
                    child.text = str(value)

        for key, value in data.items():
            if key == '_export_metadata':
                continue

            section = ET.SubElement(root, key)

            if isinstance(value, list):
                for item in value:
                    item_elem = ET.SubElement(section, 'Item')
                    for item_key, item_value in item.items():
                        field = ET.SubElement(item_elem, item_key)
                        if isinstance(item_value, (dict, list)):
                            field.text = json.dumps(item_value)
                        else:
                            field.text = str(item_value)
            elif isinstance(value, dict):
                for item_key, item_value in value.items():
                    field = ET.SubElement(section, item_key)
                    if isinstance(item_value, (dict, list)):
                        field.text = json.dumps(item_value)
                    else:
                        field.text = str(item_value)

        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

        with atomic_write(filepath, "w", encoding="utf-8") as f:
            f.write(xml_str)

    @classmethod
    def _write_html(cls, filepath: str, data: Dict[str, Any]):
        """Write data to self-contained HTML file."""
        html_parts = []
        html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soul Sense Data Export</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .section {
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #667eea;
            color: white;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .metadata {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            font-size: 0.9em;
        }
        .search-box {
            padding: 10px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
            width: 100%;
            box-sizing: border-box;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Soul Sense Data Export</h1>
        <p>Comprehensive export of your emotional intelligence data</p>
    </div>
""")

        if '_export_metadata' in data:
            html_parts.append('<div class="section"><h2>Export Metadata</h2><div class="metadata">')
            for key, value in data['_export_metadata'].items():
                html_parts.append(f'<p><strong>{key}:</strong> {value}</p>')
            html_parts.append('</div></div>')

        for key, value in data.items():
            if key == '_export_metadata':
                continue

            html_parts.append(f'<div class="section"><h2>{key.replace("_", " ").title()}</h2>')

            if isinstance(value, list) and value:
                html_parts.append('<table><thead><tr>')
                for header in value[0].keys():
                    html_parts.append(f'<th>{header.replace("_", " ").title()}</th>')
                html_parts.append('</tr></thead><tbody>')

                for item in value[:100]:
                    html_parts.append('<tr>')
                    for val in item.values():
                        html_parts.append(f'<td>{val if val else "-"}</td>')
                    html_parts.append('</tr>')

                html_parts.append('</tbody></table>')
                if len(value) > 100:
                    html_parts.append(f'<p><em>...and {len(value) - 100} more entries</em></p>')

            elif isinstance(value, dict):
                html_parts.append('<table>')
                for k, v in value.items():
                    html_parts.append(f'<tr><td><strong>{k.replace("_", " ").title()}</strong></td><td>{v if v else "-"}</td></tr>')
                html_parts.append('</table>')

            html_parts.append('</div>')

        html_parts.append("</body></html>")

        with atomic_write(filepath, "w", encoding="utf-8") as f:
            f.write(''.join(html_parts))

    @classmethod
    def _write_pdf(cls, filepath: str, data: Dict[str, Any], user: User):
        """Write data to PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                PageBreak
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
        except ImportError:
            logger.error("reportlab not installed. Cannot generate PDF.")
            raise ValueError("PDF export requires reportlab library")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72, leftMargin=72,
            topMargin=72, bottomMargin=72
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        h2_style = ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#3B82F6'),
            spaceBefore=20,
            spaceAfter=10,
        )

        story = []
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph("Soul Sense", title_style))
        story.append(Paragraph("Advanced Data Export", ParagraphStyle(
            'SubTitle', parent=title_style, fontSize=18, textColor=colors.grey
        )))
        story.append(Spacer(1, 1*inch))

        if '_export_metadata' in data:
            meta = data['_export_metadata']
            meta_data = [
                ["Export Date:", meta.get('exported_at', 'N/A')],
                ["Export ID:", meta.get('export_id', 'N/A')],
                ["Format:", meta.get('format', 'N/A').upper()],
                ["Username:", user.username],
                ["Data Types:", ', '.join(meta.get('data_types', []))],
            ]

            t_meta = Table(meta_data, colWidths=[1.5*inch, 4*inch])
            t_meta.setStyle(TableStyle([
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#475569')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ]))
            story.append(t_meta)
            story.append(PageBreak())

        for key, value in data.items():
            if key == '_export_metadata':
                continue

            story.append(Paragraph(key.replace("_", " ").title(), h2_style))

            if isinstance(value, list) and value:
                display_items = value[:50]
                headers = list(display_items[0].keys())
                table_data = [headers]
                for item in display_items[:20]:
                    row = [str(item.get(h, ''))[:50] for h in headers]
                    table_data.append(row)

                t = Table(table_data, colWidths=[1.2*inch] * len(headers))
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#10B981')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F0FDF4')]),
                ]))
                story.append(t)
                story.append(Spacer(1, 20))

            elif isinstance(value, dict):
                table_data = [[k, str(v)[:100]] for k, v in value.items()]
                t = Table(table_data, colWidths=[2*inch, 3.5*inch])
                t.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                    ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8FAFC')),
                    ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ]))
                story.append(t)
                story.append(Spacer(1, 20))

        doc.build(story)

        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())

    @classmethod
    def _encrypt_export(cls, filepath: str, password: str) -> str:
        """Encrypt export file."""
        try:
            key = Fernet.generate_key()
            fernet = Fernet(key)

            with open(filepath, 'rb') as f:
                original_data = f.read()

            encrypted_data = fernet.encrypt(original_data)
            encrypted_path = filepath + '.encrypted'
            
            with atomic_write(encrypted_path, 'wb') as f:
                f.write(encrypted_data)

            key_path = filepath + '.key'
            with atomic_write(key_path, 'wb') as f:
                f.write(key)

            os.remove(filepath)
            return encrypted_path

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Failed to encrypt export: {e}")

    @classmethod
    async def _record_export(
        cls,
        db: AsyncSession,
        user: User,
        export_id: str,
        format: str,
        filepath: str,
        options: Dict[str, Any],
        timestamp: datetime
    ):
        """Record export in database for audit trail (Async)."""
        """Record export in database."""
        try:
            date_range = options.get('date_range', {})

            export_record = ExportRecord(
                user_id=user.id,
                export_id=export_id,
                format=format,
                file_path=filepath,
                date_range_start=datetime.fromisoformat(date_range['start']) if date_range.get('start') else None,
                date_range_end=datetime.fromisoformat(date_range['end']) if date_range.get('end') else None,
                data_types=json.dumps(options.get('data_types', list(cls.DATA_TYPES))),
                is_encrypted=options.get('encrypt', False),
                status='completed',
                created_at=timestamp,
                expires_at=timestamp + timedelta(hours=48)
            )

            db.add(export_record)
            await db.commit()

        except Exception as e:
            logger.error(f"Failed to record export: {e}")
            await db.rollback()

    @classmethod
    async def get_export_history(cls, db: AsyncSession, user: User, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get export history for a user (Async).
        """
        stmt = select(ExportRecord).filter(
            ExportRecord.user_id == user.id
        ).order_by(
            ExportRecord.created_at.desc()
        ).limit(limit)
        """Get export history for a user."""
        stmt = select(ExportRecord).filter(
            ExportRecord.user_id == user.id
        ).order_by(
            desc(ExportRecord.created_at)
        ).limit(limit)
        
        result = await db.execute(stmt)
        exports = result.scalars().all()

        return [{
            'export_id': e.export_id,
            'format': e.format,
            'created_at': e.created_at.isoformat() if isinstance(e.created_at, datetime) else e.created_at,
            'expires_at': e.expires_at.isoformat() if isinstance(e.expires_at, datetime) else e.expires_at,
            'is_encrypted': e.is_encrypted,
            'status': e.status,
            'file_path': e.file_path,
        } for e in exports]

    @classmethod
    async def delete_export(cls, db: AsyncSession, user: User, export_id: str) -> bool:
        """
        Delete an export file and its record (Async).
        """
        """Delete an export file and its record."""
        stmt = select(ExportRecord).filter(
            ExportRecord.export_id == export_id,
            ExportRecord.user_id == user.id
        )
        result = await db.execute(stmt)
        export = result.scalar_one_or_none()

        if not export:
            return False

        try:
            if os.path.exists(export.file_path):
                os.remove(export.file_path)

            if export.is_encrypted and os.path.exists(export.file_path + '.key'):
                os.remove(export.file_path + '.key')

        except Exception as e:
            logger.error(f"Failed to delete export file: {e}")

        # Delete database record
        await db.delete(export)
        await db.commit()

        return True

    @classmethod
    def validate_export_access(cls, user: User, filename: str) -> bool:
        """Verify that a user is authorized to access the given filename."""
        safe_username = sanitize_filename(user.username)
        if not filename.startswith(f"{safe_username}_"):
            logger.warning(f"Access denied: User {user.username} tried to access {filename}")
            return False
        return True

    @classmethod
    async def cleanup_old_exports(cls, db: AsyncSession, max_age_hours: int = 48):
        """Delete export files older than max_age_hours (Async)."""
        """Delete export files older than max_age_hours."""
        try:
            if not cls.EXPORT_DIR.exists():
                return

            cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)

            for p in cls.EXPORT_DIR.glob("*"):
                if p.is_file():
                    try:
                        mtime = datetime.fromtimestamp(p.stat().st_mtime, UTC)
                        if mtime < cutoff:
                            p.unlink()
                            logger.info(f"Deleted old export: {p.name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {p.name}: {e}")

            # Mark database records as expired
            from sqlalchemy import update
            stmt = update(ExportRecord).filter(
                ExportRecord.expires_at < cutoff,
                ExportRecord.status == 'completed'
            ).values(status='expired')
            
            await db.execute(stmt)
            await db.commit()

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            await db.rollback()
