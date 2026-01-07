# Testing Guidelines – SOUL_SENSE_EXAM

## 1. Overview

This document outlines the testing strategy for the **SOUL_SENSE_EXAM** application. It explains how to manually and programmatically test the core features, ensuring reliability, correctness, and a good user experience.

The application includes:
- Emotional intelligence (EQ) questionnaire
- Score calculation and interpretation
- Emotional journaling
- SQLite database persistence

---

## 2. Manual Testing

Manual testing verifies the application behavior from a user’s perspective, focusing on UI flows, data handling, and edge cases.

### 2.1 Environment Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/nupurmadaan04/SOUL_SENSE_EXAM
   cd SOUL_SENSE_EXAM
   ```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```


3. Install dependencies:
```bash
pip install -r requirements.txt
```
### 2.2 Application Launch Testing

Objective: Ensure the application starts correctly.

#### Steps:

1. Run the application:

```bash
python -m app.main
```
2. Observe the application window.

### Expected Result

- Application launches without errors.
- Main questionnaire interface is visible.

---

## 2.3 Questionnaire Flow Testing

### Objective
Verify that all questions render correctly and accept user input.

### Steps
1. Start a new EQ test.
2. Answer each question using different response values.
3. Complete the questionnaire.

### Expected Result
- All questions are displayed correctly.
- Responses are accepted.
- Final EQ score is calculated and shown with interpretation.

---

## 2.4 Database Persistence Testing

### Objective
Confirm that test results and responses are stored correctly.

### Steps
1. Complete a questionnaire.
2. Open the SQLite database file (for example, using DB Browser for SQLite).
3. Inspect stored records.

### Expected Result
- Responses and scores are saved correctly.
- No duplicate or corrupted entries exist.

---

## 2.5 Emotional Journal Testing

### Objective
Validate journaling and sentiment analysis functionality.

### Steps
1. Navigate to the emotional journal section.
2. Enter positive, neutral, and negative text entries.
3. Save the entry.

### Expected Result
- Journal entries are saved successfully.
- Sentiment analysis or insights are displayed correctly.

---

## 2.6 Error and Edge Case Testing

| Scenario | Expected Outcome |
|--------|------------------|
| Empty required input | User receives a validation message |
| Invalid input format | Application handles input gracefully |
| Exit mid-test | User is warned before data loss |

Main questionnaire interface is visible.

## 3. Programmatic Testing

Automated tests validate application logic and help prevent regressions by ensuring core functionality behaves as expected when changes are introduced.

---

### 3.1 Running Existing Tests

The project includes automated tests that cover the following areas:

- Database initialization and operations
- Model logic validation
- Question loading and formatting
- Utility and helper function correctness

These tests should be executed regularly during development to ensure system stability.

```bash
python -m pytest -v
```

---

### 3.2 Writing New Tests

New tests should be added whenever new features or logic are introduced.

#### 3.2.1 Score Calculation Testing

Score calculation logic should be tested to ensure accurate EQ results.  
Tests should validate that the total score is computed correctly based on user responses.

New test cases can be added in a dedicated file such as `test_scoring.py`.
```bash
def test_eq_score_calculation():
    answers = [1, 2, 3, 4]
    assert calculate_eq_score(answers) == sum(answers)
```

---

#### 3.2.2 Database Testing with Temporary Files

To avoid modifying production data during testing:

- Use temporary database files for automated tests
- Validate insert, read, and update operations
- Ensure test data does not persist after test execution

This approach helps maintain data integrity while testing database functionality.

---

### 3.3 GUI Logic Testing

Due to limitations in testing GUI applications with standard testing frameworks:

- Separate business logic from UI components
- Test logic functions independently through automated tests
- Perform manual verification for UI behavior and user interactions

---

## 4. Regression Testing

Regression testing ensures that existing features continue to work after updates.

Best practices include:

- Running all tests before merging code changes
- Adding new tests whenever features are added or modified
- Validating scoring logic when questionnaire content changes

Continuous Integration (CI) tools such as GitHub Actions are recommended to automate regression testing.

---

## 5. Bug Reporting

All bugs should be reported using the GitHub Issues section of the repository.

Use the following format when creating a bug report:

- **Title**
- **Description**
- **Steps to Reproduce**
- **Expected Result**
- **Actual Result**
- **Severity**

Providing detailed and clear bug reports helps maintain project quality and speeds up issue resolution.

#### Following these testing guidelines ensures the SOUL_SENSE_EXAM application remains stable, accurate, and user-friendly. Both manual and automated testing should be performed regularly during development.
