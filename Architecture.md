###  🧠 Soul Sense EQ Test — System Architecture
# 1. Overview

Soul Sense EQ Test is a desktop-based Emotional Intelligence (EQ) assessment system built using Python, Tkinter, and SQLite.
The architecture prioritizes:

- Clear separation of concerns

- Testability and maintainability

- Safe local persistence

- Incremental extensibility toward ML-powered insights

The system follows a layered architecture with the GUI acting as a thin interaction layer over decoupled business and data logic.

#

# 2. High-Level Architecture
```bash
┌────────────────────┐
│   Tkinter GUI      │
│  (Presentation)   │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Application Logic │
│ (Auth, EQ,        │
│ Journal, Utils)   │
└────────┬──────────┘
         │
┌────────▼──────────┐
│ Data Access Layer │
│ (SQLite + Models) │
└────────┬──────────┘
         │
┌────────▼──────────┐
│   SQLite DB       │
│ (Local Storage)  │
└──────────────────┘

```
# 3. GUI Layer (Tkinter)

Location: `app/main.py`

**Responsibilities:**

- Rendering application windows and views
- Managing navigation between screens (Login, Test, Results, Journal)
- Capturing user input
- Displaying scores, interpretations, and insights

**Design principles:**
- No direct database access
- No business logic embedded in UI widgets
- All logic delegated to application modules

Typical GUI Flow:
```bash
Login / Sign Up
      ↓
EQ Test
      ↓
Score Interpretation
      ↓
Journal (Optional)
      ↓
Logout
```
#

# 4. Application Logic Layer

This layer contains the core business logic and domain rules.

4.1 Authentication (`app/auth.py`)

- User registration and login
- Password hashing using SHA-256
- Session lifecycle management
- User-specific data isolation

4.2 EQ Test Logic
- Question retrieval from the database
- Likert-scale response handling
- EQ score computation
- Score interpretation mapping

4.3 Journal & Emotional Analysis
- Daily emotional reflection storage
- Sentiment scoring of journal entries
- Pattern detection (stress indicators, growth mindset, self-reflection)
- Emotional trend tracking over time

4.4 Shared Utilities (app/utils.py)
- Validation helpers
- Common formatting logic
- Reusable constants and helpers

#

# 5. Data Access Layer

5.1 Database Management (`app/db.py`)
- Centralized SQLite connection handling
- Runtime-safe schema initialization
- Backward-compatible schema migrations
- Transaction safety and consistency

5.2 Models (`app/models.py`)
- Declarative database models for:
    - Users
    - Questions
    - Responses
    - Scores
    - Journal entries

SQLite remains the authoritative persistence layer for simplicity and portability.

#

# 6. Migrations

Tool: Alembic
Location: migrations/

Responsibilities:
- Controlled schema evolution
- Safe upgrades without data loss
- Versioned migration scripts

Migration strategy:
- Backward-compatible changes only
- No destructive operations
- Explicit version control

# 7. Question Loading Architecture

Script: `scripts/load_questions.py`
Source: `data/questions.txt`

Key properties:
- One-time execution
- Idempotent loading
- Questions become read-only at runtime
- Ensures consistent scoring behavior

#
# 8. Data Flow

EQ Test Flow
```bash
User Input
  ↓
GUI Event
  ↓
Application Logic
  ↓
Score Calculation
  ↓
SQLite Persistence
  ↓
Result Interpretation
```
Journal Flow
```bash
User Entry
  ↓
Sentiment Analysis
  ↓
Pattern Detection
  ↓
Database Storage
  ↓
Historical Trend View
```

#
# 9. Testing Architecture

Framework: Pytest
Location: `tests/`

Testing characteristics:

- GUI-independent tests
- Temporary SQLite databases
- Isolated and deterministic test cases

Coverage includes:
- Authentication flows
- Database migrations
- EQ scoring logic

Journal persistence and analysis

#

# 10. Future ML Integration 

The architecture supports incremental machine learning integration without structural changes.

Planned integration areas:

- ML-based sentiment classification
- Emotional trend modeling
- Stress and anomaly detection
- Personalized reflection and EQ growth recommendations

Integration strategy:
- ML logic isolated in dedicated modules
- No GUI coupling
- No breaking schema changes
