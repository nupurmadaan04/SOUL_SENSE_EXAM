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
        Fetches a comprehensive breakdown of an assessment.
        Security: Strictly filters by user_id to prevent unauthorized access.
        """
        # 1. Fetch the main score record
        stmt = select(Score).join(UserSession, Score.session_id == UserSession.session_id).filter(Score.id == assessment_id, UserSession.user_id == user_id)
        result = await db.execute(stmt)
        score = result.scalar_one_or_none()
        
        if not score:
            logger.warning(f"Assessment not found", extra={
                "assessment_id": assessment_id,
                "user_id": user_id,
                "reason": "not_found"
            })
            return None

        # 2. Get all responses for this session/user
        resp_stmt = (
            select(Response, Question, QuestionCategory)
            .join(Question, Response.question_id == Question.id)
            .join(QuestionCategory, Question.category_id == QuestionCategory.id)
            .filter(Response.session_id == score.session_id, Response.user_id == user_id)
            .all()
            .filter(Response.session_id == score.session_id)
        )
        resp_res = await db.execute(resp_stmt)
        responses = resp_res.all()

        if not responses:
            logger.info(f"No detailed responses found for assessment session {score.session_id}")
            return DetailedExamResult(
                assessment_id=score.id,
                total_score=float(score.total_score),
                max_possible_score=0.0,
                overall_percentage=0.0,
                timestamp=score.timestamp,
                category_breakdown=[],
                recommendations=[]
            )

        # 3. Process categories and aggregate scores
        category_stats = {}
        for resp, quest, cat in responses:
            cat_name = cat.name or "Uncategorized"
            if cat_name not in category_stats:
                category_stats[cat_name] = {
                    "score": 0.0,
                    "max": 0.0
                }
            
            weight = quest.weight if quest.weight is not None else 1.0
            category_stats[cat_name]["score"] += float(resp.response_value) * weight
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
                    message=f"Focus on strengthening your {name.lower()} skills through focused practice.",
                    priority="high"
                ))
            elif percentage < 85:
                recommendations.append(Recommendation(
                    category_name=name,
                    message=f"You're making good progress in {name.lower()}. Keep it up!",
                    priority="medium"
                ))
            else:
                recommendations.append(Recommendation(
                    category_name=name,
                    message=f"Excellent performance in {name.lower()}!",
                    priority="low"
                ))

        total_max = sum(d["max"] for d in category_stats.values())
        overall_pct = (score.total_score / total_max * 100.0) if total_max > 0 else 0.0

        result_obj = DetailedExamResult(
            assessment_id=score.id,
            total_score=float(score.total_score),
            max_possible_score=total_max,
            overall_percentage=round(cast(Any, overall_pct), 2),
            timestamp=score.timestamp,
            category_breakdown=breakdown,
            recommendations=recommendations
        )
        
        logger.info("Detailed results generated", extra={
            "assessment_id": assessment_id,
            "user_id": user_id,
            "categories_count": len(breakdown),
            "overall_percentage": overall_pct
        })
        
        return result_obj
