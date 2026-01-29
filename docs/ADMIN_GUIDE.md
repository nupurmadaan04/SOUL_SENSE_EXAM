# Admin Interface Guide

## Overview

The SoulSense Admin Interface provides authorized users with tools to manage questions in the database through both GUI and CLI interfaces.

## Features

- **GUI Admin Panel** - User-friendly graphical interface
- **CLI Tool** - Command-line interface for automation
- **Secure Access** - Password-protected admin accounts
- **CRUD Operations** - Create, Read, Update, Delete questions
- **Category Management** - Organize questions by category
- **Metadata Support** - Age range, difficulty, weight customization

---

## Getting Started

### 1. Create an Admin Account

**Option A: Using GUI**
```bash
python admin_interface.py
```
Click "Create Admin" button and fill in the form.

**Option B: Using CLI**
```bash
python admin_cli.py create-admin --no-auth
```

### 2. Login

Use the credentials you created to access the admin panel.

---

## GUI Interface

### Starting the GUI

```bash
python admin_interface.py
```

### Features

#### 📋 View Questions Tab
- Browse all questions in a table view
- Filter by category
- Show/hide inactive questions
- See question details at a glance

#### ➕ Add Question Tab
- Add new questions to the database
- Set category, age range, difficulty, weight
- Support for creating new categories

#### ✏️ Edit Question Tab
- Load existing questions by ID
- Modify question text and metadata
- Delete questions (soft delete)

#### 🏷️ Categories Tab
- View category statistics
- See question count per category
- Monitor category distribution

---

## CLI Interface

### Basic Commands

#### List All Questions
```bash
python admin_cli.py list
```

#### List Questions by Category
```bash
python admin_cli.py list --category "Self-Awareness"
```

#### Include Inactive Questions
```bash
python admin_cli.py list --inactive
```

#### View Specific Question
```bash
python admin_cli.py view --id 1
```

#### Add New Question
```bash
python admin_cli.py add
```
Follow the interactive prompts to enter question details.

#### Update Question
```bash
python admin_cli.py update --id 1
```
Enter new values or press Enter to keep current values.

#### Delete Question
```bash
python admin_cli.py delete --id 1
```
Confirm the deletion when prompted.

#### View Category Statistics
```bash
python admin_cli.py categories
```

#### Create New Admin User
```bash
python admin_cli.py create-admin
```

---

## Database Schema

### Questions Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| text | TEXT | Question text (required) |
| category | TEXT | Category name (default: "General") |
| age_min | INTEGER | Minimum age (default: 12) |
| age_max | INTEGER | Maximum age (default: 100) |
| difficulty | INTEGER | Difficulty level 1-5 (default: 3) |
| weight | REAL | Question weight for scoring (default: 1.0) |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Last update timestamp |
| is_active | INTEGER | Active status (1=active, 0=inactive) |

### Admin Users Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| username | TEXT | Admin username (unique) |
| password_hash | TEXT | SHA-256 hashed password |
| role | TEXT | User role (default: "admin") |
| created_at | TEXT | Account creation timestamp |

---

## Best Practices

### Question Writing Guidelines

1. **Be Clear and Specific**
   - Use simple, direct language
   - Avoid ambiguous terms
   - One concept per question

2. **Age-Appropriate**
   - Set appropriate age_min and age_max
   - Use vocabulary suitable for the target age range

3. **Consistent Format**
   - Use statements rather than questions
   - Keep consistent tone across questions
   - Use similar sentence structures

4. **Category Organization**
   - Use consistent category names
   - Create logical groupings
   - Consider using these standard categories:
     - Self-Awareness
     - Self-Management
     - Social Awareness
     - Relationship Management
     - General

### Difficulty Levels

- **1** - Very Easy (basic self-awareness)
- **2** - Easy (simple emotional recognition)
- **3** - Medium (standard EQ assessment)
- **4** - Hard (complex emotional situations)
- **5** - Very Hard (advanced emotional intelligence)

### Weight Guidelines

