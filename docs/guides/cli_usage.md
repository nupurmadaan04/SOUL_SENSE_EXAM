# SoulSense CLI Usage Guide

## Overview

The SoulSense CLI (Command Line Interface) provides a comprehensive terminal-based interface for taking emotional intelligence assessments, viewing progress, and managing your emotional wellness data. This guide covers installation, usage, and all available features.

## Installation

### Prerequisites

- **Python 3.8+** installed on your system
- **SQLite** (default) or **PostgreSQL** (optional)
- **NLTK** for sentiment analysis (automatically downloaded)

### Installation Steps

1. **Clone or download the SoulSense project**
   ```bash
   git clone <repository-url>
   cd soul-sense-exam
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Optional: Install PostgreSQL dependencies**
   ```bash
   pip install psycopg2-binary
   ```

4. **Run the CLI**
   ```bash
   python -m app.cli
   ```

### Command Line Options

The CLI supports the following command-line flags:

- **`--help`**: Display help information
- **`--version`** or **`-v`**: Display version information

```bash
# Show help
python -m app.cli --help

# Show version
python -m app.cli --version
python -m app.cli -v
```

## Getting Started

### First Run

When you first run the CLI, you'll be prompted to enter:

1. **Your name**: Used to identify your exam sessions
2. **Your age**: Determines age-appropriate questions (13-99 years)

```bash
$ python -m app.cli

      S O U L   S E N S E   ( C L I   V E R S I O N )
      ==================================================
      Emotional Intelligence Assessment
      ==================================================

Enter your name: John Doe
Enter your age (13-99): 28

Welcome, John Doe (Adult).
Loading assessment...
```

### Main Menu

After authentication, you'll see the main menu with 8 options:

```
  1. 📝 Start New Exam
  2. 📋 View History
  3. 📊 View Statistics
  4. 📈 Dashboard
  5. 💾 Export Results
  6. ⚙️  Settings
  7. ℹ️  Version
  8. 🚪 Exit
```

## Taking an Exam

### Starting an Exam

Select option **1** from the main menu to begin a new assessment.

### Question Format

Each question uses a 4-point Likert scale:

- **1. Never**
- **2. Sometimes**
- **3. Often**
- **4. Always**

### Navigation

During the exam, you can:

- **Enter 1-4**: Answer the current question
- **Enter 'b'**: Go back to the previous question
- **Enter 'q'**: Quit the exam (with confirmation)

### Reflection Phase

After answering all questions, you'll be prompted to reflect:

```
Describe a recent situation where you felt emotionally challenged.
How did you handle it?

>
```

### Results Display

After reflection, you'll see:

- **Score**: Your total score out of maximum possible
- **Percentage**: Performance percentage with color coding
- **Sentiment Analysis**: Analysis of your reflection text
- **Progress Bar**: Visual representation of your score
- **Comparisons**: How you compare to your age group and previous attempts
- **Warnings**: Notes about rushed or inconsistent responses

## Viewing History

Select option **2** to view your exam history.

### Features

- **Score Trend Graph**: ASCII visualization of your progress over time
- **Detailed Table**: Shows date, score, sentiment, and status flags
- **Color Coding**: Green (good), Yellow (average), Red (needs improvement)
- **Status Indicators**:
  - ⚡: Rushed exam (completed too quickly)
  - ⚠️: Inconsistent responses
  - ✓: Normal completion

## Viewing Statistics

Select option **3** to see comprehensive statistics.

### Statistics Displayed

- **Overview**:
  - Total exams taken
  - Consistency rate (percentage of non-rushed exams)

- **Scores**:
  - Average score with percentage
  - Best and worst scores
  - Color-coded performance indicators

- **Trend Analysis**:
  - First vs. last score comparison
  - Improvement tracking

- **Sentiment Analysis**:
  - Average sentiment score
  - Positive/Neutral/Negative classification

## Dashboard

Select option **4** to access advanced analytics.

### Dashboard Options

```
  1. 📈 EQ Score Trends
  2. ⏱️  Time-Based Analysis
  3. 🧠 Emotional Profile
  4. 💡 AI Insights
  5. ← Back to Menu
