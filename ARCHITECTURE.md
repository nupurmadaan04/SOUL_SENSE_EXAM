# SoulSense Application Architecture & Module Documentation

## 1. High-Level Architecture
SoulSense is a **modular desktop application** built using **Python** and **Tkinter** for the frontend, following a **Layered Architecture**. The application separates concerns into three distinct layers:
- **Presentation Layer (UI):** Handles user interactions, rendering views, and navigation.
- **Business Logic Layer (Services/Managers):** Processes data, enforces rules (e.g., scoring logic, auth), and interfaces with the database.
- **Data Persistence Layer (DB/Models):** Manages SQLite storage using SQLAlchemy ORM.

## 2. Module Directory Structure
The application is organized as a Python package (`app/`) with sub-packages for specific domains:

```Plaintext
app/
├── main.py              # Application Entry Point & Orchestrator
├── config.py            # Configuration Management
├── db.py                # Database Connection & Session Management
├── models.py            # SQLAlchemy Data Models
├── auth.py              # Authentication Logic
├── i18n_manager.py      # Internationalization
├── ui/                  # Presentation Layer
│   ├── components/      # Reusable UI widgets
│   ├── dashboard.py     # Analytics Visualization
│   ├── exam.py          # Assessment Interface
│   ├── journal.py       # Journaling Interface
│   ├── sidebar.py       # Navigation Control
│   └── styles.py        # Theme & Style Management
└── services/            # Business Logic (Inferred from architecture)
    └── exam_service.py  # Exam Logic
```

## 3. Core Module Responsibilities
### A. Core Infrastructure
- `app.main` **(Orchestrator)**
    - **Responsibilities:** Initializes the root Tkinter window, manages global state (current user, theme), and orchestrates top-level navigation.
    - **Key Component:** `SoulSenseApp` class acts as the central dependency injection container, passing the `app` context to sub-modules.
    - **Interactions:** Listens to `SidebarNav` events to switch the `content_area frame`.
- `app.config` **(Configuration)**
    - **Responsibilities:** Loads settings from `config.json` (e.g., database path, themes). Provides sensible defaults if the file is missing and handles directory setup for logs/data.
    - **Data Flow:** Read on startup -> consumed by `db.py` and `main.py`.
- `app.db` **(Database Access)**
    - **Responsibilities:** Configures the SQLAlchemy engine and sessions. Provides the `safe_db_context` context manager to ensure atomic transactions (commit/rollback).
    - **Key Features:** Includes a fallback mechanism (`check_db_state`) to create tables using raw SQLite if ORM initialization fails.
- `app.models` **(Data Schema)**
    - **Responsibilities:** Defines the database structure.
    - **Key Models:**
        - `User`: Core identity and authentication data.
        - `Score` & `Response`: Quantitative assessment data.
        - `JournalEntry`: Unstructured text and sentiment data.
        - `MedicalProfile` / `PersonalProfile`: Contextual user data.
    - **Optimization:** Uses SQLAlchemy events to enable SQLite Write-Ahead Logging (WAL) and creates Full-Text Search (FTS5) indexes for performance.

### B. Feature Modules
- `app.auth` **(Authentication)**
    - **Responsibilities:** Handles user login, registration, and password hashing.
    - **Interactions:** Called by `main.py` before the main dashboard loads. Updates the `SoulSenseApp.current_user_id` upon success.
- `app.ui` **(User Interface)**
    - `sidebar.py`: Manages the persistent left-hand navigation menu.
    - `styles.py`: Centralizes styling (colors, fonts) and theme switching logic.
    - `dashboard.py`: Visualizes user progress using charts/graphs.
    - `exam.py`: Renders the question bank and records answers.

## 4. Data Flow & Interactions
### Scenario 1: User Login
1. **UI:** `SoulSenseApp` triggers `show_login_screen` on startup.
2. **Action:** User submits credentials.
3. **Logic:** `app.auth.AuthManager` verifies credentials against the `User` table in the DB.
4. **Result:** On success, `SoulSenseApp` loads user settings (theme, etc.) from `UserSettings` and unhides the sidebar.

### Scenario 2: Taking an Assessment
1. **Navigation:** User clicks "Assessment" in `SidebarNav`.
2. **Routing:** `SoulSenseApp.switch_view("exam")` clears the main area and initializes `ExamManager`.
3. **Data Retrieval:** `ExamManager` requests active questions (likely via `app.questions.load_questions` or `db`).
4. Submission:
    - `ExamManager` captures answers.
    - Data is passed to the database via `SessionLocal`.
    - `Score` and `Response` records are created within a transaction.

### Scenario 3: Changing Settings
1. **Action:** User changes theme to "Dark".
2. **Persistence:** `app.db.update_user_settings` is called to save the preference to SQLite.
3. **Feedback:** `SoulSenseApp.apply_theme` is triggered, notifying `UIStyles` to refresh the active widget colors immediately without a restart.

## 5. Technical Decisions & Patterns
- **Dependency Injection:** The main `app` instance is passed down to child views (e.g., `JournalFeature(..., app=self)`), allowing deep UI components to access shared resources like the database session or user ID.
- **Proxy Pattern:** The `ContentProxy` class in `main.py` allows embedded views (like `ResultsManager`) to treat a specific `Frame` as their "root" window, facilitating modularity.
- **Hybrid Data Access:** While SQLAlchemy is the primary ORM, the system includes raw SQL fallbacks for robust initialization and performance-critical operations (like bulk indexing).