- **0.5** - Low importance questions
- **1.0** - Standard weight (default)
- **1.5-2.0** - Important questions
- **2.5+** - Critical core questions

---

## Security

### Password Requirements

- Minimum 4 characters
- SHA-256 encryption
- Unique usernames

### Access Control

- All operations require authentication
- Admin credentials stored securely
- No default admin account (must be created)

### Best Security Practices

1. Use strong passwords
2. Limit admin access to trusted users
3. Regularly review question changes
4. Backup database before bulk operations

---

## Configuration Options

This section documents all configuration options available in SoulSense, including environment variables, config.json settings, and security parameters.

### Environment Variables

Environment variables are prefixed with `SOULSENSE_` and take precedence over config.json settings.

#### Application Environment
- **`SOULSENSE_ENV`** (default: "development")
  - Environment mode: "development", "staging", "production"
  - Affects logging verbosity and error handling

- **`SOULSENSE_DEBUG`** (default: false)
  - Enable debug mode with detailed logging
  - Shows stack traces and additional debug information

- **`SOULSENSE_LOG_LEVEL`** (default: "INFO")
  - Logging level: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
  - Controls what messages are written to logs

#### Database Configuration
- **`SOULSENSE_DB_PATH`** (optional)
  - Absolute or relative path to database file
  - Overrides config.json database settings
  - If relative, resolved from project root

- **`SOULSENSE_DATABASE_TYPE`** (default: "sqlite")
  - Database type: "sqlite" or "postgresql"
  - SQLite for single-user, PostgreSQL for multi-user/production

- **`SOULSENSE_DB_HOST`** (default: "localhost")
  - PostgreSQL server hostname
  - Only used when DATABASE_TYPE is "postgresql"

- **`SOULSENSE_DB_PORT`** (default: 5432)
  - PostgreSQL server port
  - Only used when DATABASE_TYPE is "postgresql"

- **`SOULSENSE_DB_NAME`** (default: "soulsense")
  - PostgreSQL database name
  - Only used when DATABASE_TYPE is "postgresql"

- **`SOULSENSE_DB_USER`** (default: "postgres")
  - PostgreSQL username
  - Only used when DATABASE_TYPE is "postgresql"

- **`SOULSENSE_DB_PASSWORD`** (default: "password")
  - PostgreSQL password
  - Only used when DATABASE_TYPE is "postgresql"

#### Feature Toggles
- **`SOULSENSE_ENABLE_JOURNAL`** (default: true)
  - Enable/disable journaling feature
  - When disabled, journal UI elements are hidden

- **`SOULSENSE_ENABLE_ANALYTICS`** (default: true)
  - Enable/disable analytics and reporting features
  - When disabled, analytics UI and data collection are disabled

### config.json Settings

The `config.json` file contains application settings that can be modified without code changes.

#### Database Section
```json
{
  "database": {
    "filename": "soulsense.db",
    "path": "db"
  }
}
```

- **`database.filename`** (default: "soulsense.db")
  - SQLite database filename
  - Only used when DATABASE_TYPE is "sqlite"

- **`database.path`** (default: "db")
  - Database directory relative to project root
  - Set to "data" to store in data/ directory
  - Only used when DATABASE_TYPE is "sqlite"

#### UI Section
```json
{
  "ui": {
    "theme": "light",
    "window_size": "800x600"
  }
}
```

- **`ui.theme`** (default: "light")
  - Application theme: "light" or "dark"
  - Affects color scheme and visual appearance

- **`ui.window_size`** (default: "800x600")
  - Default window dimensions as "WIDTHxHEIGHT"
  - Examples: "1024x768", "1280x720"

#### Features Section
```json
{
  "features": {
    "enable_journal": true,
    "enable_analytics": true
  }
}
```

- **`features.enable_journal`** (default: true)
  - Enable journaling functionality
  - Can be overridden by SOULSENSE_ENABLE_JOURNAL

