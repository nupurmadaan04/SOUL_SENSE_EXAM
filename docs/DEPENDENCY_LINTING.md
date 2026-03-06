# Service-Layer Dependency Graph Linting

## Overview

Comprehensive dependency analysis system that enforces architectural boundaries, prevents circular dependencies, and maintains clean architecture compliance in the SoulSense backend.

## Features

✅ **Circular Dependency Detection** - Uses DFS algorithms to detect circular imports  
✅ **Layer Violation Detection** - Enforces architectural boundaries between layers  
✅ **Dynamic Import Support** - Handles `importlib`, `__import__`, and conditional imports  
✅ **Visualization** - Generates DOT/SVG graphs and interactive HTML reports  
✅ **CI/CD Integration** - Automated checks in GitHub Actions  
✅ **Comprehensive Testing** - Full test suite with edge case coverage

## Quick Start

### Analyze Dependencies

```bash
# Analyze backend directory
python scripts/dependency_analyzer.py backend/

# Generate full report with visualization
python scripts/dependency_analyzer.py backend/ --report --visualize --format both

# Check for circular dependencies only (CI mode)
python scripts/dependency_analyzer.py backend/ --check-circular

# Check for layer violations
python scripts/dependency_analyzer.py backend/ --check-layers
```

### Run CI Linter

```bash
# Run all checks
python scripts/ci_dependency_lint.py backend/

# Strict mode (warnings also fail)
python scripts/ci_dependency_lint.py backend/ --strict

# Report only (never fails)
python scripts/ci_dependency_lint.py backend/ --no-fail
```

### Generate Visualizations

```bash
# Generate HTML visualization
python scripts/dependency_visualizer.py backend/ --format html

# Generate SVG graph (requires Graphviz)
python scripts/dependency_visualizer.py backend/ --format svg

# Generate both
python scripts/dependency_visualizer.py backend/ --format both
```

## Architecture

### Architectural Layers

The system enforces a strict layered architecture:

```
┌─────────────────────────────────────────┐
│              Router Layer               │ ← API endpoints
│  (can import: service, schema, util)   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│             Service Layer               │ ← Business logic
│  (can import: repository, model, util) │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│           Repository Layer              │ ← Data access
│     (can import: model, util)           │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│             Model Layer                 │ ← Database models
│      (can import: exception)            │
└─────────────────────────────────────────┘
```

### Components

#### 1. Dependency Analyzer (`dependency_analyzer.py`)

Core analysis engine that:

- Scans Python files recursively
- Extracts imports using AST parsing
- Builds dependency graphs
- Detects circular dependencies using DFS
- Identifies architectural layer violations

**Key Classes:**

- `Module` - Represents a Python module
- `CircularDependency` - Represents a detected cycle
- `DependencyAnalyzer` - Main analyzer class

#### 2. CI Linter (`ci_dependency_lint.py`)

CI/CD integration that:

- Runs all dependency checks
- Generates structured reports
- Determines appropriate exit codes
- Enforces quality gates

**Exit Codes:**

- `0` - All checks passed
- `1` - Circular dependencies found
- `2` - Layer violations found
- `3` - Excessive dependencies found
- `4` - Multiple violations or critical issues

#### 3. Dependency Rules (`dependency_rules.py`)

Configuration for:

- Layer hierarchy definitions
- Module-specific rules
- Exclusion patterns
- CI/CD settings
- Visualization settings

#### 4. Visualizer (`dependency_visualizer.py`)

Generates:

- DOT files for Graphviz
- SVG vector graphics
- Interactive HTML reports
- Circular dependency highlights

## Usage Examples

### Example 1: Check for Circular Dependencies

```bash
python scripts/dependency_analyzer.py backend/ --check-circular
```

**Output:**

```
Scanning directory: backend/
Found 45 modules

================================================================================
DEPENDENCY ANALYSIS REPORT
================================================================================

Total Modules: 45
Total Dependencies: 127
Average Dependencies per Module: 2.82
Circular Dependencies: 2
Layer Violations: 0

--------------------------------------------------------------------------------
CIRCULAR DEPENDENCIES:
--------------------------------------------------------------------------------
  [ERROR] auth_service -> user_service -> profile_service -> auth_service
  [ERROR] exam_service -> question_service -> exam_service

❌ FAIL: Found 2 circular dependencies
```

