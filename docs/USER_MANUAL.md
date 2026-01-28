# Soul Sense EQ Test - User Manual

## Welcome to Soul Sense

Soul Sense is a comprehensive Emotional Intelligence (EQ) assessment application designed to help you understand and improve your emotional wellbeing. This desktop app combines traditional psychometric testing with modern AI-powered insights, daily journaling, and personalized emotional guidance.

### What You'll Learn in This Manual
- How to get started with registration and setup
- Taking your first EQ assessment
- Using the daily journaling feature
- Viewing and understanding your results
- Managing your profile and personal information
- Exporting your data
- Troubleshooting common issues
- Handling special scenarios like retaking tests

---

## Getting Started

### System Requirements
- **Operating System**: Windows 10/11, macOS 10.14+, or Linux
- **Python**: Version 3.11 or higher (automatically handled by installer)
- **Storage**: At least 500MB free disk space
- **Internet**: Not required for core features (optional for updates)

### Installation
1. Download the Soul Sense installer from the official website
2. Run the installer and follow the on-screen instructions
3. The app will automatically set up the database and question bank
4. Launch Soul Sense from your desktop or start menu

### First-Time Setup
When you first open Soul Sense, you'll see a login screen.

#### Creating Your Account
1. Click the **"Create Account"** button
2. Enter a username (letters and numbers only, no spaces)
3. Choose a strong password (at least 8 characters)
4. Click **"Create Account"**
5. You'll see a success message - you can now login

#### Logging In
1. Enter your username in the first field
2. Enter your password in the second field
3. Click **"Login"**
4. The main application will open

> **Tip**: Your data is stored locally on your computer. No information is sent to external servers unless you explicitly enable cloud features.

---

## Taking Your First Assessment

### Understanding EQ Assessments
Soul Sense measures your Emotional Intelligence across five key areas:
- **Self-Awareness**: Understanding your own emotions
- **Emotional Regulation**: Managing your emotional responses
- **Empathy**: Understanding others' feelings
- **Social Skills**: Building and maintaining relationships
- **Motivation**: Using emotions to achieve goals

### Starting an Assessment
1. From the main dashboard, click the **"Assessment"** card or use the sidebar menu
2. Choose your preferred assessment length:
   - **Short (5 questions)**: Quick check-in
   - **Medium (10 questions)**: Standard assessment
   - **Long (20 questions)**: Comprehensive evaluation
3. Click **"Start Assessment"**

### During the Assessment
1. Read each question carefully
2. Use the slider to rate how much you agree with each statement:
   - 1 = Strongly Disagree
   - 3 = Neutral
   - 5 = Strongly Agree
3. Click **"Next"** to move to the next question
4. Your progress is shown at the top of the screen

### After Completing Assessment
- Your results will be calculated automatically
- You'll see your EQ scores across all five categories
- AI-powered insights will highlight your strengths and areas for growth
- Results are saved to your profile for future reference

---

## Daily Journaling

### Why Journal?
Journaling helps you:
- Track emotional patterns over time
- Process difficult experiences
- Celebrate positive moments
- Receive AI-powered insights about your wellbeing

### Writing Your First Entry
1. Click **"Journal"** from the sidebar or main dashboard
2. Fill in your daily metrics using the sliders:
   - **Sleep Hours**: How many hours you slept
   - **Sleep Quality**: Rate your sleep (1-10)
   - **Energy Level**: Your current energy (1-10)
   - **Work Hours**: Hours spent working
   - **Stress Level**: Current stress (1-10)
   - **Screen Time**: Minutes spent on screens

3. Add context about your day:
   - **Daily Schedule**: Key events or activities
   - **Stress Triggers**: What caused stress today?

4. Write your thoughts in the main text area
5. Add tags (comma-separated) like: work, family, stress, gratitude
6. Click **"Save Entry"**

### AI Analysis
After saving, Soul Sense will:
- Analyze the sentiment of your writing
- Identify emotional patterns
- Provide personalized health insights
- Suggest areas for attention

### Viewing Past Entries
1. Click **"View Past Entries"** in the journal
2. Use filters to find specific entries:
   - **Tags**: Search by keywords
   - **Date Range**: Entries from specific dates
   - **Mood**: Positive, neutral, or negative entries
   - **Month**: Entries from specific months
   - **Type**: High stress days, great days, or poor sleep nights

### Mood Trends
1. Click **"Mood Trends"** in the journal
2. View charts showing:
   - Sentiment scores over time
   - Stress level patterns
   - Energy level trends
   - Sleep hour tracking

---

## Viewing Your Results

### Assessment Results
1. Go to **"History"** in the sidebar
2. View a timeline of all your completed assessments
3. Click on any assessment to see detailed results:
   - Overall EQ score
   - Category breakdowns
   - AI insights and recommendations
   - Date completed

### Dashboard Analytics
1. Click **"Dashboard"** from the sidebar
2. View comprehensive analytics:
   - EQ score trends over time
   - Average scores across categories
   - Progress indicators
   - Benchmarking against general population

### Understanding Your Scores
- **Scores range from 0-100**
- **Above 70**: Strong emotional intelligence
- **50-70**: Average emotional intelligence
- **Below 50**: Area for development

---

## Managing Your Profile

### Accessing Profile Settings
1. Click **"Profile"** from the sidebar
2. Navigate using the left sidebar:
   - **Overview**: Quick summary of your information
   - **Medical**: Health and medical details
   - **History**: Personal background and life events
   - **Strengths**: Your strengths and goals
   - **Settings**: App preferences

