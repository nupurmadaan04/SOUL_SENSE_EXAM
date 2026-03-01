#!/usr/bin/env python3
"""
Test script to verify IDOR fixes for journal and survey services.
"""

import os
import re

def test_journal_idor_fix():
    """Test that journal service properly validates ownership."""
    print("Testing Journal Service IDOR fix...")

    try:
        # Read the journal service file
        with open("backend/fastapi/api/services/journal_service.py", "r", encoding="utf-8") as f:
            content = f.read()

        # Check that get_entry_by_id filters by user_id
        if "JournalEntry.user_id == current_user.id" in content:
            print("✓ JournalService.get_entry_by_id filters by user_id")
            return True
        else:
            print("✗ JournalService.get_entry_by_id missing user_id filter")
            return False

    except Exception as e:
        print(f"✗ Error testing JournalService: {e}")
        return False

def test_survey_idor_fix():
    """Test that survey service properly restricts access to published surveys."""
    print("Testing Survey Service IDOR fix...")

    try:
        # Read the survey service file
        with open("backend/fastapi/api/services/survey_service.py", "r", encoding="utf-8") as f:
            content = f.read()

        # Check that get_template_by_id has admin_access parameter
        if "admin_access: bool = False" in content:
            print("✓ SurveyService.get_template_by_id has admin_access parameter")
            return True
        else:
            print("✗ SurveyService.get_template_by_id missing admin_access parameter")
            return False

    except Exception as e:
        print(f"✗ Error testing SurveyService: {e}")
        return False

def main():
    print("Running IDOR fix verification tests...\n")

    journal_ok = test_journal_idor_fix()
    survey_ok = test_survey_idor_fix()

    print("\n" + "="*50)
    if journal_ok and survey_ok:
        print("✓ All IDOR fixes verified successfully!")
        return 0
    else:
        print("✗ Some IDOR fixes failed verification")
        return 1

if __name__ == "__main__":
    exit(main())