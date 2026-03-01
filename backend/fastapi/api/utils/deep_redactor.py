import re
import logging
import inspect
import json
from typing import Any, Dict, List, Set, Type, Optional, Union
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase
from .redaction import mask_email, mask_phone, mask_ip

# Regex patterns for common PII in strings
PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    # Improved phone regex
    "phone": re.compile(r"(\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"),
    # Match keys like 'password', 'secret', 'token', 'key'
    "secret_key": re.compile(r"(?i)(password|secret|token|key|auth|api_key|client_secret)"),
}

# Regex for sensitive field names
SENSITIVE_NAME_RE = re.compile(r"(?i)(email|phone|password|secret|token|auth|otp|code|pin|ssn|card|bank|address|birth|dob|medication|allergy|medical|condition|emergency|contact|blood)")

class SchemaRegistry:
    """Caches object schema information to avoid expensive reflection on every log call."""
    _cache: Dict[Type, Set[str]] = {}

    @classmethod
    def get_sensitive_fields(cls, obj_type: Type) -> Set[str]:
        if obj_type in cls._cache:
            return cls._cache[obj_type]
        
        sensitive_fields = set()
        
        # 1. Check for @redactable fields (explicitly marked by developer)
        if hasattr(obj_type, "__redactable_fields__"):
            sensitive_fields.update(getattr(obj_type, "__redactable_fields__"))

        # 2. Pydantic Support
        if inspect.isclass(obj_type) and issubclass(obj_type, BaseModel):
            for field_name, field_info in obj_type.model_fields.items():
                if field_info.json_schema_extra and field_info.json_schema_extra.get("sensitive"):
                    sensitive_fields.add(field_name)
                elif SENSITIVE_NAME_RE.search(field_name):
                    sensitive_fields.add(field_name)
        
        # 3. SQLAlchemy Support
        elif hasattr(obj_type, "__table__"):
            try:
                for column in obj_type.__table__.columns:
                    if column.info and column.info.get("sensitive"):
                        sensitive_fields.add(column.name)
                    elif SENSITIVE_NAME_RE.search(column.name):
                        sensitive_fields.add(column.name)
            except Exception:
                pass

        # 4. Generic class attribute inspection fallback
        if not sensitive_fields and inspect.isclass(obj_type):
            for name, _ in inspect.getmembers(obj_type, lambda x: not inspect.isroutine(x)):
                if not name.startswith("_") and SENSITIVE_NAME_RE.search(name):
                    sensitive_fields.add(name)

        cls._cache[obj_type] = sensitive_fields
        return sensitive_fields

