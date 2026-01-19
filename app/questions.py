import logging
import json
import os
import time
from datetime import datetime, timedelta
from functools import lru_cache
import threading
from typing import List, Tuple, Optional, Dict, Any, Union, Callable
from sqlalchemy.orm import Session

from app.db import safe_db_context
from app.models import Question, QuestionCache, StatisticsCache
from app.exceptions import DatabaseError, ResourceError
from app.config import DATA_DIR

logger = logging.getLogger(__name__)

# ------------------ CACHING CONFIGURATION ------------------
# ------------------ PERFORMANCE OPTIMIZATIONS ------------------
# Simple in-memory storage for active questions
# Tuple structure: (id, question_text, tooltip, min_age, max_age)
_ALL_QUESTIONS: List[Tuple[int, str, Optional[str], int, int]] = []
_INIT_LOCK = threading.Lock()


def initialize_questions() -> bool:
    """
    Load all active questions from DB into memory.
    Safe to call multiple times (reloads data).
    """
    global _ALL_QUESTIONS
    
    with _INIT_LOCK:
        try:
            # Use specific context for initialization
            with safe_db_context() as session:
                # Optimized query fetching only needed columns
                qs = session.query(
                    Question.id, 
                    Question.question_text, 
                    Question.tooltip, 
                    Question.min_age, 
                    Question.max_age
                ).filter(
                    Question.is_active == 1
                ).order_by(Question.id).all()
                
                # Convert to list of tuples immediately
                # Explicit conversion to satisfy MyPy and ensure pure tuples
                _ALL_QUESTIONS = [(q.id, q.question_text, q.tooltip, q.min_age, q.max_age) for q in qs]
                
                logger.info(f"Loaded {len(_ALL_QUESTIONS)} active questions into memory.")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize questions: {e}")
            return False