### Updating Personal Information
#### Basic Information
1. Go to **Profile → History**
2. Update fields like:
   - Occupation
   - Education level
   - Marital status
   - Bio/description

#### Contact Information
1. In the History section, find the Contact Information area
2. Update:
   - Email address
   - Phone number
   - Physical address
   - Date of birth
   - Gender

#### Medical Information
1. Go to **Profile → Medical**
2. Add or update:
   - Blood type
   - Allergies
   - Current medications
   - Medical conditions
   - Emergency contact information

### Life Events Timeline
1. In **Profile → History**, scroll to the timeline section
2. Click **"Add Event"** to record important life events
3. Include:
   - Date of the event
   - Title/summary
   - Detailed description

### Strengths and Preferences
1. Go to **Profile → Strengths**
2. Define your:
   - Top personal strengths
   - Areas for improvement
   - Current challenges
   - Learning style preferences
   - Communication preferences

---

## Data Export and Backup

### Exporting Your Data
1. Go to **Profile → Data Export**
2. Click **"Export as JSON"**
3. Choose where to save the file
4. Your complete data will be saved including:
   - All assessment results
   - Journal entries
   - Profile information
   - Medical details

### Understanding Exported Data
The JSON file contains all your information in a structured format that can be:
- Imported into other applications
- Shared with healthcare providers (with your permission)
- Used for personal record-keeping
- Restored if you reinstall the app

### Data Backup
1. Go to **Profile → Settings**
2. Find the **"Data Backup"** section
3. Click **"Manage Backups"**
4. Create local backups of your data
5. Restore from previous backups if needed

---

## Troubleshooting

### Common Issues

#### Can't Login
- **Problem**: Forgot username or password
- **Solution**: Try different username variations. If you can't remember, contact support with your registration email

#### App Won't Start
- **Problem**: Application fails to launch
- **Solution**:
  1. Ensure Python 3.11+ is installed
  2. Check that all required files are present
  3. Try running as administrator (Windows) or with sudo (Linux/Mac)
  4. Check the logs in the `logs/` folder for error details

#### Assessment Questions Don't Load
- **Problem**: Questions fail to appear during assessment
- **Solution**:
  1. Restart the application
  2. Check internet connection (questions are stored locally but may need initial download)
  3. Verify the question database is intact

#### Journal Entries Not Saving
- **Problem**: Journal content disappears after saving
- **Solution**:
  1. Ensure you clicked "Save Entry"
  2. Check available disk space
  3. Restart the app and try again
  4. Check the database file isn't corrupted

#### Charts Not Displaying
- **Problem**: Mood trend charts don't show
- **Solution**: Install matplotlib using: `pip install matplotlib`

### Performance Issues
- **Slow Loading**: Close other applications to free up memory
- **Large Database**: Export old data and create a fresh installation
- **High CPU Usage**: This is normal during AI analysis of journal entries

---

## Common Scenarios

### Retaking Assessments
1. Go to **"Deep Dive"** in the sidebar
2. Choose an assessment type (Career Clarity, Work Satisfaction, etc.)
3. Select your preferred length
4. Complete the assessment
5. Compare results with previous assessments in your History

### Tracking Progress Over Time
1. Use the **Dashboard** to see trends
2. Review **History** for assessment comparisons
3. Check **Mood Trends** in the Journal for emotional patterns
4. Export data periodically to track long-term progress

### Managing High Stress Periods
1. Increase journaling frequency during stressful times
2. Use the stress level slider to track daily stress
3. Review AI insights for coping suggestions
4. Consider professional support if stress persists

### Preparing for Important Events
1. Take a practice assessment before big events
2. Journal about your feelings and expectations
3. Use the "Daily Schedule" field to plan your day
4. Review past successful experiences in your timeline

### Sharing Results with Others
1. Export your data as JSON
2. Share only the information you're comfortable with
3. Consider printing key insights from the Dashboard
4. Discuss results with trusted friends, family, or professionals

---

## Privacy and Security

### Your Data is Local
- All information stays on your computer
- No data is sent to external servers without your permission
- You control all backups and exports

### Data Retention
- Assessment results are kept indefinitely
- Journal entries are stored until you delete them
- You can delete your entire account and all data at any time

### Best Practices
- Use a strong, unique password
- Keep your Soul Sense installation updated
- Regularly backup important data
- Be mindful of what you write in journals (they're private but stored locally)

---

## Getting Help

### Built-in Help
- Check the **FAQ** in the application menu
- Review this manual for detailed instructions
- Use the **Settings** page for configuration help

### Community Support
- Visit the official Soul Sense community forums
- Check the GitHub repository for updates and known issues
- Contact the development team through official channels

### Professional Support
Remember: Soul Sense is a self-assessment tool, not a substitute for professional mental health care. If you're experiencing significant emotional distress, please consult qualified mental health professionals.

---

## Appendix: Keyboard Shortcuts

- **Enter**: Submit forms and move to next question
- **Tab**: Navigate between form fields
- **Ctrl+S**: Save current work (where applicable)
- **Ctrl+N**: Start new assessment
- **F1**: Open help (future feature)

---

*Built with ❤️ for emotional intelligence and personal growth*

*Last updated: [Current Date]*
*Version: 1.0*
