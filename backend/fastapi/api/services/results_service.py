import logging
from typing import List, Optional, Any, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import Score, Response, Question, QuestionCategory, UserSession
from ..schemas import DetailedExamResult, CategoryScore, Recommendation

logger = logging.getLogger("api.exam")


class AssessmentResultsService:
    @staticmethod
    async def get_detailed_results(db: AsyncSession, assessment_id: int, user_id: int) -> Optional[DetailedExamResult]:
        """
        Fetches a comprehensive breakdown of assessment results (Async).
        """
        # 1. Fetch main score record
        stmt = select(Score).filter(Score.id == assessment_id)
        result = await db.execute(stmt)
        score = result.scalar_one_or_none()
        
        if not score:
            logger.warning(f"Assessment score not found for id: {assessment_id}")
            return None

        # Verify user ownership (check score.user_id or score.session_id)
        if getattr(score, "user_id", None) is not None:
            if score.user_id != user_id:
                logger.warning(f"User {user_id} attempted to access score {assessment_id} owned by {score.user_id}")
                return None
        elif getattr(score, "session_id", None):
            session_stmt = select(UserSession).filter(UserSession.session_id == score.session_id, UserSession.user_id == user_id)
            session_res = await db.execute(session_stmt)
            if not session_res.scalar_one_or_none():
                return None

        # 2. Get all responses joined with Question and Category
        resp_stmt = (
            select(Response, Question, QuestionCategory)
            .join(Question, Response.question_id == Question.id)
            .outerjoin(QuestionCategory, Question.category_id == QuestionCategory.id)
            .filter(Response.session_id == score.session_id)
        )
        resp_result = await db.execute(resp_stmt)
        responses = resp_result.all()

        if not responses:
            logger.info(f"No detailed responses found for assessment session {score.session_id}")
            return DetailedExamResult(
                assessment_id=score.id,
                total_score=float(score.total_score or 0),
                max_possible_score=100.0,
                overall_percentage=float(score.total_score or 0),
                timestamp=str(score.timestamp) if score.timestamp else "",
                category_breakdown=[],
                recommendations=[
                    Recommendation(category_name="General", message="Complete another assessment to receive full category insights.", priority="medium")
                ]
            )

        # 3. Process categories
        category_stats = {}
        for resp, quest, cat in responses:
            cat_name = (cat.name if cat else None) or getattr(quest, "category", None) or "Emotional Intelligence"
            if cat_name not in category_stats:
                category_stats[cat_name] = {"score": 0.0, "max": 0.0}
            
            weight = getattr(quest, "weight", 1.0)
            if weight is None:
                weight = 1.0
            resp_val = float(resp.response_value) if resp.response_value is not None else 3.0
            category_stats[cat_name]["score"] += resp_val * weight
            category_stats[cat_name]["max"] += 5.0 * weight

        breakdown = []
        recommendations = []
        for name, data in category_stats.items():
            percentage = (data["score"] / data["max"]) * 100.0 if data["max"] > 0 else 0.0
            breakdown.append(CategoryScore(
                category_name=name,
                score=round(data["score"], 1),
                max_score=round(data["max"], 1),
                percentage=round(percentage, 1)
            ))

            if percentage < 60:
                recommendations.append(Recommendation(
                    category_name=name,
                    message=f"Focus on practicing self-reflection and exercises for {name}.",
                    priority="high"
                ))
            elif percentage < 80:
                recommendations.append(Recommendation(
                    category_name=name,
                    message=f"Good baseline in {name}. Regular journaling can help deepen this skill.",
                    priority="medium"
                ))
            else:
                recommendations.append(Recommendation(
                    category_name=name,
                    message=f"Demonstrating strong mastery in {name}!",
                    priority="low"
                ))

        total_score_sum = sum(d["score"] for d in category_stats.values())
        total_max = sum(d["max"] for d in category_stats.values())
        overall_pct = (total_score_sum / total_max * 100.0) if total_max > 0 else (float(score.total_score or 0))

        return DetailedExamResult(
            assessment_id=score.id,
            total_score=float(score.total_score if score.total_score is not None else total_score_sum),
            max_possible_score=total_max,
            overall_percentage=round(overall_pct, 2),
            timestamp=str(score.timestamp) if score.timestamp else "",
            category_breakdown=breakdown,
            recommendations=recommendations
        )
