# 🔍 Dependency Graph Linting - Quick Reference

## 🚀 Quick Start

```bash
# Interactive menu (recommended for first-time users)
python run_dependency_checks.py interactive

# Quick check
python run_dependency_checks.py quick backend

# Full analysis with visualization
python run_dependency_checks.py full backend

# CI mode (fails on violations)
python run_dependency_checks.py ci backend
```

## 📊 What Does It Do?

✅ Detects circular dependencies  
✅ Enforces architectural layer boundaries  
✅ Generates dependency visualizations  
✅ Provides detailed analysis reports  
✅ Integrates with CI/CD pipelines

## 🎯 Current Status

**Backend Analysis:**

- 51 modules scanned
- 31 circular dependencies found ⚠️
- 55 layer violations detected ⚠️
- Average 27.22 dependencies per module

## 📁 Key Files

| File                                | Purpose                 |
| ----------------------------------- | ----------------------- |
| `scripts/dependency_analyzer.py`    | Core analysis engine    |
| `scripts/ci_dependency_lint.py`     | CI/CD integration       |
| `scripts/dependency_rules.py`       | Configuration & rules   |
| `scripts/dependency_visualizer.py`  | Visualization generator |
| `run_dependency_checks.py`          | Easy-to-use interface   |
| `tests/test_dependency_analyzer.py` | Test suite              |
| `docs/DEPENDENCY_LINTING.md`        | Full documentation      |

## 🔧 Common Commands

### Analyze Dependencies

```bash
python scripts/dependency_analyzer.py backend/ --report
```

### Check for Circular Dependencies

```bash
python scripts/dependency_analyzer.py backend/ --check-circular
```

### Generate Visualization

```bash
python scripts/dependency_visualizer.py backend/ --format both
```

### Run CI Checks

```bash
python scripts/ci_dependency_lint.py backend/
```

### Run Tests

```bash
python -m pytest tests/test_dependency_analyzer.py -v
```

### Run Integration Test

```bash
python tests/test_dependency_analyzer.py
```

## 📈 Example Output

```
🔍 Running dependency checks...

📊 Summary:
   Modules: 51
   Dependencies: 1388
   Average: 27.22

⚠️  Found 31 circular dependencies:
   • auth_service → user_service → profile_service → auth_service
   • exam_service → question_service → exam_service

⚠️  Found 55 layer violations

✅ Analysis complete!
```

## 🎨 Visualization

Generates three types of output:

1. **DOT File** - Graphviz format for custom rendering
2. **SVG Graph** - Vector graphic with color-coded layers
3. **HTML Report** - Interactive report with metrics

Example:

```bash
python scripts/dependency_visualizer.py backend/ --output backend_deps
```

Creates:

- `backend_deps.dot`
- `backend_deps.svg`
- `backend_deps.html`

## 🏗️ Architecture Layers

```
Router (API endpoints)
   ↓ can import
Service (Business logic)
   ↓ can import
Repository (Data access)
   ↓ can import
Model (Database models)
```

**Rules:**

- Routers can import: services, schemas, utils
- Services can import: repositories, models, utils
- Models can only import: exceptions
- **Never reverse these relationships!**

## ⚙️ Configuration

Edit `scripts/dependency_rules.py` to customize:

- Layer hierarchy
- Maximum dependencies per module
- Exclusion patterns
- CI/CD settings
- Visualization colors

## 🚨 CI/CD Integration

### GitHub Actions

Workflow file includes at: `.github/workflows/dependency-lint.yml`

**Triggers on:**

- Push to main/develop
- Pull requests

**Actions:**

- Runs dependency checks
- Generates visualizations
- Posts PR comments
- Fails build on violations

### Exit Codes

- `0` - All checks passed
- `1` - Circular dependencies found
- `2` - Layer violations found
- `3` - Excessive dependencies
- `4` - Multiple violations

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/test_dependency_analyzer.py -v

# Run integration test
python tests/test_dependency_analyzer.py

# Expected output: ✅ INTEGRATION TEST PASSED
```

**Test Coverage:**

- Simple circular dependencies
- Complex circular dependencies
- Layer detection
- Layer violations
- Dynamic imports
- Conditional imports
- Plugin systems
- Edge cases

## 🔨 Fixing Violations

### Circular Dependencies

❌ **Bad:**

```python
# user_service.py
from profile_service import ProfileService

class UserService:
    def __init__(self):
        self.profile = ProfileService()
```

✅ **Good:**

```python
# user_service.py
class UserService:
    def __init__(self, profile_service=None):
        self.profile_service = profile_service  # Dependency injection
```

### Layer Violations

❌ **Bad:**

```python
# service/user_service.py
from routers.user_router import UserRouter  # Services shouldn't import routers!
```

✅ **Good:**

```python
# routers/user_router.py
from services.user_service import UserService  # Routers import services ✓
```

## 📚 Documentation

Full documentation available at:

- **`docs/DEPENDENCY_LINTING.md`** - Complete guide
- **`DEPENDENCY_IMPLEMENTATION_SUMMARY.md`** - Implementation details

## 🔗 Integration

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
python scripts/ci_dependency_lint.py backend/ --no-fail
```

### Make executable:

```bash
chmod +x .git/hooks/pre-commit
```

## 💡 Tips

1. **Run checks frequently** - Catch issues early
2. **Fix circular deps first** - They're the most critical
3. **Use dependency injection** - Breaks circular dependencies
4. **Respect layer boundaries** - Maintains clean architecture
5. **Keep services focused** - Limit dependencies per module

## 🐛 Troubleshooting

### Graphviz not found?

```bash
# Windows
choco install graphviz

# Linux
sudo apt-get install graphviz

# macOS
brew install graphviz
```

### False positives?

1. Check the reported cycle is actually circular
2. Review if the dependency is necessary
3. Refactor to break the cycle

### Performance slow?

- Exclude additional directories in `dependency_rules.py`
- Analyze specific subdirectories instead of entire project

## 📞 Support

1. Check documentation: `docs/DEPENDENCY_LINTING.md`
2. Review examples in test suite
3. Run integration test to verify setup
4. Open an issue with details

## 🎓 Next Steps

1. **Run Analysis**

   ```bash
   python run_dependency_checks.py interactive
   ```

2. **Review Report**
   - Check circular dependencies
   - Review layer violations
   - Note high-dependency modules

3. **Fix Issues**
   - Start with circular dependencies
   - Use dependency injection
   - Respect layer boundaries

4. **Enable CI**
   - Commit workflow file
   - Set up pre-commit hook
   - Make part of code review

## ✨ Features

✅ AST-based import analysis  
✅ Circular dependency detection  
✅ Layer violation detection  
✅ Dynamic import support  
✅ Conditional import handling  
✅ Plugin system support  
✅ DOT/SVG/HTML visualization  
✅ CI/CD integration  
✅ Comprehensive testing  
✅ Edge case handling  
✅ Report generation  
✅ Interactive interface

---

**Ready to get started?**

```bash
python run_dependency_checks.py interactive
```
