#!/usr/bin/env python3
"""
Script to check for gendered terms in the codebase and question bank.
Ensures the application remains inclusive and gender-neutral.
"""

import os
import re
import sys

# Define gendered terms to look for
GENDERED_TERMS = [
    r"\bhe\b", r"\bshe\b", r"\bhim\b", r"\bher\b", r"\bhis\b", r"\bhers\b",
    r"\bman\b", r"\bwoman\b", r"\bmen\b", r"\bwomen\b",
    r"\bmale\b", r"\bfemale\b",
    r"\bboy\b", r"\bgirl\b", r"\bboys\b", r"\bgirls\b",
    r"\bfather\b", r"\bmother\b", r"\bdad\b", r"\bmom\b",
    r"\bhusband\b", r"\bwife\b",
    r"\bguy\b", r"\bguys\b", r"\blady\b", r"\bladies\b"
]

# Files/Directories to exclude
EXCLUDE_DIRS = [
    '.git', '__pycache__', 'venv', 'env', '.pytest_cache', 
    'scripts/check_gender_bias.py',  # Exclude this script itself
    'logs', 'migrations', 'frontend-web', 'mobile-app', 
    '.mypy_cache', 'SOUL_SENSE_EXAM', 'soulsense_db'
]

EXCLUDE_FILES = [
    'LICENSE.txt', 'COMPLIANCE.md', 'RISK_ASSESSMENT.md', 
    'README.md', 'RESEARCH_REFERENCES.md', 'FAQ.md' # Documentation might mention these terms in context
]

def is_excluded(filepath):
    # Normalize path separator
    filepath = filepath.replace('\\', '/')
    parts = filepath.split('/')
    
    # Check if any part of the path is in EXCLUDE_DIRS
    for part in parts:
        if part in EXCLUDE_DIRS:
            # But wait, the root folder itself might be named SOUL_SENSE_EXAM.
            # We want to exclude the *inner* duplicate, not the root.
            # Ideally, we rely on os.walk's dirs[:] modification for directories.
            # But this function is used for files too.
            # Let's trust the os.walk filter for directories.
            # However, for files, we need to be careful.
            pass

    # Actually, the loop in scan_codebase handles removing excluded directories from traversal.
    # So we don't need to check directories in the filepath here, UNLESS the file itself is excluded.
    # The current implementation of scan_codebase does:
    # dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    # So we won't even enter excluded directories.
    # Therefore, is_excluded(filepath) mainly protects against file-level exclusions
    # or if we are passed a specific file path directly.
    
    if os.path.basename(filepath) in EXCLUDE_FILES:
        return True
        
    return False

def check_file(filepath):
    """Checks a single file for gendered terms."""
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # Whitelist specific lines (like citations)
                if "Haibo He" in line:
                    continue
                
                # Whitelist demographic options/definitions (where Male/Female appear together)
                if "Male" in line and "Female" in line:
                    continue
                    
                for term in GENDERED_TERMS:
                    if re.search(term, line, re.IGNORECASE):
                        # Filter out false positives if needed (e.g. 'hero' contains substring 'h-e-r')
                        # The regex uses \b boundary, so 'hero' is safe.
                        issues.append((line_num, term, line.strip()))
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return issues

def scan_codebase(root_dir):
    """Scans the codebase recursively."""
    all_issues = {}
    files_scanned = 0

    for root, dirs, files in os.walk(root_dir):
        # Remove excluded dirs from traversal
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            filepath = os.path.join(root, file)
            if is_excluded(filepath):
                continue
            
            # Check only text-based files
            if not file.endswith(('.py', '.txt', '.md', '.json', '.html', '.js', '.css')):
                continue

            files_scanned += 1
            issues = check_file(filepath)
            if issues:
                all_issues[filepath] = issues

    return all_issues, files_scanned

def main():
    print("Starting Gender Bias Check...")
    root_directory = os.getcwd()
    issues, count = scan_codebase(root_directory)
    
    print(f"Scanned {count} files.")
    
    if issues:
        print("\n\033[91mFound potential gendered terms:\033[0m")
        for filepath, file_issues in issues.items():
            print(f"\nFile: {filepath}")
            for line_num, term, content in file_issues:
                clean_term = term.replace(r'\b', '')
                print(f"  Line {line_num}: Found '{clean_term}' -> \"{content}\"")
        print("\n\033[91mFAILURE: Gendered terms detected. Please review and replace with neutral language.\033[0m")
        sys.exit(1)
    else:
        print("\n\033[92mSUCCESS: No gendered terms found. Codebase appears gender-neutral.\033[0m")
        sys.exit(0)

if __name__ == "__main__":
    main()
