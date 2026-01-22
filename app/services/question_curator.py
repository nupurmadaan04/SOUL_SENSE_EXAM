from typing import List, Dict, Any


class QuestionCurator:
    """Curates question banks for Deep Dive assessments with version metadata."""

    DEFAULT_VERSION = "v1"

    _BASE_BANKS: Dict[str, List[str]] = {
        "career_clarity": [
            "I have a clear 5-year career plan.",
            "I feel my current role utilizes my best skills.",
            "I know exactly what skills I need to learn for my next promotion.",
            "I have a mentor who guides my professional growth.",
            "I am confident in my industry knowledge.",
            "I regularly network with people in my field.",
            "I can clearly articulate my professional value proposition.",
            "I feel secure in my current employment.",
            "I am excited about the future of my career path.",
            "My personal values align with my career choice.",
            "I have unexplored career interests I want to pursue.",
            "I feel stuck in my current role.",
            "I regularly receive constructive feedback.",
            "I have updated my resume/portfolio in the last 6 months.",
            "I know my market value (salary expectation).",
            "I have a clear definition of 'success' for myself.",
            "I prioritize work-life balance in my career planning.",
            "I am open to changing industries if needed.",
            "I have a 'Plan B' if my current job disappears.",
            "I feel my career is progressing at the right pace."
        ],
        "work_satisfaction": [
            "I look forward to starting my work day.",
            "I feel appreciated by my manager/supervisor.",
            "I have good relationships with my colleagues.",
            "My workload is manageable.",
            "I have the tools and resources to do my job well.",
            "I feel my compensation is fair.",
            "The company culture aligns with my personality.",
            "I have autonomy in how I do my work.",
            "I feel my opinions are valued at work.",
            "I rarely think about quitting.",
            "I leave work feeling energized, not drained.",
            "I have a clear understanding of my responsibilities.",
            "I receive recognition for my achievements.",
            "My physical/remote work environment is comfortable.",
            "I have opportunities for professional development.",
            "Communication within my team is effective.",
            "I feel a sense of purpose in my work.",
            "I can disconnect from work when off the clock.",
            "I trust the leadership of my organization.",
            "I would recommend my workplace to a friend."
        ],
        "strengths_deep_dive": [
            "I am aware of my top 3 personal strengths.",
            "I use my strengths every day.",
            "When faced with a challenge, I rely on my natural talents.",
            "I actively seek opportunities to use my strengths.",
            "I can easily describe what I'm best at to others.",
            "I focus more on building strengths than fixing weaknesses.",
            "My strengths have helped me overcome past failures.",
            "Others often compliment me on the same specific traits.",
            "I feel 'in flow' when using my core strengths.",
            "I seek feedback to refine my talents.",
            "I admire the strengths of others without envy.",
            "I know which tasks drain me versus energize me.",
            "I have a plan to further develop my talents.",
            "I help others discover their strengths.",
            "I feel authentic when I am performing well.",
            "I can distinguish between a learned skill and a natural talent.",
            "I consider my strengths when making big decisions.",
            "I have taken a formal strengths assessment before.",
            "I believe my strengths are valuable to my community.",
            "I am confident in what I bring to the table."
        ]
    }

    QUESTION_BANKS: Dict[str, Dict[str, List[str]]] = {
        key: {
            "v1": values,
            "v2": list(reversed(values))
        }
        for key, values in _BASE_BANKS.items()
    }

    VERSION_METADATA: Dict[str, Dict[str, Dict[str, str]]] = {
        "career_clarity": {
            "v1": {
                "description": "Foundational exploration of planning, confidence, and clarity.",
                "released_on": "2024-02-12"
            },
            "v2": {
                "description": "Updated narrative focusing on values, pivots, and backup planning.",
                "released_on": "2025-01-08"
            }
        },
        "work_satisfaction": {
            "v1": {
                "description": "Baseline satisfaction check covering appreciation, workload, and trust.",
                "released_on": "2024-05-23"
            },
            "v2": {
                "description": "Reordered questions to highlight burnout signals and recovery practices.",
                "released_on": "2025-03-14"
            }
        },
        "strengths_deep_dive": {
            "v1": {
                "description": "Strengths awareness with focus on practice and feedback.",
                "released_on": "2024-08-19"
            },
            "v2": {
                "description": "Flips the story to emphasize leadership, impact, and legacy.",
                "released_on": "2025-04-02"
            }
        }
    }

    @staticmethod
    def get_questions(assessment_type: str, count: int = 10, version: str = DEFAULT_VERSION) -> List[str]:
        versions = QuestionCurator.QUESTION_BANKS.get(assessment_type, {})
        version_key = version.lower()
        bank = versions.get(version_key) or versions.get(QuestionCurator.DEFAULT_VERSION, [])
        if not bank:
            return []
        actual_count = min(count, len(bank))
        return bank[:actual_count]

    @staticmethod
    def available_versions(assessment_type: str) -> List[str]:
        versions = QuestionCurator.QUESTION_BANKS.get(assessment_type)
        if not versions:
            return []
        return sorted(versions.keys())

    @staticmethod
    def version_metadata(assessment_type: str, version: str) -> Dict[str, str]:
        type_metadata = QuestionCurator.VERSION_METADATA.get(assessment_type, {})
        version_key = version.lower()
        return type_metadata.get(version_key) or type_metadata.get(QuestionCurator.DEFAULT_VERSION, {})

    @staticmethod
    def recommend_tests(user_profile: Any, score_data: Dict[str, Any]) -> List[str]:
        recommendations = []
        age = getattr(user_profile, 'age', 0) or 0
        stress = score_data.get('stress', 0)
        energy = score_data.get('energy', 0)
        total_eq = score_data.get('total_score', 0)

        if 20 <= age <= 35:
            recommendations.append("career_clarity")
        elif total_eq > 80 and age > 40:
            recommendations.append("career_clarity")

        if stress > 6 or energy < 4:
            recommendations.append("work_satisfaction")

        if total_eq < 50:
            recommendations.append("strengths_deep_dive")
        elif not recommendations:
            recommendations.append("strengths_deep_dive")

        return list(set(recommendations))