def safe_thread_run(func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Wrapper to run a function safely in a thread with exception logging."""
    def wrapper() -> None:
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Background thread error in {func.__name__}: {e}", exc_info=True)
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()

def load_questions(
    age: Optional[int] = None,
    db_path: Optional[str] = None
) -> List[Tuple[int, str, Optional[str], int, int]]:
    """
    Load questions from in-memory cache.
    Filters by age if provided.
    """
    # Backward compatibility for age as string
    if isinstance(age, str) and db_path is None:
        try:
            age = int(age) if age else None
        except ValueError:
            age = None
            
    # Lazy Init Fallback (if list is empty due to startup race or first run)
    if not _ALL_QUESTIONS:
        logger.info("Questions not initialized, loading now...")
        initialize_questions()
    
    # Return filter result
    if age is None:
        # Return a copy to prevent modification of global list
        return list(_ALL_QUESTIONS)
        
    # In-memory filter is extremely fast
    return [q for q in _ALL_QUESTIONS if q[3] <= age <= q[4]]


SATISFACTION_QUESTIONS = {
    # Core satisfaction question
    "satisfaction_level": {
        "en": "Overall, how satisfied are you with your current work or studies?",
        "es": "En general, ¿qué tan satisfecho está con su trabajo o estudios actuales?",
        "hi": "कुल मिलाकर, आप अपने वर्तमान कार्य या अध्ययन से कितने संतुष्ट हैं?"
    },
    
    # Context questions
    "satisfaction_context": {
        "en": "What best describes your current situation?",
        "es": "¿Qué describe mejor su situación actual?",
        "hi": "आपकी वर्तमान स्थिति का सबसे अच्छा वर्णन क्या करता है?"
    },
    
    # Factor analysis
    "positive_factors": {
        "en": "What are the main positive aspects of your work/studies? (Select all that apply)",
        "es": "¿Cuáles son los principales aspectos positivos de su trabajo/estudios? (Seleccione todos los que correspondan)",
        "hi": "आपके कार्य/अध्ययन के मुख्य सकारात्मक पहलू क्या हैं? (लागू होने वाले सभी का चयन करें)"
    },
    
    "negative_factors": {
        "en": "What are the main challenges or negative aspects? (Select all that apply)",
        "es": "¿Cuáles son los principales desafíos o aspectos negativos? (Seleccione todos los que correspondan)",
        "hi": "मुख्य चुनौतियाँ या नकारात्मक पहलू क्या हैं? (लागू होने वाले सभी का चयन करें)"
    },
    
    # Improvement suggestions
    "improvement_suggestions": {
        "en": "What would most improve your satisfaction?",
        "es": "¿Qué mejoraría más su satisfacción?",
        "hi": "आपकी संतुष्टि में सबसे अधिक क्या सुधार करेगा?"
    }
}

SATISFACTION_OPTIONS = {
    "scale_10": {
        "en": [str(i) for i in range(1, 11)],  # 1-10
        "es": [str(i) for i in range(1, 11)],
        "hi": [str(i) for i in range(1, 11)]
    },
    
    "context_options": {
        "en": [
            "Full-time employment",
            "Part-time employment", 
            "Student (undergraduate)",
            "Student (graduate/postgrad)",
            "Self-employed/Freelancer",
            "Remote worker",
            "Hybrid work arrangement",
            "Looking for work",
            "On a break/sabbatical",
            "Other"
        ],
        "es": [
            "Empleo a tiempo completo",
            "Empleo a tiempo parcial",
            "Estudiante (pregrado)",
            "Estudiante (posgrado)",
            "Autónomo/Freelancer",
            "Trabajador remoto",
            "Arreglo de trabajo híbrido",
            "Buscando trabajo",
            "En pausa/sabático",
            "Otro"
        ],
        "hi": [
            "पूर्णकालिक रोजगार",
            "अंशकालिक रोजगार",
            "छात्र (स्नातक)",
            "छात्र (स्नातकोत्तर)",
            "स्वरोजगार/फ्रीलांसर",
            "दूरस्थ कार्यकर्ता",
            "संकर कार्य व्यवस्था",
            "काम की तलाश में",
            "विराम/सैबेटिकल पर",
            "अन्य"
        ]
    },
    
    "positive_factor_options": {
        "en": [
            "Good work-life balance",
            "Supportive colleagues/peers",
            "Interesting/meaningful work",
            "Opportunities for growth",
            "Fair compensation",
            "Autonomy/freedom",
            "Positive work environment",
            "Good management/supervision",
            "Learning opportunities",
            "Job security"
        ],
        "es": [
            "Buena balance trabajo-vida",
            "Colegas/compañeros de apoyo",
            "Trabajo interesante/significativo",
            "Oportunidades de crecimiento",
            "Compensación justa",
            "Autonomía/libertad",
            "Ambiente laboral positivo",
            "Buena gestión/supervisión",
            "Oportunidades de aprendizaje",
            "Seguridad laboral"
        ],
        "hi": [
            "अच्छा कार्य-जीवन संतुलन",
            "सहायक सहयोगी/साथी",
            "रोचक/सार्थक कार्य",
            "विकास के अवसर",
            "उचित पारिश्रमिक",
            "स्वायत्तता/स्वतंत्रता",
            "सकारात्मक कार्य वातावरण",
            "अच्छा प्रबंधन/पर्यवेक्षण",
            "सीखने के अवसर",
            "नौकरी की सुरक्षा"
        ]
    },
    
    "negative_factor_options": {
        "en": [
            "Excessive workload",
            "Poor work-life balance",
            "Unsupportive colleagues",
            "Lack of growth opportunities",
            "Unfair compensation",
            "Micromanagement",
            "Toxic work environment",
            "Unclear expectations",
            "Job insecurity",
            "Lack of recognition",
            "Boring/repetitive tasks",
            "Workplace politics"
        ],
        "es": [
            "Carga de trabajo excesiva",
            "Mal balance trabajo-vida",
            "Colegas no solidarios",
            "Falta de oportunidades de crecimiento",
            "Compensación injusta",
            "Micromanagement",
            "Ambiente laboral tóxico",
            "Expectativas poco claras",
            "Inseguridad laboral",
            "Falta de reconocimiento",
            "Tareas aburridas/repetitivas",
            "Políticas laborales"
        ],
        "hi": [
            "अत्यधिक कार्यभार",
            "खराब कार्य-जीवन संतुलन",
            "असहायक सहयोगी",
            "विकास के अवसरों की कमी",
            "अनुचित पारिश्रमिक",
            "सूक्ष्म प्रबंधन",
            "विषाक्त कार्य वातावरण",
            "अस्पष्ट अपेक्षाएँ",
            "नौकरी की असुरक्षा",
            "मान्यता की कमी",
            "उबाऊ/दोहराव वाले कार्य",
            "कार्यस्थल की राजनीति"
        ]
    },
    
    "improvement_options": {
        "en": [
            "Better work-life balance",
            "Higher compensation",
            "More growth opportunities",
            "Improved relationships with colleagues",
            "More autonomy/control",
            "Clearer career path",
            "Better management support",
            "Reduced workload",
            "More interesting work",
            "Improved work environment",
            "Better recognition",
            "Other"
        ],
        "es": [
            "Mejor balance trabajo-vida",
            "Mayor compensación",
            "Más oportunidades de crecimiento",
            "Mejores relaciones con colegas",
            "Más autonomía/control",
            "Trayectoria profesional más clara",
            "Mejor apoyo de gestión",
            "Reducción de carga de trabajo",
            "Trabajo más interesante",
            "Mejor ambiente laboral",
            "Mejor reconocimiento",
            "Otro"
        ],
        "hi": [
            "बेहतर कार्य-जीवन संतुलन",
            "उच्च पारिश्रमिक",
            "अधिक विकास के अवसर",
            "सहयोगियों के साथ बेहतर संबंध",
            "अधिक स्वायत्तता/नियंत्रण",
            "स्पष्ट करियर पथ",
            "बेहतर प्रबंधन सहायता",
            "कार्यभार में कमी",
            "अधिक रोचक कार्य",
            "बेहतर कार्य वातावरण",
            "बेहतर मान्यता",
            "अन्य"
        ]
    }
}

# ------------------ ADDITIONAL OPTIMIZATION FUNCTIONS ------------------

def get_question_count(age: Optional[int] = None) -> int:
    """Get count of active questions (optimized)"""
    # Lazy Init Fallback
    if not _ALL_QUESTIONS:
        initialize_questions()
        
    if age is None:
        return len(_ALL_QUESTIONS)
        
    return len([q for q in _ALL_QUESTIONS if q[3] <= age <= q[4]])

def preload_all_question_sets():
    """Deprecated: In-memory loading handles this automatically"""
    pass

def clear_all_caches():
    """Clear in-memory cache and reload from DB"""
    global _ALL_QUESTIONS
    with _INIT_LOCK:
        _ALL_QUESTIONS = []
    # Trigger reload
    initialize_questions()
    return True

import random

def get_random_questions_by_age(all_questions, user_age, num_questions):
    """
    Filters questions by min_age and max_age, returns randomized,
    non-repeating set of questions for one attempt.
    """
    filtered_questions = [
        q for q in all_questions if q[3] <= user_age <= q[4]
    ]

    if len(filtered_questions) < num_questions:
        raise ValueError("Not enough questions for this age")

    selected_questions = random.sample(filtered_questions, num_questions)
    return selected_questions

# ------------------ INITIALIZATION ------------------
# Explicitly initialize on module import to ensure readiness
# Note: In a larger app, we might want to defer this to app.main
# But keeping it here ensures functionality if imported standalone
# Using a thread to avoid blocking if import happens in main thread
safe_thread_run(initialize_questions)


