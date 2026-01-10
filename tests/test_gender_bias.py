
import pytest
import os
from scripts.check_gender_bias import scan_codebase

def test_no_gender_bias_in_codebase():
    """
    Ensures that the codebase remains free of non-inclusive gendered terms.
    Uses the logic from scripts/check_gender_bias.py.
    """
    root_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    issues, count = scan_codebase(root_directory)
    
    assert count > 0, "Should have scanned some files"
    
    if issues:
        error_msg = "\nFound potential gendered terms:\n"
        for filepath, file_issues in issues.items():
            error_msg += f"\nFile: {filepath}\n"
            for line_num, term, content in file_issues:
                error_msg += f"  Line {line_num}: Found '{term.replace(r'\\b', '')}' -> \"{content}\"\n"
        pytest.fail(error_msg)