- **`features.enable_analytics`** (default: true)
  - Enable analytics and reporting
  - Can be overridden by SOULSENSE_ENABLE_ANALYTICS

#### Exam Section
```json
{
  "exam": {
    "num_questions": 5
  }
}
```

- **`exam.num_questions`** (default: 5)
  - Number of questions in each assessment
  - Affects assessment length and scoring

#### Experimental Section
```json
{
  "experimental": {
    "ai_journal_suggestions": false,
    "advanced_analytics": false,
    "beta_ui_components": false,
    "ml_emotion_detection": false,
    "data_export_v2": false
  }
}
```

- **`experimental.ai_journal_suggestions`** (default: false)
  - Enable AI-powered journal entry suggestions
  - Experimental feature, may be unstable

- **`experimental.advanced_analytics`** (default: false)
  - Enable advanced analytics features
  - Includes additional charts and statistical analysis

- **`experimental.beta_ui_components`** (default: false)
  - Enable beta UI components and layouts
  - May include unfinished or experimental interfaces

- **`experimental.ml_emotion_detection`** (default: false)
  - Enable machine learning emotion detection
  - Requires ML models and may impact performance

- **`experimental.data_export_v2`** (default: false)
  - Enable enhanced data export features
  - Includes additional export formats and options

### Security Configuration

Security settings are defined in `app/security_config.py` and affect password policies, session management, and input validation.

#### Password Security
- **`MIN_PASSWORD_LENGTH`** (default: 8)
  - Minimum characters required for passwords
  - Affects account creation and password changes

- **`MAX_PASSWORD_LENGTH`** (default: 128)
  - Maximum characters allowed for passwords
  - Prevents extremely long password attacks

- **`PASSWORD_HASH_ROUNDS`** (default: 12)
  - PBKDF2 hash rounds for password security
  - Higher values increase security but slow authentication

#### Session Security
- **`SESSION_TIMEOUT_HOURS`** (default: 24)
  - Hours before automatic logout
  - Balances security with user convenience

- **`MAX_LOGIN_ATTEMPTS`** (default: 5)
  - Failed login attempts before account lockout
  - Prevents brute force attacks

- **`LOCKOUT_DURATION_MINUTES`** (default: 5)
  - Minutes account remains locked after failed attempts
  - Temporary measure to prevent continued attacks

#### Database Security
- **`DB_CONNECTION_TIMEOUT`** (default: 20)
  - Seconds to wait for database connections
  - Prevents hanging on database issues

- **`DB_POOL_SIZE`** (default: 5)
  - Maximum concurrent database connections
  - Affects performance and resource usage

#### Input Validation
- **`MAX_INPUT_LENGTH`** (default: 1000)
  - Maximum characters allowed in text inputs
  - Prevents buffer overflow and spam

- **`ALLOWED_FILE_EXTENSIONS`** (default: ['.jpg', '.jpeg', '.png', '.gif'])
  - Permitted file types for uploads
  - Security measure against malicious file uploads

- **`MAX_FILE_SIZE_MB`** (default: 5)
  - Maximum file size in megabytes
  - Prevents large file upload attacks

#### Rate Limiting
- **`MAX_REQUESTS_PER_MINUTE`** (default: 60)
  - Maximum API requests per minute per user
  - Prevents abuse and ensures fair resource usage

### Configuration Management

#### Setting Environment Variables

**Linux/macOS:**
```bash
export SOULSENSE_DEBUG=true
export SOULSENSE_LOG_LEVEL=DEBUG
python app.py
```

**Windows:**
```cmd
set SOULSENSE_DEBUG=true
set SOULSENSE_LOG_LEVEL=DEBUG
python app.py
```

**Using .env file:**
```bash
# Create .env file in project root
SOULSENSE_DEBUG=true
SOULSENSE_LOG_LEVEL=DEBUG
SOULSENSE_DATABASE_TYPE=postgresql
SOULSENSE_DB_HOST=localhost
```

#### Modifying config.json

1. Open `config.json` in a text editor
2. Modify desired settings
3. Save the file
4. Restart the application

