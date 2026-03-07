# Static Analysis Severity Budget Enforcement

## Overview

This feature enforces quality gates by comparing actual static analysis violations against configured severity budgets for `mypy`, `flake8`, and `bandit`.

## Components

### 1. Configuration (`config/static_analysis_budget.json`)
Defines maximum allowed violations per severity level for each tool:
- **CRITICAL**: Syntax errors, security vulnerabilities (0 allowed by default)
- **HIGH**: Type errors, complexity issues
- **MEDIUM**: Type mismatches, style violations
- **LOW**: Minor warnings, info-level issues

### 2. Enforcement Script (`scripts/static_analysis_gate.py`)
- Runs mypy, flake8, and bandit
- Classifies violations by severity
- Compares against configured budgets
- Generates detailed JSON reports
- Exits with failure if any budget is exceeded

### 3. CI Integration (`.github/workflows/python-app.yml`)
- Runs enforcement step after vulnerability scanning
- Uploads report artifacts for audit trail
- Blocks PRs if severity budget is exceeded

## Usage

### Run Locally
```bash
python scripts/static_analysis_gate.py --config config/static_analysis_budget.json --report report.json
```

### Adjust Budgets
Edit `config/static_analysis_budget.json` to increase/decrease limits per tool and severity level.

## Report Output

Example report structure:
```json
{
  "status": "pass|fail",
  "summary": {
    "mypy": { "passed": true, "summary": {...}, "exceeded": [] },
    "flake8": { "passed": true, "summary": {...}, "exceeded": [] },
    "bandit": { "passed": true, "summary": {...}, "exceeded": [] }
  },
  "violations": {
    "mypy": { "critical": 0, "high": 0, "medium": 0, "low": 0 },
    "flake8": { "critical": 0, "high": 0, "medium": 0, "low": 0 },
    "bandit": { "critical": 0, "high": 0, "medium": 0, "low": 0 }
  }
}
```

## Severity Classification

### MyPy
- CRITICAL: Syntax errors, invalid syntax
- HIGH: No-redef, name-defined, type-var errors
- MEDIUM: Assignment, call-arg, union-attr errors
- LOW: Other type checking warnings

### Flake8
- CRITICAL: E9xx (syntax errors)
- HIGH: C9xx (McCabe complexity)
- MEDIUM: E1xx, E2xx, E7xx (logic errors)
- LOW: Style and formatting warnings

### Bandit
- Uses tool's native severity classification
- CRITICAL/HIGH: High-severity security issues
- MEDIUM: Medium-severity issues
- LOW: Low-severity warnings

## Failure Scenarios

The gate fails if:
1. Any tool reports violations exceeding the limit for its severity level
2. Tools fail to run (gracefully handled with logging)
3. Configuration file is missing or invalid

## Next Steps

- Monitor reports for violations
- Adjust budgets as code quality improves
- Add `# noqa`, `# type: ignore` comments for exceptions (requires PR justification)
