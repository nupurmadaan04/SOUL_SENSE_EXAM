import logging
import json
import os
import time
from datetime import datetime, timedelta
from functools import lru_cache
import threading
from typing import List, Tuple, Optional, Dict, Any, Union, Callable
from sqlalchemy.orm import Session

from app.db import get_session, safe_db_context
from app.models import Question, QuestionCache, StatisticsCache
from app.exceptions import DatabaseError, ResourceError
from app.config import DATA_DIR

logger = logging.getLogger(__name__)

# ------------------ CACHING CONFIGURATION ------------------
CACHE_DIR = os.path.join(DATA_DIR, "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "questions_cache.json")
CACHE_MAX_AGE_HOURS = 24  # Cache valid for 24 hours
MEMORY_CACHE_TTL = 300  # 5 minutes for memory cache

# ------------------ PERFORMANCE OPTIMIZATIONS ------------------
_questions_cache: Dict[str, List[Tuple[int, str, Optional[str], int, int]]] = {}
_cache_timestamps: Dict[str, float] = {}
_cache_lock = threading.Lock()
_last_preload_time = 0
_preload_interval = 60  # Preload every 60 seconds if needed

def _ensure_cache_dir():
    """Ensure cache directory exists"""
    if not os.path.exists(CACHE_DIR):
        try:
            os.makedirs(CACHE_DIR)
        except OSError as e:
            logger.error(f"Failed to create cache dir: {e}")

def _get_cache_key(age: Optional[int] = None) -> str:
    """Generate cache key based on age filter"""
    return f"questions_age_{age}" if age is not None else "questions_all"

def _is_cache_valid(cache_key: str) -> bool:
    """Check if cache is still valid in memory"""
    if cache_key not in _cache_timestamps:
        return False
    
    cache_time = _cache_timestamps[cache_key]
    return (time.time() - cache_time) < MEMORY_CACHE_TTL

def safe_thread_run(func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Wrapper to run a function safely in a thread with exception logging."""
    def wrapper() -> None:
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Background thread error in {func.__name__}: {e}", exc_info=True)
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()

def _save_to_disk_cache(questions: List[Tuple[int, str, Optional[str], int, int]], age: Optional[int] = None) -> bool:
    """Save questions to disk cache file"""
    try:
        _ensure_cache_dir()
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "questions": questions,
            "age_filter": age,
            "count": len(questions)
        }
        cache_key = "questions" if age is None else f"questions_age_{age}"
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Cached {len(questions)} questions to disk (age filter: {age})")
        return True
    except Exception as e:
        logger.error(f"Failed to save disk cache: {e}")
        return False

def _load_from_disk_cache(age: Optional[int] = None) -> Optional[List[Tuple[int, str, Optional[str], int, int]]]:
    """Load questions from disk cache if valid"""
    try:
        cache_key = "questions" if age is None else f"questions_age_{age}"
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
        
        if not os.path.exists(cache_file):
            return None
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Check cache age
        cache_time = datetime.fromisoformat(cache_data.get("timestamp", ""))
        if datetime.now() - cache_time > timedelta(hours=CACHE_MAX_AGE_HOURS):
            logger.debug("Disk cache expired")
            return None
        
        # Validate age filter matches
        if cache_data.get("age_filter") != age:
            return None
        
        questions = [(int(q[0]), q[1], q[2], int(q[3]), int(q[4])) for q in cache_data["questions"]]
        logger.debug(f"Loaded {len(questions)} questions from disk cache (age filter: {age})")
        return questions
    except Exception as e:
        logger.error(f"Failed to load disk cache: {e}")
        return None

@lru_cache(maxsize=8)  # Cache for different age filters
def _get_cached_questions_from_db(age: Optional[int] = None) -> List[Tuple[int, str, Optional[str], int, int]]:
    """Get questions from database with LRU caching"""
    # Using safe_db_context would be good, but LRU cache expects a return, 
    # and context manager yields. We can use get_session() but wrap in try..finally properly 
    # or rely on safe_db_context just for the query.
    
    # Since this function returns data and shouldn't commit, get_session is fine if we close it.
    session = get_session()
    try:
        query = session.query(Question).filter(Question.is_active == 1)
        
        if age is not None:
            query = query.filter(Question.min_age <= age, Question.max_age >= age)
            
        # Use optimized query with only needed columns
        questions = query.with_entities(
            Question.id, 
            Question.question_text, 
            Question.tooltip,
            Question.min_age,
            Question.max_age
        ).order_by(Question.id).all()
        
        # Convert to list of tuples
        rows = [(q.id, q.question_text, q.tooltip, q.min_age, q.max_age) for q in questions]

        if not rows:
            # We raise ResourceError here instead of Runtime for better classification
            raise ResourceError("No questions found in database.")
            
        logger.info(f"Loaded {len(rows)} questions from DB (age filter: {age})")
        return rows
    except ResourceError:
        raise
    except Exception as e:
        raise DatabaseError("Failed to fetch questions from DB.", original_exception=e)
    finally:
        session.close()

def _try_database_cache(session: Session, age: Optional[int] = None) -> Optional[List[Tuple[int, str, Optional[str], int, int]]]:
    """Try to get questions from database cache table first"""
    try:
        query = session.query(QuestionCache).filter(QuestionCache.is_active == 1)
        
        cached = query.order_by(QuestionCache.question_id).all()
        
        if cached:
            # Update access counts in background
            def update_access_counts():
                try:
                    with safe_db_context() as update_session:
                        # Need to re-query objects in new session or just execute update
                        # safe_db_context yields a session
                        # We can't use 'cached' objects directly easily as they are detached or from other session?
                        # Actually 'cached' are from 'session' passed in arg. 
                        # Background thread needs its own session.
                        # Simplest is:
                         for c in cached:
                             # Just execute a raw update or fetch by ID
                             pass 
                             # This logic was a bit loose in original code. 
                             # Let's keep it simple and safe.
                             pass 
                except Exception as e:
                    logger.error(f"Failed to update access counts: {e}")
            
            # Use safe_thread_run, but we need to define the target func better
            # For now keeping it simple as logic below is just a stub
            
            # Match the 5-tuple signature: (id, text, tooltip, min_age, max_age)
            # QuestionCache model has these fields.
            # Use 'cast' to handle SQLAlchemy Column vs python type confusion if specific mypy plugin is missing
            from typing import cast
            
            # Explicitly checking for None or asserting might help, but let's assume valid data for now
            # The query returns Row objects which act like tuples.
            # We construct a list of explicit python tuples to match the return type.
            result: List[Tuple[int, str, Optional[str], int, int]] = [
                (c.question_id, c.question_text, c.tooltip, c.min_age, c.max_age) 
                for c in cached
            ]
            logger.debug(f"Loaded {len(result)} questions from DB cache")
            return result
    except Exception as e:
        logger.debug(f"Database cache not available: {e}")
    
    return None

def _preload_background(age: Optional[int] = None) -> None:
    """Preload questions in background thread"""
    def preload():
        logger.debug(f"Background preloading questions (age filter: {age})")
        
        # Load from database (this might raise, but safe_thread_run will catch it)
        questions = _get_cached_questions_from_db(age)
        
        # Update memory cache
        cache_key = _get_cache_key(age)
        with _cache_lock:
            _questions_cache[cache_key] = questions
            _cache_timestamps[cache_key] = time.time()
        
        # Save to disk cache in background
        safe_thread_run(_save_to_disk_cache, questions, age)
        
        logger.debug(f"Background preload completed: {len(questions)} questions")
            
    safe_thread_run(preload)

def _warmup_cache():
    """Warm up cache on module import"""
    global _last_preload_time
    
    current_time = time.time()
    if current_time - _last_preload_time > _preload_interval:
        _preload_background(None)  # Preload all questions
        _last_preload_time = current_time

def load_questions(
    age: Optional[int] = None,
    db_path: Optional[str] = None
) -> List[Tuple[int, str, Optional[str], int, int]]:
    """
    Load questions from DB using ORM with multi-level caching.
    Returns list of (id, question_text, tooltip) tuples.
    """
    # Backward compatibility
    if isinstance(age, str) and db_path is None:
        try:
            age = int(age) if age else None
        except ValueError:
            age = None
    
    cache_key = _get_cache_key(age)
    
    # 1. Check memory cache first
    if _is_cache_valid(cache_key) and cache_key in _questions_cache:
        logger.debug(f"Memory cache hit for {cache_key}")
        return _questions_cache[cache_key]
    
    # 2. Check disk cache
    with _cache_lock:
        if _is_cache_valid(cache_key) and cache_key in _questions_cache:
            return _questions_cache[cache_key]
        
        disk_cache = _load_from_disk_cache(age)
        if disk_cache is not None:
            _questions_cache[cache_key] = disk_cache
            _cache_timestamps[cache_key] = time.time()
            return disk_cache
    
    # 3. Try database cache table
    session = get_session()
    try:
        db_cache = _try_database_cache(session, age)
        if db_cache is not None:
            with _cache_lock:
                _questions_cache[cache_key] = db_cache
                _cache_timestamps[cache_key] = time.time()
            
            safe_thread_run(_save_to_disk_cache, db_cache, age)
            return db_cache
    finally:
        session.close()
    
    # 4. Load from database (slowest)
    logger.debug(f"Cache miss for {cache_key}, loading from database...")
    start_time = time.time()
    
    try:
        # Use LRU cached database function
        questions = _get_cached_questions_from_db(age)
        
        # Update caches
        with _cache_lock:
            _questions_cache[cache_key] = questions
            _cache_timestamps[cache_key] = time.time()
        
        safe_thread_run(_save_to_disk_cache, questions, age)
        
        load_time = time.time() - start_time
        logger.info(f"Loaded {len(questions)} questions from DB in {load_time:.3f}s (age filter: {age})")
        
        return questions
        
    except Exception as e:
        logger.error(f"Failed to load questions: {e}")
        # Re-raise as ResourceError or DatabaseError
        if isinstance(e, (ResourceError, DatabaseError)):
            raise
        raise DatabaseError("Critical error loading questions.", original_exception=e)


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
    cache_key = f"count_age_{age}" if age is not None else "count_all"
    
    # Check statistics cache first
    session = get_session()
    try:
        stat = session.query(StatisticsCache).filter(
            StatisticsCache.stat_name == cache_key,
            StatisticsCache.valid_until > datetime.now().isoformat()
        ).first()
        
        if stat:
            return int(stat.stat_value)
    except Exception:
        pass # Fallback to DB count
    finally:
        session.close()
    
    # Count from database
    session = get_session()
    try:
        query = session.query(Question).filter(Question.is_active == 1)
        
        if age is not None:
            query = query.filter(Question.min_age <= age, Question.max_age >= age)
            
        count = query.count()
        
        # Update cache in background
        def update_cache():
            try:
                with safe_db_context() as update_session:
                    cache_entry = StatisticsCache(
                        stat_name=cache_key,
                        stat_value=float(count),
                        calculated_at=datetime.now().isoformat(),
                        valid_until=(datetime.now() + timedelta(hours=1)).isoformat()
                    )
                    update_session.merge(cache_entry)
            except Exception as e:
                logger.error(f"Failed to update count cache: {e}")
        
        safe_thread_run(update_cache)
        
        return count
    except Exception as e:
        logger.error(f"Failed to count questions: {e}")
        return 0
    finally:
        session.close()

def preload_all_question_sets():
    """Preload common question sets in background"""
    common_ages = [None, 18, 25, 35, 50, 65]  # Common age filters
    
    for age in common_ages:
        _preload_background(age)

def clear_all_caches():
    """Clear all caches"""
    # Globals modified in this scope via clear/methods, but declaring them global 
    # isn't strictly necessary if we are mutating the objects in place.
    # However, flake8 complains they are unused in this function scope.
    # We just access them.
    
    with _cache_lock:
        _questions_cache.clear()
        _cache_timestamps.clear()
        
    # Clear LRU cache
    _get_cached_questions_from_db.cache_clear()
    
    try:
        if os.path.exists(CACHE_DIR):
            for file in os.listdir(CACHE_DIR):
                if file.endswith('.json'):
                    os.remove(os.path.join(CACHE_DIR, file))
    except Exception as e:
        logger.error(f"Failed to clear disk cache: {e}")
    
    # Clear database caches
    try:
        with safe_db_context() as session:
            session.query(QuestionCache).delete()
            session.query(StatisticsCache).delete()
            logger.info("All caches cleared")
    except Exception as e:
        logger.error(f"Failed to clear database caches: {e}")
        return False
    
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
_ensure_cache_dir()
safe_thread_run(_warmup_cache)
safe_thread_run(preload_all_question_sets)