class DeepRedactor:
    """Recursively redacts PII from various object types."""

    @classmethod
    def redact(cls, obj: Any, depth: int = 0) -> Any:
        # Prevent infinite recursion for deep or circular structures
        if depth > 10:
            return "***MAX_DEPTH_REACHED***"

        if obj is None:
            return None

        # Handle strings: apply regex-based masking
        if isinstance(obj, str):
            return cls._redact_string(obj)

        # Handle bytes
        if isinstance(obj, bytes):
            try:
                decoded = obj.decode("utf-8")
                return cls._redact_string(decoded).encode("utf-8")
            except Exception:
                return obj

        # Handle dictionaries
        if isinstance(obj, dict):
            return {k: cls._redact_value_by_key(k, v, depth + 1) for k, v in obj.items()}

        # Handle lists and tuples
        if isinstance(obj, (list, tuple)):
            redacted_items = [cls.redact(item, depth + 1) for item in obj]
            return tuple(redacted_items) if isinstance(obj, tuple) else redacted_items

        # Handle Pydantic models
        if isinstance(obj, BaseModel):
            return cls._redact_pydantic(obj, depth)

        # Handle SQLAlchemy models
        if hasattr(obj, "__table__") and hasattr(obj, "__dict__"):
            return cls._redact_sqlalchemy(obj, depth)

        # Handle other objects with __dict__ (generic reflection)
        if hasattr(obj, "__dict__"):
            return cls._redact_generic(obj, depth)

        # For unknown objects, we cannot easily redact internal PII unless we convert to string
        # but that would trigger expensive string formatting here.
        return obj

    @classmethod
    def _redact_string(cls, text: str) -> str:
        """Redacts PII patterns from a plain string."""
        # Redact emails
        text = PII_PATTERNS["email"].sub(lambda m: mask_email(m.group(0)), text)
        # Redact phones
        text = PII_PATTERNS["phone"].sub(lambda m: mask_phone(m.group(0)), text)
        return text

    @classmethod
    def _redact_value_by_key(cls, key: str, value: Any, depth: int) -> Any:
        """Special handling for values associated with sensitive-looking keys."""
        if SENSITIVE_NAME_RE.search(key):
            if isinstance(value, str):
                lower_key = key.lower()
                if "email" in lower_key: return mask_email(value)
                if "phone" in lower_key: return mask_phone(value)
                if "ip" in lower_key: return mask_ip(value)
                return "***REDACTED***"
            elif isinstance(value, (int, float, bool)) or value is None:
                return "***REDACTED***"
        
        return cls.redact(value, depth)

    @classmethod
    def _redact_pydantic(cls, obj: BaseModel, depth: int) -> Dict[str, Any]:
        sensitive_fields = SchemaRegistry.get_sensitive_fields(type(obj))
        redacted = {}
        # Iterate over __dict__ instead of model_dump to keep nested models intact
        for k in obj.__dict__.keys():
            if k.startswith("_"): continue
            v = getattr(obj, k)
            if k in sensitive_fields:
                redacted[k] = cls._redact_value_by_key(k, v, depth + 1)
            else:
                redacted[k] = cls.redact(v, depth + 1)
        return redacted

    @classmethod
    def _redact_sqlalchemy(cls, obj: Any, depth: int) -> Dict[str, Any]:
        sensitive_fields = SchemaRegistry.get_sensitive_fields(type(obj))
        redacted = {}
        try:
            from sqlalchemy import inspect as sqla_inspect
            state = sqla_inspect(obj)
            if state:
                # Retain ID for context
                # Redact columns
                for attr in state.mapper.column_attrs:
                    key = attr.key
                    if key in state.unloaded:
                        continue
                    value = getattr(obj, key)
                    if key in sensitive_fields:
                        redacted[key] = cls._redact_value_by_key(key, value, depth + 1)
                    else:
                        redacted[key] = cls.redact(value, depth + 1)
                
                # Redact relationships
                for rel in state.mapper.relationships:
                    key = rel.key
                    if key in state.unloaded:
                        continue
                    value = getattr(obj, key)
                    redacted[key] = cls.redact(value, depth + 1)
                    
                return redacted
        except Exception:
            pass
        return cls._redact_generic(obj, depth)

    @classmethod
    def _redact_generic(cls, obj: Any, depth: int) -> Dict[str, Any]:
        sensitive_fields = SchemaRegistry.get_sensitive_fields(type(obj))
        redacted = {}
        for k, v in obj.__dict__.items():
            if k.startswith("_"): continue
            if k in sensitive_fields:
                redacted[k] = cls._redact_value_by_key(k, v, depth + 1)
            else:
                redacted[k] = cls.redact(v, depth + 1)
        return redacted

class DeepRedactorFormatter(logging.Formatter):
    """
    Logging Formatter that deeply redacts PII from log arguments.
    Ensures that even if developers log raw objects, PII is masked.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Create a shallow copy of record to avoid permanently mutating it if multiple handlers exist
        # But logging.Formatter.format typically works on the original record.
        # To be safe and compliant with "zero impact on API response times", 
        # we redact in-place but only what's necessary.
        
        # 1. Redact positional arguments (record.args)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: DeepRedactor.redact(v) for k, v in record.args.items()}
            else:
                # tuple is immutable, so we replace it
                record.args = tuple(DeepRedactor.redact(arg) for arg in record.args)

        # 2. Redact the message itself (record.msg)
        if isinstance(record.msg, str):
            record.msg = DeepRedactor.redact(record.msg)
            
        # 3. Redact 'extra' fields
        standard_record_attrs = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
            'processName', 'process', 'message', 'asctime', 'request_id'
        }
        
        for key, value in record.__dict__.items():
            if key not in standard_record_attrs and not key.startswith("_"):
                record.__dict__[key] = DeepRedactor.redact(value)

        return super().format(record)