**Example config.json:**
```json
{
    "database": {
        "filename": "soulsense.db",
        "path": "data"
    },
    "ui": {
        "theme": "dark",
        "window_size": "1024x768"
    },
    "features": {
        "enable_journal": true,
        "enable_analytics": true
    },
    "exam": {
        "num_questions": 10
    },
    "experimental": {
        "ai_journal_suggestions": false,
        "advanced_analytics": true,
        "beta_ui_components": false,
        "ml_emotion_detection": false,
        "data_export_v2": false
    }
}
```

#### Configuration Priority

Settings are applied in this order (highest priority first):
1. Environment variables (SOULSENSE_*)
2. config.json file
3. Default values in code

#### Validation and Error Handling

- Invalid config.json files will cause startup failure with error messages
- Missing config.json falls back to defaults with warning
- Environment variables are validated for correct types
- Security settings cannot be modified at runtime

---

## Troubleshooting

### Common Issues

**Issue: "Invalid credentials"**
- Solution: Verify username and password are correct
- Create new admin account if needed

**Issue: Cannot delete question**
- Solution: Questions are soft-deleted (is_active=0), not permanently removed
- Use database tools for permanent deletion if needed

**Issue: Changes not reflecting in app**
- Solution: Restart the application to reload questions
- Check question is_active status

**Issue: CLI import error**
- Solution: Install required package: `pip install tabulate`

---

## API Reference

### QuestionDatabase Class

#### Methods

**`add_question(text, category, age_min, age_max, difficulty, weight)`**
- Add a new question to the database
- Returns: question_id

**`update_question(question_id, text, category, age_min, age_max, difficulty, weight)`**
- Update an existing question
- Returns: Boolean (success/failure)

**`delete_question(question_id)`**
- Soft delete a question (sets is_active=0)
- Returns: Boolean (success/failure)

**`get_all_questions(include_inactive=False)`**
- Retrieve all questions
- Returns: List of question dictionaries

**`get_question_by_id(question_id)`**
- Get a specific question
- Returns: Question dictionary or None

**`get_categories()`**
- Get all unique categories
- Returns: List of category names

**`verify_admin(username, password)`**
- Verify admin credentials
- Returns: Boolean

**`create_admin(username, password)`**
- Create new admin account
- Returns: Boolean

---

## Examples

### Example 1: Bulk Add Questions

```python
from admin_interface import QuestionDatabase

db = QuestionDatabase()

questions = [
    ("You can recognize your emotions as they happen.", "Self-Awareness", 12, 25, 2, 1.0),
    ("You understand why you feel a certain way.", "Self-Awareness", 14, 30, 3, 1.0),
    ("You can control your emotions in stressful situations.", "Self-Management", 15, 35, 4, 1.5),
]

for q in questions:
    db.add_question(*q)
    print(f"Added: {q[0][:50]}...")
```

### Example 2: Export Questions

```python
from admin_interface import QuestionDatabase
import json

db = QuestionDatabase()
questions = db.get_all_questions()

with open('questions_backup.json', 'w') as f:
    json.dump(questions, f, indent=2)

print(f"Exported {len(questions)} questions")
```

### Example 3: Update Multiple Questions

```python
from admin_interface import QuestionDatabase

db = QuestionDatabase()
questions = db.get_all_questions()

# Update all questions in a category
for q in questions:
    if q['category'] == 'General':
        db.update_question(q['id'], category='Self-Awareness')

print("Updated category for all General questions")
```

---

## Support

For issues or questions:
1. Check this documentation
2. Review the code comments
3. Submit an issue on GitHub
4. Contact the development team

---

## Future Enhancements

Planned features:
- [ ] Bulk import from CSV/JSON
- [ ] Question versioning
- [ ] Usage analytics
- [ ] Multi-language support for admin panel
- [ ] Role-based permissions
- [ ] Audit logging
- [ ] Question templates
- [ ] Automated backups

---

**Happy Question Managing! 📝**
