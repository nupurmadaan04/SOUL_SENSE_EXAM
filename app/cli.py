
import os
import sys
import logging
import time
import math
from typing import Optional, Dict, Any, Tuple, List

# --- Refactor: Imports moved inside methods or guarded where possible ---
# But we need types for class definition. 
# We assume the environment is set up correctly by the runner (or main block)
# instead of hacking path at module level.

# Simple logging config for CLI 
logging.basicConfig(level=logging.ERROR) 

# Lazy load NLTK inside class or setup method to avoid import time cost/errors
SENTIMENT_AVAILABLE = False
try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    SENTIMENT_AVAILABLE = True
except ImportError:
    pass

from app.services.exam_service import ExamSession
from app.questions import load_questions, get_random_questions_by_age
from app.utils import compute_age_group
# from app.logger import setup_logging # Not used in snippet, but good practice

# ANSI Color Codes
class Colors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    @staticmethod
    def supports_color():
        """Check if terminal supports color output"""
        # Windows terminal detection
        if os.name == 'nt':
            # Enable ANSI on Windows 10+
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                return True
            except Exception:
                return os.environ.get('TERM') is not None
        # Unix-like systems
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

# Global color support flag
COLOR_ENABLED = Colors.supports_color()

def colorize(text: str, color: str) -> str:
    """Apply color to text if supported"""
    if COLOR_ENABLED:
        return f"{color}{text}{Colors.RESET}"
    return text