### Example 2: Generate Visualization

```bash
python scripts/dependency_visualizer.py backend/ --output backend_deps
```

Creates:

- `backend_deps.dot` - Graphviz DOT file
- `backend_deps.svg` - Vector graphic
- `backend_deps.html` - Interactive report

### Example 3: Run Full CI Check

```bash
python scripts/ci_dependency_lint.py backend/ --output reports/ci_report.json
```

**Output:**

```
🔍 Running dependency checks...
   Root path: backend/
   Strict mode: False

📊 Checking for circular dependencies...
   ❌ Found 1 circular dependencies
📊 Checking for layer violations...
   ✅ No layer violations found
📊 Checking for excessive dependencies...
   ⚠️  Found 3 modules with excessive dependencies
📊 Checking critical modules...
   ✅ No issues in critical modules

================================================================================
DEPENDENCY LINT SUMMARY
================================================================================

Status: FAILED
Total Modules: 45
Total Dependencies: 127
Errors: 1
Warnings: 3
Critical Issues: 0

❌ Dependency checks failed with exit code: 1
```

## Configuration

### Layer Rules (`dependency_rules.py`)

Customize architectural boundaries:

```python
LAYER_HIERARCHY = {
    'router': {
        'allowed': ['service', 'schema', 'exception', 'util'],
        'forbidden': ['router'],
        'description': 'API route handlers and endpoints'
    },
    'service': {
        'allowed': ['model', 'schema', 'exception', 'util', 'repository'],
        'forbidden': ['router', 'service'],
        'description': 'Business logic layer'
    },
    # ... more layers
}
```

### Maximum Dependencies

Set limits per layer:

```python
MODULE_RULES = {
    'max_dependencies': {
        'default': 15,
        'service': 10,
        'router': 8,
        'util': 5,
        'exception': 0
    }
}
```

### Exclusion Patterns

Exclude directories from analysis:

```python
EXCLUDE_PATTERNS = [
    '__pycache__',
    '.venv',
    'tests',
    'migrations',
    'alembic'
]
```

## CI/CD Integration

### GitHub Actions

The system includes a complete GitHub Actions workflow (`.github/workflows/dependency-lint.yml`):

**Features:**

- Runs on every push to `main` or `develop`
- Checks both `backend/` and `app/` directories
- Generates visualization artifacts
- Comments on PRs with results
- Fails build if violations found

**Setup:**

1. Commit the workflow file
2. Push to GitHub
3. Workflow runs automatically

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash

echo "Running dependency checks..."

python scripts/ci_dependency_lint.py backend/ --output /tmp/dep_report.json

if [ $? -ne 0 ]; then
    echo "❌ Dependency checks failed!"
    echo "Fix circular dependencies before committing."
    exit 1
fi

echo "✅ Dependency checks passed!"
```

Make executable:

```bash
chmod +x .git/hooks/pre-commit
```

## Testing

### Run Test Suite

```bash
# Run all tests
python -m pytest tests/test_dependency_analyzer.py -v

# Run specific test
python -m pytest tests/test_dependency_analyzer.py::TestDependencyAnalyzer::test_simple_circular_dependency -v

# Run integration test
python tests/test_dependency_analyzer.py
```

### Test Coverage

The test suite covers:

- ✅ Simple circular dependencies (A → B → A)
- ✅ Complex circular dependencies (A → B → C → A)
- ✅ No false positives on clean dependencies
- ✅ Layer detection accuracy
- ✅ Layer violation detection
- ✅ Dynamic import detection (`importlib`)
- ✅ Conditional imports (`TYPE_CHECKING`)
- ✅ Plugin systems
- ✅ Syntax error handling
- ✅ Empty projects
- ✅ Self-imports

## Edge Cases Handled

### 1. Dynamic Imports

```python
import importlib

