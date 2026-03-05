import re
import unicodedata
import html
from typing import Optional

def sanitize_string(val: str, escape_html: bool = True) -> str:
    """
    Sanitizes a string input by performing:
    1. Unicode normalization (NFKC)
    2. Removal of null bytes and non-printable control characters
    3. Trimming whitespace
    4. Optional HTML escaping (default: True)
    """
    if not val or not isinstance(val, str):
        return val

    # 1. Unicode Normalization (prevents homoglyph/encoding bypasses)
    val = unicodedata.normalize('NFKC', val)

    # 2. Trim whitespace
    val = val.strip()

    # 3. Remove Null Bytes and non-printable control characters (except \n, \r, \t)
    # This preserves basic formatting while stripping potential exploit precursors.
    val = "".join(ch for ch in val if unicodedata.category(ch)[0] != "C" or ch in "\n\r\t")

    # 4. Context-aware HTML Escaping (Defense-in-depth for XSS)
    if escape_html:
        val = html.escape(val, quote=True)

    return val

def clean_identifier(val: str) -> str:
    """
    Strict cleaning for identifiers like usernames and emails.
    Removes ALL control characters and whitespace.
    """
    if not val or not isinstance(val, str):
        return val
    
    # Normalize
    val = unicodedata.normalize('NFKC', val)
    
    # Strip all whitespace and control characters
    val = "".join(val.split())
    val = "".join(ch for ch in val if unicodedata.category(ch)[0] != "C")
    
    return val.lower()