class SoulSenseCLI:
    def __init__(self, auth_manager: Any = None, session_manager: Any = None) -> None:
        """
        Initialize CLI environment.
        dependency injection supported for testing.
        """
        self.username = ""
        self.age = 0
        self.age_group = ""
        self.session: Optional[ExamSession] = None
        
        # Dependency Injection / Lazy Load
        self._auth_manager = auth_manager
        self._session_manager = session_manager
        
        # Load SHARED settings
        from app.utils import load_settings
        self.settings = load_settings()
        self.num_questions = self.settings.get("question_count", 10)
        
        # Setup Environment
        self._setup_nltk()

    def _setup_nltk(self):
        """Lazy load/download NLTK data"""
        if not SENTIMENT_AVAILABLE:
            return
            
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            try:
                print("Downloading NLTK data (vader_lexicon)...")
                nltk.download('vader_lexicon', quiet=True)
            except Exception as e:
                # Log but continue, sentiment will just be unavailable
                logging.warning(f"Failed to download NLTK data: {e}")

    def clear_screen(self) -> None:
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self) -> None:
        self.clear_screen()
        print("="*60)
        print("      S O U L   S E N S E   ( C L I   V E R S I O N )")
        print("="*60)
        print("Emotional Intelligence Assessment")
        print("="*60 + "\n")

    def get_input(self, prompt: str) -> str:
        try:
            return input(prompt).strip()
        except EOFError:
            return ""

    def authenticate(self) -> None:
        """Get user details with validation and load settings"""
        self.print_header()
        
        from app.validation import validate_required, validate_age, AGE_MIN, AGE_MAX
        
        # Username
        while True:
            name = self.get_input("Enter your name: ")
            valid, msg = validate_required(name, "Name")
            if valid:
                self.username = name
                break
            print(msg)
            
        # Age
        while True:
            age_str = self.get_input(f"Enter your age ({AGE_MIN}-{AGE_MAX}): ")
            valid, msg = validate_age(age_str)
            if valid:
                self.age = int(age_str)
                self.age_group = compute_age_group(self.age)
                break
            print(msg)
            
        print(f"\nWelcome, {self.username} ({self.age_group}).")
        
        # === DB Integration: Implicit Registration & Settings ===
        try:
            from app.db import safe_db_context, get_user_settings
            from app.models import User
            
            user_id = None
            print("Syncing with database...")
            
            with safe_db_context() as session:
                # Check for existing user
                user = session.query(User).filter_by(username=self.username).first()
                
                if not user:
                    print(f"Creating new user profile for '{self.username}'...")
                    # Create new user with valid constraints
                    user = User(
                        username=self.username, 
                        password_hash="implicit_cli_auth" # Placeholder
                    )
                    session.add(user)
                    session.commit()
                    session.refresh(user)
                else:
                    print("User profile found.")
                
                user_id = int(user.id)
            
            # Load User Settings
            if user_id:
                settings = get_user_settings(user_id)
                self.settings.update(settings)
                
                # Apply CLI specific overrides
                self.num_questions = self.settings.get("question_count", 10)
                
                theme = self.settings.get("theme", "light")
                print(f"Loaded settings: {self.num_questions} questions | Theme: {theme}")
                
        except Exception as e:
            print(f"⚠️  {Colors.RED}Offline Mode/Error: Could not sync with DB ({e}){Colors.RESET}")
            print("Using default settings.")
        
        print("\nLoading assessment...\n")
        time.sleep(1)

    def initialize_session(self) -> None:
        """Load questions and start session"""
        try:
            all_questions = load_questions(age=self.age)
            # Use configured number of questions
            num_q = min(self.num_questions, len(all_questions))
            selected_questions = get_random_questions_by_age(all_questions, self.age, num_q)
            
            self.session = ExamSession(self.username, self.age, self.age_group, selected_questions)
            self.session.start_exam()
        except Exception as e:
            print(f"Error loading exam: {e}")
            sys.exit(1)

    def print_progress(self, current: int, total: int, pct: float) -> None:
        """ASCII Progress Bar"""
        bar_len = 30
        filled_len = int(bar_len * pct / 100)
        bar = '█' * filled_len + '-' * (bar_len - filled_len)
        print(f"\nProgress: [{bar}] {int(pct)}% ({current}/{total})")

    def run_exam_loop(self) -> None:
        """Main Exam Loop"""
        if not self.session:
            return

        while not self.session.is_finished():
            self.clear_screen()
            
            current, total, pct = self.session.get_progress()
            q_text, q_tooltip = self.session.get_current_question()
            
            # Header
            print(f"Question {current} of {total}")
            self.print_progress(current-1, total, pct) # Show progress completed so far
            print("-" * 60)
            
            # Question
            print(f"\n{q_text}\n")
            if q_tooltip:
                print(f"[TIP: {q_tooltip}]")
            print("-" * 60)
            
            # Options
            print("\nOptions:")
            print("  1. Never")
            print("  2. Sometimes")
            print("  3. Often")
            print("  4. Always")
            print("\n  [b] Back   [q] Quit")
            
            # Input Loop
            while True:
                choice = self.get_input("\nSelect (1-4): ").lower()
                
                if choice == 'q':
                    confirm = self.get_input("Are you sure you want to quit? (y/n): ").lower()
                    if confirm == 'y':
                        print("Exiting...")
                        sys.exit(0)
                
                elif choice == 'b':
                    if self.session.go_back():
                        break # Break input loop to re-render previous q
                    else:
                        print("Already at the first question.")
                
                elif choice in ('1', '2', '3', '4'):
                    self.session.submit_answer(int(choice))
                    break # Advance to next q
                
                else:
                    print("Invalid input. Please enter 1-4, 'b', or 'q'.")

    def run_reflection(self) -> None:
        """Reflection Phase"""
        if not self.session:
            return

        self.clear_screen()
        print("="*60)
        print("      F I N A L   R E F L E C T I O N")
        print("="*60 + "\n")
        
        print("Describe a recent situation where you felt emotionally challenged.")
        print("How did you handle it?\n")
        
        text = self.get_input("> ")
        
        print("\nAnalyzing...")
        self.session.submit_reflection(text)
        time.sleep(1)

    def get_score_label(self, percentage: float) -> Tuple[str, str, str]:
        """Return (label, emoji, color) based on score percentage"""
        if percentage >= 85:
            return ("EXCELLENT", "🌟", Colors.GREEN)
        elif percentage >= 70:
            return ("GOOD", "✨", Colors.CYAN)
        elif percentage >= 50:
            return ("AVERAGE", "📊", Colors.YELLOW)
        else:
            return ("NEEDS WORK", "📈", Colors.RED)

    def get_sentiment_label(self, score: float) -> str:
        """Return sentiment description"""
        if score >= 50:
            return "Positive"
        elif score >= 0:
            return "Neutral"
        else:
            return "Negative"

    def get_historical_data(self) -> Tuple[Optional[float], Optional[float]]:
        """Fetch user's previous scores for comparison"""
        try:
            from app.db import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get last score (excluding current)
            cursor.execute(
                "SELECT total_score FROM scores WHERE username = ? ORDER BY timestamp DESC LIMIT 2",
                (self.username,)
            )
            rows = cursor.fetchall()
            last_score = rows[1][0] if len(rows) > 1 else None
            
            # Get age group average
            cursor.execute(
                "SELECT AVG(total_score) FROM scores WHERE detailed_age_group = ?",
                (self.age_group,)
            )
            avg_row = cursor.fetchone()
            age_avg = avg_row[0] if avg_row and avg_row[0] else None
            
            return last_score, age_avg
        except Exception:
            return None, None

    def show_results(self) -> None:
        """Display Enhanced Final Results"""
        if not self.session:
            return

        success = self.session.finish_exam()
        if not success:
            print("Error saving results.")
            return

        self.clear_screen()
        
        # Calculate metrics
        max_score = len(self.session.responses) * 4
        percentage = (self.session.score / max_score * 100) if max_score > 0 else 0
        label, emoji, color = self.get_score_label(percentage)
        sentiment_label = self.get_sentiment_label(self.session.sentiment_score)
        
        # Get historical data
        last_score, age_avg = self.get_historical_data()
        
        # Header
        print("="*60)
        print("      R E S U L T S")
        print("="*60 + "\n")
        
        # Main Score with color
        score_text = f"{self.session.score}/{max_score} ({percentage:.0f}%) - {label} {emoji}"
        print(f"Score: {colorize(score_text, color)}")
        print(f"Sentiment: {self.session.sentiment_score:.1f} ({sentiment_label})")
        
        # ASCII Progress Bar
        bar_len = 20
        filled = int(bar_len * percentage / 100)
        bar = '█' * filled + '░' * (bar_len - filled)
        print(f"\n[{bar}] {percentage:.0f}%")
        
        # Comparisons
        print("")
        if age_avg:
            diff = self.session.score - age_avg
            direction = "↑" if diff > 0 else "↓" if diff < 0 else "→"
            print(f"📊 Age group ({self.age_group}): {direction} {abs(diff):.0f} vs average ({age_avg:.0f})")
        
        if last_score is not None:
            diff = self.session.score - last_score
            direction = "↑" if diff > 0 else "↓" if diff < 0 else "→"
            print(f"📈 Trend: {direction} {abs(diff)} from last attempt ({last_score})")
        
        # Warnings
        if self.session.is_rushed:
            print("\n⚠️  Note: You seemed to rush through the questions.")
        
        if self.session.is_inconsistent:
            print("\n⚠️  Note: Your responses show some inconsistency.")
            
        print("\n" + "="*60)
        print("Thank you for using Soul Sense CLI.")
        self.get_input("\nPress Enter to exit...")

    def show_main_menu(self) -> int:
        """Display main menu and return user choice"""
        self.print_header()
        
        print(f"Welcome back, {self.username}!\n" if self.username else "")
        print("  1. 📝 Start New Exam")
        print("  2. 📋 View History")
        print("  3. 📊 View Statistics")
        print("  4. 📈 Dashboard")
        print("  5. 💾 Export Results")
        print("  6. ⚙️  Settings")
        print("  7. ℹ️  Version")
        print("  8. 🚪 Exit")
        print("")
        
        while True:
            choice = self.get_input("Select option (1-8): ")
            if choice in ('1', '2', '3', '4', '5', '6', '7', '8'):
                return int(choice)
            print("Invalid choice. Please enter 1-8.")

    def show_history(self) -> None:
        """Display exam history with ASCII graph"""
        self.clear_screen()
        print("="*60)
        print("      E X A M   H I S T O R Y")
        print("="*60 + "\n")
        
        try:
            from app.db import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT timestamp, total_score, sentiment_score, is_rushed, is_inconsistent 
                   FROM scores WHERE username = ? 
                   ORDER BY timestamp DESC LIMIT 10""",
                (self.username,)
            )
            rows = cursor.fetchall()
            
            if not rows:
                print("No exam history found. Take your first exam!")
            else:
                # Score Trend Graph (ASCII Sparkline)
                scores = [r[1] or 0 for r in reversed(rows)]  # Oldest to newest
                if len(scores) > 1:
                    print("📈 Score Trend (oldest → newest):")
                    max_score = 40
                    graph_height = 5
                    for level in range(graph_height, 0, -1):
                        threshold = (level / graph_height) * max_score
                        line = "  "
                        for score in scores:
                            if score >= threshold:
                                line += colorize("█", Colors.GREEN if score >= 28 else Colors.YELLOW if score >= 20 else Colors.RED)
                            else:
                                line += "░"
                            line += " "
                        print(line)
                    print("  " + "─" * (len(scores) * 2))
                    print("")
                
                # Table with colors
                print(f"{'Date':<20} {'Score':<12} {'Sentiment':<10} {'Status'}")
                print("-" * 60)
                for row in rows:
                    date = row[0][:16] if row[0] else "N/A"
                    score_val = row[1] or 0
                    pct = (score_val / 40) * 100
                    
                    # Color based on score
                    if pct >= 70:
                        score_color = Colors.GREEN
                    elif pct >= 50:
                        score_color = Colors.YELLOW
                    else:
                        score_color = Colors.RED
                    
                    score_str = colorize(f"{score_val}/40 ({pct:.0f}%)", score_color)
                    sentiment = f"{row[2]:.1f}" if row[2] else "0.0"
                    
                    # Status icons
                    flags = []
                    if row[3]: flags.append("⚡")  # rushed
                    if row[4]: flags.append("⚠️")  # inconsistent
                    status = " ".join(flags) if flags else colorize("✓", Colors.GREEN)
                    
                    print(f"{date:<20} {score_str:<22} {sentiment:<10} {status}")
                    
        except Exception as e:
            print(f"Error loading history: {e}")
        
        self.get_input("\nPress Enter to continue...")

    def show_statistics(self) -> None:
        """Display comprehensive user statistics"""
        self.clear_screen()
        print("="*60)
        print("      S T A T I S T I C S")
        print("="*60 + "\n")
        
        try:
            from app.db import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            # Basic stats
            cursor.execute("SELECT COUNT(*) FROM scores WHERE username = ?", (self.username,))
            total = cursor.fetchone()[0] or 0
            
            if total == 0:
                print("No exam data yet. Take your first exam!")
                self.get_input("\nPress Enter to continue...")
                return
            
            cursor.execute("SELECT AVG(total_score) FROM scores WHERE username = ?", (self.username,))
            avg = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT MAX(total_score) FROM scores WHERE username = ?", (self.username,))
            best = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT MIN(total_score) FROM scores WHERE username = ?", (self.username,))
            worst = cursor.fetchone()[0] or 0
            
            # Consistency rate (non-rushed exams)
            cursor.execute("SELECT COUNT(*) FROM scores WHERE username = ? AND is_rushed = 0", (self.username,))
            consistent = cursor.fetchone()[0] or 0
            consistency_rate = (consistent / total * 100) if total > 0 else 0
            
            # First vs Last score (improvement)
            cursor.execute("SELECT total_score FROM scores WHERE username = ? ORDER BY timestamp ASC LIMIT 1", (self.username,))
            first_score = cursor.fetchone()
            first_score = first_score[0] if first_score else 0
            
            cursor.execute("SELECT total_score FROM scores WHERE username = ? ORDER BY timestamp DESC LIMIT 1", (self.username,))
            last_score = cursor.fetchone()
            last_score = last_score[0] if last_score else 0
            
            improvement = last_score - first_score
            
            # Average sentiment
            cursor.execute("SELECT AVG(sentiment_score) FROM scores WHERE username = ?", (self.username,))
            avg_sentiment = cursor.fetchone()[0] or 0
            
            # Display stats with colors
            print(colorize("📊 OVERVIEW", Colors.BOLD))
            print(f"   Total Exams:        {total}")
            print(f"   Consistency Rate:   {colorize(f'{consistency_rate:.0f}%', Colors.GREEN if consistency_rate >= 80 else Colors.YELLOW)}")
            print("")
            
            print(colorize("📈 SCORES", Colors.BOLD))
            avg_color = Colors.GREEN if avg >= 28 else Colors.YELLOW if avg >= 20 else Colors.RED
            print(f"   Average:            {colorize(f'{avg:.1f}/40 ({avg/40*100:.0f}%)', avg_color)}")
            print(f"   Best:               {colorize(f'{best}/40', Colors.GREEN)}")
            print(f"   Worst:              {colorize(f'{worst}/40', Colors.RED)}")
            print("")
            
            print(colorize("📉 TREND", Colors.BOLD))
            if improvement > 0:
                trend_str = colorize(f"↑ +{improvement} points", Colors.GREEN)
            elif improvement < 0:
                trend_str = colorize(f"↓ {improvement} points", Colors.RED)
            else:
                trend_str = "→ No change"
            print(f"   First → Last:       {trend_str}")
            print(f"   First Score:        {first_score}/40")
            print(f"   Latest Score:       {last_score}/40")
            print("")
            
            print(colorize("💭 SENTIMENT", Colors.BOLD))
            sent_color = Colors.GREEN if avg_sentiment >= 50 else Colors.YELLOW if avg_sentiment >= 0 else Colors.RED
            sent_label = "Positive" if avg_sentiment >= 50 else "Neutral" if avg_sentiment >= 0 else "Negative"
            print(f"   Avg Sentiment:      {colorize(f'{avg_sentiment:.1f} ({sent_label})', sent_color)}")
                
        except Exception as e:
            print(f"Error loading statistics: {e}")
        
        self.get_input("\nPress Enter to continue...")

    def export_results(self) -> None:
        """Export results to file with directory selection"""
        self.clear_screen()
        print("="*60)
        print("      E X P O R T   R E S U L T S")
        print("="*60 + "\n")
        
        print("  1. Export as JSON")
        print("  2. Export as CSV")
        print("  3. Back to Menu")
        print("")
        
        choice = self.get_input("Select format (1-3): ")
        
        if choice == '3' or choice not in ('1', '2'):
            return
            
        try:
            from app.db import get_connection
            import json
            from datetime import datetime
            
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT timestamp, total_score, sentiment_score, reflection_text, is_rushed, is_inconsistent 
                   FROM scores WHERE username = ? ORDER BY timestamp DESC""",
                (self.username,)
            )
            rows = cursor.fetchall()
            
            if not rows:
                print("No data to export.")
                self.get_input("\nPress Enter to continue...")
                return
            
            # Ask for directory
            print(f"\nFound {len(rows)} exam(s) to export.")
            default_dir = os.path.abspath("exports")
            print(f"\nDefault directory: {default_dir}")
            custom_dir = self.get_input("Enter directory path (or press Enter for default): ").strip()
            
            try:
                from app.utils.file_validation import validate_file_path, sanitize_filename, ValidationError
                
                if custom_dir:
                    # User provided a directory. We validate it exists or can be created.
                    # Note: We don't strictly enforce base_dir here for CLI as power users might want 
                    # to export to Desktop/etc., but we DO ensure it treats '..' safely via realpath
                    # For strict mode we could enforce base_dir=default_dir
                    export_dir = os.path.realpath(os.path.abspath(custom_dir))
                else:
                    export_dir = default_dir
                
                os.makedirs(export_dir, exist_ok=True)
                
            except Exception as e:
                print(f"\n{colorize('❌ Error:', Colors.RED)} Invalid directory: {e}")
                self.get_input("\nPress Enter to continue...")
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = "json" if choice == '1' else "csv"
            
            # Sanitize username for filename
            safe_username = sanitize_filename(self.username)
            filename = f"{safe_username}_{timestamp}.{ext}"
            
            # Final validation before writing
            try:
                filepath = validate_file_path(
                    os.path.join(export_dir, filename), 
                    allowed_extensions=[f".{ext}"]
                )
            except ValidationError as ve:
                print(f"\n{colorize('❌ Security Error:', Colors.RED)} {ve}")
                self.get_input("\nPress Enter to continue...")
                return
            
            # Import atomic_write
            from app.utils.atomic import atomic_write
            
            if choice == '1':
                # JSON Export
                data = {
                    "username": self.username,
                    "exported_at": datetime.now().isoformat(),
                    "total_exams": len(rows),
                    "results": [
                        {
                            "timestamp": r[0],
                            "score": r[1],
                            "sentiment": r[2],
                            "reflection": r[3],
                            "is_rushed": bool(r[4]),
                            "is_inconsistent": bool(r[5])
                        } for r in rows
                    ]
                }
                with atomic_write(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    
            elif choice == '2':
                # CSV Export
                with atomic_write(filepath, 'w', encoding='utf-8') as f:
                    f.write("timestamp,score,sentiment,reflection,is_rushed,is_inconsistent\n")
                    for r in rows:
                        reflection = (r[3] or "").replace('"', '""').replace('\n', ' ')
                        f.write(f'"{r[0]}",{r[1]},{r[2]},"{reflection}",{r[4]},{r[5]}\n')
            
            print(f"\n{colorize('✅ Export successful!', Colors.GREEN)}")
            print(f"\nFile saved to:")
            print(colorize(f"   {filepath}", Colors.CYAN))
                
        except Exception as e:
            print(f"\n{colorize('❌ Error exporting:', Colors.RED)} {e}")
        
        self.get_input("\nPress Enter to continue...")

    def show_dashboard(self) -> None:
        """Display dashboard sub-menu"""
        while True:
            self.clear_screen()
            print("="*60)
            print("      D A S H B O A R D")
            print("="*60 + "\n")
            
            print("  1. 📈 EQ Score Trends")
            print("  2. ⏱️  Time-Based Analysis")
            print("  3. 🧠 Emotional Profile")
            print("  4. 💡 AI Insights")
            print("  5. ← Back to Menu")
            print("")
            
            choice = self.get_input("Select option (1-5): ")
            
            if choice == '1':
                self.show_eq_trends()
            elif choice == '2':
                self.show_time_analysis()
            elif choice == '3':
                self.show_emotional_profile()
            elif choice == '4':
                self.show_ai_insights()
            elif choice == '5':
                return
            else:
                print("Invalid choice.")

    def show_eq_trends(self) -> None:
        """Display EQ score trends over time"""
        self.clear_screen()
        print("="*60)
        print("      E Q   S C O R E   T R E N D S")
        print("="*60 + "\n")
        
        try:
            from app.db import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT timestamp, total_score FROM scores 
                   WHERE username = ? ORDER BY timestamp ASC LIMIT 20""",
                (self.username,)
            )
            rows = cursor.fetchall()
            
            if not rows:
                print("No data yet. Take some exams first!")
            else:
                # ASCII Graph
                print(colorize("📊 Score Over Time:", Colors.BOLD))
                print("")
                max_score = 40
                for row in rows:
                    date = row[0][:10] if row[0] else "N/A"
                    score = row[1] or 0
                    pct = score / max_score
                    bar_len = int(pct * 30)
                    
                    if score >= 28:
                        color = Colors.GREEN
                    elif score >= 20:
                        color = Colors.YELLOW
                    else:
                        color = Colors.RED
                    
                    bar = colorize("█" * bar_len, color) + "░" * (30 - bar_len)
                    print(f"  {date} [{bar}] {score}/40")
                    
        except Exception as e:
            print(f"Error: {e}")
        
        self.get_input("\nPress Enter to continue...")

    def show_time_analysis(self) -> None:
        """Display time-based analysis"""
        self.clear_screen()
        print("="*60)
        print("      T I M E - B A S E D   A N A L Y S I S")
        print("="*60 + "\n")
        
        try:
            from app.db import get_connection
            from datetime import datetime
            
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get all scores with timestamps
            cursor.execute(
                """SELECT timestamp, total_score FROM scores 
                   WHERE username = ? ORDER BY timestamp DESC""",
                (self.username,)
            )
            rows = cursor.fetchall()
            
            if not rows:
                print("No data yet.")
            else:
                # Analyze by hour
                hour_scores: Dict[int, List[float]] = {}
                for row in rows:
                    try:
                        ts = datetime.fromisoformat(row[0])
                        hour = ts.hour
                        if hour not in hour_scores:
                            hour_scores[hour] = []
                        hour_scores[hour].append(row[1] or 0)
                    except:
                        pass
                
                if hour_scores:
                    print(colorize("⏰ Performance by Time of Day:", Colors.BOLD))
                    print("")
                    
                    best_hour = max(hour_scores, key=lambda h: sum(hour_scores[h])/len(hour_scores[h]))
                    worst_hour = min(hour_scores, key=lambda h: sum(hour_scores[h])/len(hour_scores[h]))
                    
                    best_avg = sum(hour_scores[best_hour]) / len(hour_scores[best_hour])
                    worst_avg = sum(hour_scores[worst_hour]) / len(hour_scores[worst_hour])
                    
                    print(f"   {colorize('Best time:', Colors.GREEN)} {best_hour:02d}:00 - Avg: {best_avg:.1f}/40")
                    print(f"   {colorize('Worst time:', Colors.RED)} {worst_hour:02d}:00 - Avg: {worst_avg:.1f}/40")
                    print("")
                    print(colorize("💡 Tip:", Colors.CYAN), f"Consider taking exams around {best_hour:02d}:00 for best results!")
                else:
                    print("Not enough data for time analysis.")
                    
        except Exception as e:
            print(f"Error: {e}")
        
        self.get_input("\nPress Enter to continue...")

    def show_emotional_profile(self) -> None:
        """Display emotional profile analysis"""
        self.clear_screen()
        print("="*60)
        print("      E M O T I O N A L   P R O F I L E")
        print("="*60 + "\n")
        
        try:
            from app.db import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get average score and sentiment
            cursor.execute(
                """SELECT AVG(total_score), AVG(sentiment_score), COUNT(*) 
                   FROM scores WHERE username = ?""",
                (self.username,)
            )
            row = cursor.fetchone()
            
            if not row or row[2] == 0:
                print("No data yet. Take some exams first!")
            else:
                avg_score = row[0] or 0
                avg_sentiment = row[1] or 0
                count = row[2]
                
                # Determine profile based on score and sentiment
                score_pct = (avg_score / 40) * 100
                
                if score_pct >= 70 and avg_sentiment >= 30:
                    profile = ("🌟 Emotionally Intelligent Leader", Colors.GREEN)
                    desc = "You exhibit strong EQ with positive outlook."
                elif score_pct >= 70:
                    profile = ("🎯 High Achiever", Colors.CYAN)
                    desc = "Strong EQ skills, potential for more positivity."
                elif score_pct >= 50 and avg_sentiment >= 0:
                    profile = ("📈 Growing Learner", Colors.YELLOW)
                    desc = "Developing EQ with room for growth."
                elif score_pct >= 50:
                    profile = ("🔄 In Transition", Colors.YELLOW)
                    desc = "Building skills, facing some challenges."
                else:
                    profile = ("🌱 Early Stage", Colors.MAGENTA)
                    desc = "Beginning your EQ journey."
                
                print(colorize("Your Emotional Profile:", Colors.BOLD))
                print("")
                print(f"   {colorize(profile[0], profile[1])}")
                print(f"   {desc}")
                print("")
                print(colorize("Metrics:", Colors.BOLD))
                print(f"   EQ Score:    {avg_score:.1f}/40 ({score_pct:.0f}%)")
                print(f"   Sentiment:   {avg_sentiment:.1f}")
                print(f"   Exams Taken: {count}")
                
        except Exception as e:
            print(f"Error: {e}")
        
        self.get_input("\nPress Enter to continue...")

    def show_ai_insights(self):
        """Display AI-generated insights"""
        self.clear_screen()
        print("="*60)
        print("      A I   I N S I G H T S")
        print("="*60 + "\n")
        
        try:
            from app.db import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get user data
            cursor.execute(
                """SELECT total_score, sentiment_score, is_rushed, is_inconsistent 
                   FROM scores WHERE username = ? ORDER BY timestamp DESC LIMIT 5""",
                (self.username,)
            )
            rows = cursor.fetchall()
            
            if not rows:
                print("Not enough data for AI insights. Take some exams first!")
            else:
                print(colorize("🤖 Personalized Insights:", Colors.BOLD))
                print("")
                
                scores = [r[0] or 0 for r in rows]
                sentiments = [r[1] or 0 for r in rows]
                rushed_count = sum(1 for r in rows if r[2])
                inconsistent_count = sum(1 for r in rows if r[3])
                
                avg_score = sum(scores) / len(scores)
                trend = scores[0] - scores[-1] if len(scores) > 1 else 0
                
                # Generate insights
                insights = []
                
                if avg_score >= 30:
                    insights.append(f"✅ {colorize('Strong EQ!', Colors.GREEN)} Your average score of {avg_score:.0f}/40 shows excellent emotional intelligence.")
                elif avg_score >= 20:
                    insights.append(f"📊 Your average score of {avg_score:.0f}/40 is in the developing range. Keep practicing!")
                else:
                    insights.append(f"🌱 Your average score suggests you're at the beginning of your EQ journey.")
                
                if trend > 0:
                    insights.append(f"📈 {colorize('Improving!', Colors.GREEN)} Your recent scores are trending upward by {trend:.0f} points.")
                elif trend < 0:
                    insights.append(f"📉 Recent scores dropped by {abs(trend):.0f} points. Consider taking the exam when relaxed.")
                
                if rushed_count > len(rows) // 2:
                    insights.append(f"⚡ {colorize('Tip:', Colors.YELLOW)} You tend to rush. Take more time to reflect on each question.")
                
                if inconsistent_count > 0:
                    insights.append(f"🔄 Some inconsistency detected. Try to be more mindful of your answers.")
                
                avg_sentiment = sum(sentiments) / len(sentiments)
                if avg_sentiment >= 30:
                    insights.append(f"😊 {colorize('Positive outlook!', Colors.GREEN)} Your reflection sentiment is optimistic.")
                elif avg_sentiment < 0:
                    insights.append(f"💭 Consider focusing on positive aspects in your reflections.")
                
                for insight in insights:
                    print(f"   {insight}")
                    print("")
                    
        except Exception as e:
            print(f"Error: {e}")
        
        self.get_input("\nPress Enter to continue...")

    def show_settings(self):
        """Display settings menu"""
        while True:
            self.clear_screen()
            print("="*60)
            print("      S E T T I N G S")
            print("="*60 + "\n")
            
            print(f"   Current Settings:")
            print(f"   ─────────────────")
            print(f"   Questions per exam: {colorize(str(self.num_questions), Colors.CYAN)}")
            print("")
            print("  1. Change number of questions")
            print("  2. ← Back to Menu")
            print("")
            
            choice = self.get_input("Select option (1-2): ")
            
            if choice == '1':
                # Loop until valid input provided or user cancels with 'b'
                from app.validation import validate_range
                while True:
                    new_val = self.get_input(f"Enter new question count (1-20, current: {self.num_questions}) [b to cancel]: ")
                    if new_val.lower() == 'b':
                        break

                    # Use validate_range to check numeric and bounds
                    valid, msg = validate_range(new_val, 1, 20, "Question count")
                    if not valid:
                        print(colorize(f"Invalid: {msg}", Colors.YELLOW))
                        continue

                    # Ensure an integer value
                    try:
                        q_int = int(float(new_val))
                    except (ValueError, TypeError):
                        print(colorize("Please enter a whole number.", Colors.YELLOW))
                        continue

                    # Final bounds check after conversion (in case float like 3.5 was provided)
                    if q_int < 1 or q_int > 20:
                        print(colorize("Invalid value. Must be an integer between 1 and 20.", Colors.YELLOW))
                        continue

                    # Apply setting
                    self.num_questions = q_int
                    try:
                        from app.utils import save_settings
                        self.settings["question_count"] = self.num_questions
                        save_settings(self.settings)
                        print(colorize(f"\n✅ Saved! Next exam will have {self.num_questions} questions.", Colors.GREEN))
                        print(colorize("   (This setting is shared with GUI)", Colors.CYAN))
                    except Exception as e:
                        print(f"\n{colorize('Warning:', Colors.YELLOW)} Setting applied for this session but could not save: {e}")

                    self.get_input("\nPress Enter to continue...")
                    break
            elif choice == '2':
                return

    def show_version(self) -> None:
        """Display application version information"""
        from app.constants import VERSION, APP_NAME
        
        self.clear_screen()
        print("="*60)
        print("      V E R S I O N   I N F O")
        print("="*60 + "\n")
        
        print(f"  {colorize(APP_NAME, Colors.CYAN)} {colorize(f'v{VERSION}', Colors.GREEN)}")
        print(f"\n  Build Date: January 2026")
        print(f"  Python {sys.version.split()[0]}")
        print("\n" + "="*60)
        
        self.get_input("\nPress Enter to continue...")

    def run_exam_flow(self):
        """Run complete exam flow"""
        self.initialize_session()
        self.run_exam_loop()
        self.run_reflection()
        self.show_results()

    def run(self):
        """Main execution flow with menu"""
        try:
            # Initial authentication
            if not self.username:
                self.authenticate()
            
            # Main menu loop
            while True:
                choice = self.show_main_menu()
                
                if choice == 1:
                    self.run_exam_flow()
                elif choice == 2:
                    self.show_history()
                elif choice == 3:
                    self.show_statistics()
                elif choice == 4:
                    self.show_dashboard()
                elif choice == 5:
                    self.export_results()
                elif choice == 6:
                    self.show_settings()
                elif choice == 7:
                    self.show_version()
                elif choice == 8:
                    print("\nGoodbye! 👋")
                    sys.exit(0)
                    
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except Exception as e:
            print(f"\nFatal Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    if '--help' in sys.argv:
        print("Soul Sense CLI - Run with 'python -m app.cli'")
        sys.exit(0)
    
    if '--version' in sys.argv or '-v' in sys.argv:
        from app.constants import VERSION, APP_NAME
        print(f"{APP_NAME} v{VERSION}")
        sys.exit(0)
        
    cli = SoulSenseCLI()
    cli.run()