# Detected by analyzer
module = importlib.import_module('some_module')
```

### 2. Conditional Imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Still analyzed
    from some_module import SomeClass
```

### 3. Plugin Systems

```python
# Dynamic plugin loading
for plugin_name in discover_plugins():
    plugin = importlib.import_module(f'plugins.{plugin_name}')
```

### 4. Syntax Errors

Files with syntax errors are skipped gracefully without crashing the analyzer.

### 5. Self-Imports

Modules importing themselves are detected and handled appropriately.

## Troubleshooting

### No Graphviz Installation

If you see:

```
⚠️ Graphviz 'dot' command not found
```

**Install Graphviz:**

- **Windows:** `choco install graphviz`
- **Linux:** `sudo apt-get install graphviz`
- **macOS:** `brew install graphviz`

### False Positives

If you get false positives for circular dependencies:

1. Check if imports are actually circular
2. Review the cycle in the report
3. Consider if the dependency is necessary
4. Refactor to break the cycle

### Layer Detection Issues

If layers are incorrectly detected:

1. Ensure consistent naming (e.g., `*_service.py` for services)
2. Place files in appropriately named directories
3. Update `detect_layer()` method if needed

## Metrics & Reports

### Report Structure

```json
{
  "status": "passed",
  "summary": {
    "total_modules": 45,
    "total_dependencies": 127,
    "errors": 0,
    "warnings": 2,
    "critical_issues": 0
  },
  "violations": {
    "circular": [],
    "layer": [],
    "excessive": [],
    "critical": []
  },
  "metadata": {
    "root_path": "backend/",
    "strict_mode": false,
    "timestamp": "2026-03-06T10:30:00"
  }
}
```

### Key Metrics

- **Total Modules** - Number of Python modules analyzed
- **Total Dependencies** - Sum of all import relationships
- **Average Dependencies** - Mean dependencies per module
- **Circular Dependencies** - Number of detected cycles
- **Layer Violations** - Count of architectural violations

## Best Practices

### 1. Keep Services Independent

❌ **Bad:**

```python
# user_service.py
from profile_service import ProfileService

class UserService:
    def __init__(self):
        self.profile_svc = ProfileService()
```

✅ **Good:**

```python
# user_service.py
class UserService:
    def __init__(self, profile_svc=None):
        self.profile_svc = profile_svc  # Dependency injection
```

### 2. Use Dependency Injection

Break circular dependencies by injecting dependencies rather than importing them.

### 3. Create Shared Models

Instead of services importing from each other, create shared model/schema modules.

### 4. Follow Layer Boundaries

- Routers call services
- Services call repositories
- Repositories access models
- Never reverse these relationships

### 5. Run Checks Frequently

```bash
# Before committing
python scripts/ci_dependency_lint.py backend/ --no-fail

# Before pushing
python scripts/ci_dependency_lint.py backend/
```

## Performance

### Benchmark Results

Tested on SoulSense backend (45 modules, 127 dependencies):

- **Scan & Build:** ~0.5s
- **Circular Detection:** ~0.1s
- **Layer Violation Check:** ~0.05s
- **Report Generation:** ~0.02s
- **Total:** ~0.7s

Performance scales roughly O(N + E) where N = modules, E = edges.

## Contributing

### Adding New Checks

1. Add check method to `DependencyAnalyzer`
2. Update `CILinter` to call new check
3. Add tests to `test_dependency_analyzer.py`
4. Update documentation

### Adding New Layers

1. Update `LAYER_HIERARCHY` in `dependency_rules.py`
2. Update `detect_layer()` method if needed
3. Add color to visualization config
4. Document the new layer

## Support

For issues or questions:

1. Check this documentation
2. Review test cases for examples
3. Check GitHub Issues
4. Create a new issue with details

## License

Same as SoulSense project.

## Changelog

### Version 1.0.0 (2026-03-06)

- Initial release
- Circular dependency detection
- Layer violation detection
- Visualization support
- CI/CD integration
- Comprehensive test suite
- Edge case handling
