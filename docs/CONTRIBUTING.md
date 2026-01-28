# Contributing to SOUL_SENSE_EXAM

Thank you for your interest in contributing to **SOUL_SENSE_EXAM** 🎉  
We welcome contributions of all kinds, including bug fixes, improvements, documentation, and new features.

Please take a moment to read this guide before getting started.

---

## How to Contribute

### 1. Fork the Repository

1. Go to the project repository on GitHub
2. Click the **Fork** button (top‑right)
3. This will create a copy of the repository under your GitHub account

---

### 2. Clone the Forked Repository

Clone your fork to your local machine:

```bash
git clone https://github.com/<your-username>/SOUL_SENSE_EXAM.git
cd SOUL_SENSE_EXAM
```

Add the original repository as an upstream remote:

```bash
git remote add upstream https://github.com/nupurmadaan04/SOUL_SENSE_EXAM.git
```

---

### 3. Create a New Branch

Always create a new branch for your changes:

```bash
git checkout -b feature/your-branch-name
```

---

### 4. Make Your Changes

- Follow the existing project structure and coding style
- Keep changes focused and minimal
- Add comments where necessary
- Test your changes before committing

### 5. Run Quality Checks Locally

Before committing, please ensure your code passes all quality checks to avoid CI failures:

#### 1. Type Checking

We use **mypy** for static type checking. Your code must pass with **0 errors**.

```bash
python -m mypy app/
```

#### 2. Gender Bias Check

Ensure your code uses inclusive language.

```bash
python scripts/check_gender_bias.py
```

_Note: This script scans the entire codebase (excluding generated files)._

#### 3. Run Tests

We use `pytest` for testing. Run all tests with:

```bash
python -m pytest tests/
```

To run tests with coverage report:

```bash
python -m coverage run --source=app -m pytest tests/
python -m coverage report -m
```

The suite includes:

- **Unit Tests**: `tests/test_exam_service.py`, `tests/test_cli_refactored.py`, `tests/test_cli_extended.py`
- **Integration Tests**: `tests/test_profile_integration.py`
- **Logic Tests**: `tests/test_questions_logic.py`

Please ensure all tests pass (or known failures are marked `xfail`) before submitting a PR.

#### 4. Frontend Quality Checks (Web)

If you are working in the `frontend-web` directory:

1.  **Strict Linting**: Architectural boundaries and import rules are checked via ESLint.
    ```bash
    cd frontend-web
    npm run lint
    ```
2.  **Production Build**: Ensure the application compiles without errors.
    ```bash
    npm run build
    ```

---

### 5. Commit Your Changes

Write clear and meaningful commit messages.

#### Commit message guidelines:

- Use the present tense (e.g., “Add validation logic”)
- Keep it short and descriptive
- Reference issues if applicable

Example:

```bash
git commit -m "Add input validation for login form"
```

---

### 6. Push Changes to Your Fork

```bash
git push origin feature/your-branch-name
```

---

## 7. Submit a Pull Request (PR)

1. Go to the original repository on GitHub.
2. Click **New Pull Request**.
3. Select your branch from your fork.
4. Provide a clear description of:
   - What you changed
   - Why the change is needed
   - Any related issues

---

### Please Ensure

- Your PR is based on the latest `main` branch
- The code builds and runs correctly
- No unnecessary files are included

---

## Coding Guidelines

- Follow consistent formatting and naming conventions
- Avoid hard-coded values where possible
- Write clean, readable, and maintainable code
- Comment complex or non-obvious logic

---

## Code Review Process

- Maintainers will review your pull request
- You may be asked to make changes
- Once approved, your PR will be merged 🎉
