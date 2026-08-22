"""
Filesystem Case-Sensitivity Conflict Detector

Detects filename conflicts across case-sensitive and case-insensitive environments.
Helps prevent deployment failures caused by inconsistent casing.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Set


# Directories to ignore during scanning
IGNORED_DIRS = {
    '.git', '.venv', '__pycache__', '.pytest_cache', '.coverage',
    'node_modules', 'htmlcov', '.ipynb_checkpoints', 'dist', 'build',
    '.github', '.env', 'migrations', 'logs'
}

# File extensions to ignore
IGNORED_EXTENSIONS = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe'}


def get_git_files(repo_path: str = '.') -> List[str]:
    """Get all files tracked by git."""
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split('\n') if f]
    except Exception:
        pass
    return []


def scan_directory(path: str, max_depth: int = 50) -> List[Dict[str, Any]]:
    """
    Scan directory recursively for case-sensitive filename conflicts.
    
    Uses git if available for accurate detection, falls back to filesystem.
    
    Args:
        path: Root directory to scan
        max_depth: Maximum recursion depth (prevent processing very deep trees)
    
    Returns:
        List of conflicts found, each containing:
        {
            'directory': str,
            'files': List[str],
            'severity': 'high'
        }
    """
    if not os.path.exists(path):
        return []
    
    conflicts = []
    
    # Try git first (more reliable for detecting case issues)
    git_conflicts = _check_git_conflicts(path)
    if git_conflicts:
        return git_conflicts
    
    # Fallback to filesystem scan
    ignored_paths = _get_ignored_paths(path)
    
    for dirpath, dirnames, filenames in os.walk(path):
        # Stop if too deep
        depth = dirpath.replace(path, '').count(os.sep)
        if depth > max_depth:
            dirnames[:] = []
            continue
        
        # Skip ignored directories
        dirnames[:] = [d for d in dirnames 
                      if d not in IGNORED_DIRS and 
                      os.path.join(dirpath, d) not in ignored_paths]
        
        # Skip symlinks
        if os.path.islink(dirpath):
            dirnames[:] = []
            continue
        
        # Check for case conflicts in this directory
        conflict = _check_case_conflicts(dirpath, filenames)
        if conflict:
            conflicts.append(conflict)
    
    return conflicts


def _get_ignored_paths(root_path: str) -> Set[str]:
    """Get set of paths to ignore during scan."""
    ignored = set()
    
    for dirpath, dirnames, _ in os.walk(root_path):
        for dirname in IGNORED_DIRS:
            full_path = os.path.join(dirpath, dirname)
            if os.path.exists(full_path):
                ignored.add(os.path.normpath(full_path))
        
        # Stop early
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
    
    return ignored


def _check_git_conflicts(repo_path: str) -> List[Dict[str, Any]]:
    """Check git index for case-sensitivity conflicts."""
    try:
        git_files = get_git_files(repo_path)
        if not git_files:
            return []
        
        # Group by directory and lowercase filename
        by_dir_lower: Dict[str, Dict[str, List[str]]] = {}
        
        for filepath in git_files:
            # Skip ignored extensions
            if any(filepath.endswith(ext) for ext in IGNORED_EXTENSIONS):
                continue
            
            directory = os.path.dirname(filepath) or '.'
            filename = os.path.basename(filepath)
            
            if directory not in by_dir_lower:
                by_dir_lower[directory] = {}
            
            key = filename.lower()
            if key not in by_dir_lower[directory]:
                by_dir_lower[directory][key] = []
            by_dir_lower[directory][key].append(filename)
        
        # Find conflicts
        conflicts = []
        for directory, groups in by_dir_lower.items():
            for lowercase_name, file_list in groups.items():
                if len(file_list) > 1 and len(set(file_list)) > 1:
                    conflicts.append({
                        'directory': directory,
                        'files': sorted(set(file_list)),
                        'severity': 'high'
                    })
        
        return conflicts
    except Exception:
        return []


def _check_case_conflicts(directory: str, filenames: List[str]) -> Dict[str, Any] | None:
    """
    Check for case-sensitive conflicts in a single directory.
    
    Args:
        directory: Directory path
        filenames: List of filenames in directory
    
    Returns:
        Conflict dict if found, None otherwise
    """
    if not filenames:
        return None
    
    # Group files by lowercase name
    groups: Dict[str, List[str]] = {}
    for filename in filenames:
        # Skip files we don't care about
        if any(filename.endswith(ext) for ext in IGNORED_EXTENSIONS):
            continue
        
        key = filename.lower()
        if key not in groups:
            groups[key] = []
        groups[key].append(filename)
    
    # Find conflicts (same lowercase name, different actual case)
    conflicts_found = []
    for lowercase_name, file_list in groups.items():
        if len(file_list) > 1 and len(set(file_list)) > 1:
            conflicts_found.extend(file_list)
    
    if conflicts_found:
        rel_dir = os.path.relpath(directory, os.path.dirname(directory))
        return {
            'directory': rel_dir,
            'files': sorted(conflicts_found),
            'severity': 'high'
        }
    
    return None


def check_git_staged_files(repo_path: str = '.') -> List[Dict[str, Any]]:
    """
    Check only staged Git files for case conflicts.
    
    Args:
        repo_path: Git repository root
    
    Returns:
        List of conflicts found in staged files
    """
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            return []
        
        staged_files = result.stdout.strip().split('\n')
        staged_files = [f for f in staged_files if f]
        
        if not staged_files:
            return []
        
        # Group by directory
        by_dir: Dict[str, List[str]] = {}
        for filepath in staged_files:
            directory = os.path.dirname(filepath) or '.'
            filename = os.path.basename(filepath)
            
            if directory not in by_dir:
                by_dir[directory] = []
            by_dir[directory].append(filename)
        
        # Check each directory
        conflicts = []
        for directory, filenames in by_dir.items():
            conflict = _check_case_conflicts(directory, filenames)
            if conflict:
                conflicts.append(conflict)
        
        return conflicts
    except Exception:
        return []


def generate_report(conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate JSON report from conflicts.
    
    Args:
        conflicts: List of conflicts
    
    Returns:
        Report dictionary
    """
    return {
        'total_conflicts': len(conflicts),
        'conflicts': conflicts,
        'status': 'FAILED' if conflicts else 'PASSED'
    }


def format_report_text(report: Dict[str, Any]) -> str:
    """
    Format report as human-readable text.
    
    Args:
        report: Report dictionary
    
    Returns:
        Formatted text report
    """
    conflict_count = report['total_conflicts']
    
    if conflict_count == 0:
        return "✓ No case-sensitivity conflicts found"
    
    lines = [
        f"✗ Case-Sensitivity Conflicts Detected ({conflict_count}):\n"
    ]
    
    for conflict in report['conflicts']:
        lines.append(f"  Directory: {conflict['directory']}")
        for filename in conflict['files']:
            lines.append(f"    - {filename}")
        lines.append("")
    
    return '\n'.join(lines)