```

#### EQ Score Trends

- Visual timeline of your scores over time
- Color-coded bars showing performance levels
- Historical score progression

#### Time-Based Analysis

- Performance analysis by hour of day
- Identifies your best and worst testing times
- Personalized recommendations for optimal exam timing

#### Emotional Profile

- Comprehensive emotional intelligence profile
- Based on your average scores and sentiment
- Personalized descriptions and development suggestions

#### AI Insights

- Machine learning-powered analysis of your data
- Personalized recommendations and insights
- Performance trend analysis
- Behavioral pattern recognition

## Exporting Results

Select option **5** to export your exam data.

### Export Formats

1. **JSON Export**: Structured data format
2. **CSV Export**: Spreadsheet-compatible format

### Export Process

1. Choose export format (JSON or CSV)
2. Specify export directory (or use default `exports/` folder)
3. Files are automatically named with timestamp and username

### JSON Export Structure

```json
{
  "username": "John Doe",
  "exported_at": "2026-01-28T10:30:00",
  "total_exams": 5,
  "results": [
    {
      "timestamp": "2026-01-28T10:25:00",
      "score": 32,
      "sentiment": 45.2,
      "reflection": "I handled the situation by...",
      "is_rushed": false,
      "is_inconsistent": false
    }
  ]
}
```

### CSV Export Format

```csv
timestamp,score,sentiment,reflection,is_rushed,is_inconsistent
"2026-01-28T10:25:00",32,45.2,"I handled the situation by...",0,0
```

## Settings

Select option **6** to modify application settings.

### Available Settings

- **Number of Questions**: Configure how many questions per exam (1-20)
  - Default: 10 questions
  - Shared with GUI application
  - Persisted across sessions

### Changing Settings

1. Select "Change number of questions"
2. Enter new value (1-20) or 'b' to cancel
3. Setting is saved and applied immediately

## Version Information

Select option **7** to view version details.

### Information Displayed

- Application name and version
- Build date
- Python version
- System information

## Configuration

The CLI uses the same configuration system as the GUI application.

### Environment Variables

- **`SOULSENSE_ENV`**: Environment mode (development/staging/production)
- **`SOULSENSE_DEBUG`**: Enable debug logging
- **`SOULSENSE_LOG_LEVEL`**: Set logging level
- **`SOULSENSE_DB_PATH`**: Database file location
- **`SOULSENSE_DATABASE_TYPE`**: Database type (sqlite/postgresql)
- **`SOULSENSE_DB_HOST`**: PostgreSQL host
- **`SOULSENSE_DB_PORT`**: PostgreSQL port
- **`SOULSENSE_DB_NAME`**: PostgreSQL database name
- **`SOULSENSE_DB_USER`**: PostgreSQL username
- **`SOULSENSE_DB_PASSWORD`**: PostgreSQL password

### config.json Settings

See the main admin guide for complete configuration options.

## Troubleshooting

### Common Issues

#### Database Connection Errors

**Problem**: "Could not sync with DB" message
**Solution**:
- Ensure database file exists and is writable
- Check database configuration in config.json
- For PostgreSQL, verify connection parameters

#### NLTK Download Errors

**Problem**: Sentiment analysis unavailable
**Solution**:
- Ensure internet connection for initial NLTK download
- The application will work without sentiment analysis

#### Color Display Issues

**Problem**: Colors not displaying properly
**Solution**:
- Colors are automatically disabled on unsupported terminals
- Use `--help` to verify CLI is working

#### Export Permission Errors

**Problem**: Cannot export to specified directory
**Solution**:
- Check write permissions on target directory
- Use default exports directory if custom path fails

### Performance Tips

- **Database**: SQLite performs better for single-user scenarios
- **Memory**: Close other applications during exams for best performance
- **Storage**: Regular exports help manage database size

## Advanced Usage

### Batch Processing

The CLI is designed for interactive use but can be scripted:

```bash
# Non-interactive version (requires code modification)
echo "John Doe" | python -m app.cli
```

### Custom Configuration

Create a custom config.json for specific environments:

```json
{
  "database": {
    "filename": "custom.db",
    "path": "data"
  },
  "ui": {
    "theme": "dark"
  },
  "exam": {
    "num_questions": 15
  }
}
```

### Database Management

- **Backup**: Regular exports serve as backups
- **Migration**: Use GUI for complex database operations
- **Cleanup**: Old exam data can be archived via exports

## Support and Resources

- **Documentation**: See docs/ADMIN_GUIDE.md for configuration details
- **Issues**: Report bugs via GitHub issues
- **Contributing**: See docs/CONTRIBUTING.md for development guidelines

## Version History

- **v1.0.0**: Initial CLI release with basic exam functionality
- **v1.1.0**: Added dashboard and advanced analytics
- **v1.2.0**: Enhanced export features and configuration options
- **v1.3.0**: Improved sentiment analysis and AI insights

---

*This guide covers SoulSense CLI version 1.0.0. Features may vary in different versions.*