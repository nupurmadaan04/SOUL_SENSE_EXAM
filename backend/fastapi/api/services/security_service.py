import json
import os
import logging
from typing import Set

logger = logging.getLogger(__name__)

class SecurityService:
    _disposable_domains: Set[str] = set()
    _loaded: bool = False

    @classmethod
    def _load_domains(cls):
        """Loads disposable email domains from JSON resource."""
        if cls._loaded:
            return
        
        try:
            # Resolve path relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "..", "resources", "disposable_emails.json")
            
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    domains = json.load(f)
                    cls._disposable_domains = set(domains)
                cls._loaded = True
                logger.info(f"Loaded {len(cls._disposable_domains)} disposable email domains.")
            else:
                logger.warning(f"Disposable emails list not found at {json_path}")
        except Exception as e:
            logger.error(f"Failed to load disposable domains: {e}")

    @classmethod
    def is_disposable_email(cls, email: str) -> bool:
        """
        Safety check to identify disposable/temporary email addresses.
        Checks both the direct domain and parent domains for suffix matching.
        """
        if not email or "@" not in email:
            return False
            
        cls._load_domains()
        
        if not cls._disposable_domains:
            return False

        # Extract domain
        try:
            domain = email.split("@")[-1].lower().strip()
            
            # 1. Exact match
            if domain in cls._disposable_domains:
                return True
                
            # 2. Suffix/Parent domain match (e.g., sub.mailinator.com)
            parts = domain.split(".")
            # Reconstruct domains from right to left (min 2 parts like 'example.com')
            for i in range(len(parts) - 1):
                parent_domain = ".".join(parts[i:])
                if parent_domain in cls._disposable_domains:
                    return True
                    
            return False
        except Exception:
            return False
