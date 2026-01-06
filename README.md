# 🧠 Soul Sense EQ Test

Soul Sense EQ Test is a desktop-based Emotional Intelligence (EQ) assessment application built using Python, Tkinter, and SQLite.
It provides an interactive self-reflection test, persists results locally, and is designed with maintainability, testability, and extensibility in mind.

---

## ✨ Features

- **User Authentication:** Secure signup, login, and logout system
- Interactive Tkinter-based GUI
- SQLite-backed persistence for questions, responses, and scores
- Questions loaded once into the database, then read-only at runtime
- Automatic EQ score calculation with interpretation
- Stores:
  - User credentials (securely hashed)
  - Per-question responses
  - Final EQ score
  - Optional age and age group
- Backward-compatible database schema migrations
- Pytest-based test suite with isolated temporary databases
- Daily emotional journal with AI sentiment analysis
- Emotional pattern tracking and insights
- View past journal entries and emotional journey
---

## 📝 Journal Feature

The journal feature allows users to:

- Write daily emotional reflections
- Get AI-powered sentiment analysis of entries
- Track emotional patterns over time
- View past entries and emotional journey
- Receive insights on stress indicators, growth mindset, and self-reflection

**AI Analysis Capabilities:**

- **Sentiment Scoring:** Analyzes positive/negative emotional tone  
- **Pattern Detection:** Identifies stress indicators, relationship focus, growth mindset, and self-reflection  
- **Emotional Tracking:** Monitors emotional trends over time  


---

## 🛠 Technologies Used

- Python 3.11+
- Tkinter (GUI)
- SQLite3 (Database)
- Pytest (Testing)

---

## 📂 Project Structure (Refactored)

```bash

SOUL_SENSE_EXAM/
│
├── app/                     # Core application package
│   ├── __init__.py
│   ├── main.py              # Tkinter application entry point
│   ├── db.py                # Database connection utilities
│   ├── models.py            # Schema & migrations
│   ├── questions.py         # Question loading from DB
│   └── utils.py             # Shared helpers (e.g., age grouping)
│
├── scripts/                 # One-time / maintenance scripts
│   ├── __init__.py
│   └── load_questions.py    # Loads questions.txt into the DB (run once)
│
├── data/
│   └── questions.txt        # Source question bank (seed data)
│
├── db/
│   └── soulsense.db         # SQLite database (generated at runtime)
│
├── tests/                   # Pytest test suite
│   ├── test_db.py
│   ├── test_models.py
│   ├── test_questions.py
│   └── test_utils.py
│
├── logs/
│   └── soulsense.log        # Application logs
│
├── pytest.ini               # Pytest configuration
└── README.md
```
---

## 🧩 Question Format

Each question is rated on a 4-point Likert scale:

- Never (1)
- Sometimes (2)
- Often (3)
- Always (4)

### Sample Questions

- You can recognize your emotions as they happen.
- You adapt well to changing situations.
- You actively listen to others when they speak.

---

## 🐍 Setting Up a Virtual Environment & Installing Packages

It’s recommended to use a **virtual environment** to keep your project dependencies isolated from your system Python.

1️⃣ Create a Virtual Environment  
From your project root directory: 
```bash
python -m venv venv  
```
This will create a `venv/` folder inside your project.

2️⃣ Activate the Virtual Environment  

Windows: 
```bash 
venv\Scripts\activate  
```
macOS/Linux:  
```bash
source venv/bin/activate  
```
When active, your terminal prompt will show `(venv)`.

3️⃣ Install Required Packages  

Once activated, install your project dependencies:  
```bash
pip install pandas numpy pytest  
```


<!--4️⃣ Save Dependencies (Optional but Recommended)  

Freeze installed packages to a `requirements.txt` file:  
pip freeze > requirements.txt  

Later, to replicate the environment on another machine:  
pip install -r requirements.txt -->


> Always **activate the virtual environment** before running scripts or installing new packages.  

✅ Tip: If you see `ModuleNotFoundError`, it usually means your virtual environment is **not active** or the package isn’t installed inside it.


---

## ▶️ How to Run

Load questions into the database (one-time step):

```bash
    python -m scripts.load_questions
```
Start the application:

```bash
    python -m app.main
```

### First Time Setup
1. When you first run the application, you'll see a login screen
2. Click "Sign Up" to create a new account with username and password
3. After creating an account, login with your credentials
4. You can now take the EQ test with personalized data tracking
5. Use the "Logout" button to switch users or end your session
---

## 🧪 Running Tests

From the project root:

```bash
    python -m pytest -v
```
Tests use temporary SQLite databases and do not affect production data.

---

## 🧱 Design Notes

- Database schemas are created and migrated safely at runtime
- Question loading is idempotent and separated from application logic
- Core logic is decoupled from the GUI to enable testing
- Refactor preserves original application behavior while improving structure

---

## 📌 Status

- Refactor complete
- Tests added
- Stable baseline for further enhancements (e.g., decorators, generators)

## 🤝 Contributing

We welcome contributions from the community.  
Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing to help maintain a respectful and inclusive environment.

