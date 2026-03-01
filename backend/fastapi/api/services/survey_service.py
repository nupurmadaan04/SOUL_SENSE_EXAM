from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple, Dict, Any
from uuid import uuid4
from datetime import datetime, UTC
import logging

from ..models import (
    SurveyTemplate, SurveySection, SurveyQuestion, 
    SurveySubmission, SurveyResponse, SurveyStatus, QuestionType, User
)

logger = logging.getLogger("api.surveys")

class SurveyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_template(self, user_id: int, data: Dict[str, Any]) -> SurveyTemplate:
        """Create a new survey template (Draft)."""
        template = SurveyTemplate(
            uuid=str(uuid4()),
            title=data['title'],
            description=data.get('description'),
            scoring_logic=data.get('scoring_logic'),
            created_by_id=user_id,
            status=SurveyStatus.DRAFT,
            version=1
        )
        self.db.add(template)
        await self.db.flush() 
        
        for s_data in data.get('sections', []):
            section = SurveySection(
                survey_id=template.id,
                title=s_data['title'],
                description=s_data.get('description'),
                order=s_data.get('order', 0)
            )
            self.db.add(section)
            await self.db.flush()
            
            for q_data in s_data.get('questions', []):
                question = SurveyQuestion(
                    section_id=section.id,
                    question_text=q_data['question_text'],
                    question_type=q_data['question_type'],
                    options=q_data.get('options'),
                    is_required=q_data.get('is_required', True),
                    order=q_data.get('order', 0),
                    logic_config=q_data.get('logic_config')
                )
                self.db.add(question)
        
        await self.db.commit()
        # Reload with all relationships
        stmt = select(SurveyTemplate).options(
            selectinload(SurveyTemplate.sections).selectinload(SurveySection.questions)
        ).where(SurveyTemplate.id == template.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_active_surveys(self) -> List[SurveyTemplate]:
        """List all currently active and published surveys."""
        stmt = select(SurveyTemplate).where(
            SurveyTemplate.is_active == True,
            SurveyTemplate.status == SurveyStatus.PUBLISHED
        ).order_by(SurveyTemplate.title)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_template_by_id(self, template_id: int, admin_access: bool = False) -> Optional[SurveyTemplate]:
        stmt = select(SurveyTemplate).options(
            selectinload(SurveyTemplate.sections).selectinload(SurveySection.questions)
        ).where(SurveyTemplate.id == template_id)
        
        if not admin_access:
            # Public access: only published and active surveys
            stmt = stmt.where(
                SurveyTemplate.is_active == True,
                SurveyTemplate.status == SurveyStatus.PUBLISHED
            )
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def publish_template(self, template_id: int) -> SurveyTemplate:
        """Mark a template as published. Encompasses versioning logic."""
        template = await self.get_template_by_id(template_id, admin_access=True)
        if not template:
            raise ValueError("Template not found")
        
        # Deactivate all other versions of this UUID
        stmt = update(SurveyTemplate).where(
            SurveyTemplate.uuid == template.uuid,
            SurveyTemplate.id != template.id
        ).values(is_active=False)
        await self.db.execute(stmt)
        
        template.status = SurveyStatus.PUBLISHED
        template.is_active = True
        
        await self.db.commit()
        return template

    async def create_new_version(self, template_id: int, user_id: int) -> SurveyTemplate:
        """Create a DRAFT clone of an existing template for modification."""
        old = await self.get_template_by_id(template_id, admin_access=True)
        if not old:
            raise ValueError("Original template not found")

        # Create clone
        new_template = SurveyTemplate(
            uuid=old.uuid,
            title=f"{old.title} (Clone)",
            description=old.description,
            version=old.version + 1,
            status=SurveyStatus.DRAFT,
            is_active=False,
            scoring_logic=old.scoring_logic,
            created_by_id=user_id
        )
        self.db.add(new_template)
        await self.db.flush()

        for old_sec in old.sections:
            new_sec = SurveySection(
                survey_id=new_template.id,
                title=old_sec.title,
                description=old_sec.description,
                order=old_sec.order
            )
            self.db.add(new_sec)
            await self.db.flush()
            
            for old_q in old_sec.questions:
                new_q = SurveyQuestion(
                    section_id=new_sec.id,
                    question_text=old_q.question_text,
                    question_type=old_q.question_type,
                    options=old_q.options,
                    is_required=old_q.is_required,
                    order=old_q.order,
                    logic_config=old_q.logic_config
                )
                self.db.add(new_q)

        await self.db.commit()
        return await self.get_template_by_id(new_template.id)

    async def submit_responses(self, user_id: int, survey_id: int, responses: List[Dict[str, Any]], metadata: Dict[str, Any] = None) -> SurveySubmission:
        """Process survey submission and apply scoring DSL."""
        survey = await self.get_template_by_id(survey_id)
        if not survey or survey.status != SurveyStatus.PUBLISHED:
            raise ValueError("Inactive or missing survey")

        # Validate all required questions are answered
        required_questions = set()
        all_questions = set()
        for section in survey.sections:
            for question in section.questions:
                all_questions.add(question.id)
                if question.is_required:
                    required_questions.add(question.id)

        submitted_question_ids = set()
        for r_data in responses:
            qid = r_data['question_id']
            val = r_data['answer_value']
            if qid not in all_questions:
                raise ValueError(f"Question {qid} does not belong to this survey")
            if not val or str(val).strip() == "":
                raise ValueError(f"Question {qid} cannot have an empty answer")
            submitted_question_ids.add(qid)

        missing_required = required_questions - submitted_question_ids
        if missing_required:
            raise ValueError(f"Missing responses for required questions: {list(missing_required)}")

        submission = SurveySubmission(
            user_id=user_id,
            survey_id=survey_id,
            metadata_json=metadata,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC)
        )
        self.db.add(submission)
        await self.db.flush()

        answer_map = {} 
        for r_data in responses:
            qid = r_data['question_id']
            val = r_data['answer_value']
            
            resp = SurveyResponse(
                submission_id=submission.id,
                question_id=qid,
                answer_value=str(val)
            )
            self.db.add(resp)
            answer_map[qid] = val
        
        # Apply Scoring DSL Engine
        total_scores = self._calculate_scores_dsl(survey.scoring_logic, answer_map)
        submission.total_scores = total_scores
        
        await self.db.commit()
        return submission

    def _calculate_scores_dsl(self, logic: List[Dict], answers: Dict[int, Any]) -> Dict[str, float]:
        """
        Custom JSON-based Scoring DSL.
        Supports rules like:
        [
            {
                "if": {"qid": 12, "op": "==", "val": "High Stress"},
                "then": {"anxiety": 5, "resilience": -2}
            }
        ]
        """
        scores = {}
        if not logic: return scores
        
        for rule in logic:
            condition = rule.get('if', {})
            qid = condition.get('qid')
            op = condition.get('op', '==')
            target_val = condition.get('val')
            
            actual_val = answers.get(qid)
            if actual_val is None: continue

            # Evaluation logic
            match = False
            if op == '==':
                match = str(actual_val) == str(target_val)
            elif op == '>':
                try: match = float(actual_val) > float(target_val)
                except: pass
            elif op == '<':
                try: match = float(actual_val) < float(target_val)
                except: pass

            if match:
                consequences = rule.get('then', {})
                for dimension, delta in consequences.items():
                    scores[dimension] = scores.get(dimension, 0.0) + float(delta)
        
        return scores
