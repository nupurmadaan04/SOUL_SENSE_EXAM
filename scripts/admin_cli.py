"""
Command Line Interface for Admin Operations
Provides CLI access to question management
"""

import sys
import argparse
from admin_interface import QuestionDatabase
import getpass
from tabulate import tabulate
import numpy as np
from app.db import get_connection


class AdminCLI:
    """Command-line interface for admin operations"""
    
    def __init__(self):
        self.db = QuestionDatabase()
        self.authenticated = False
    
    def authenticate(self):
        """Authenticate admin user"""
        print("\n" + "="*50)
        print("  SoulSense Admin CLI - Authentication Required")
        print("="*50 + "\n")
        
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        
        if self.db.verify_admin(username, password):
            self.authenticated = True
            print(f"\n✓ Authenticated as {username}\n")
            return True
        else:
            print("\n✗ Authentication failed\n")
            return False
    
    def list_questions(self, category=None, include_inactive=False):
        """List all questions"""
        questions = self.db.get_all_questions(include_inactive)
        
        if category and category != "all":
            questions = [q for q in questions if q['category'].lower() == category.lower()]
        
        if not questions:
            print("\nNo questions found.\n")
            return
        
        # Prepare data for table
        table_data = []
        for q in questions:
            status = "✓" if q['is_active'] == 1 else "✗"
            text = q['text'][:60] + "..." if len(q['text']) > 60 else q['text']
            table_data.append([
                q['id'],
                text,
                q['category'],
                f"{q['age_min']}-{q['age_max']}",
                q['difficulty'],
                q['weight'],
                status
            ])
        
        headers = ["ID", "Question Text", "Category", "Age Range", "Diff", "Weight", "Active"]
        print(f"\n{tabulate(table_data, headers=headers, tablefmt='grid')}\n")
        print(f"Total: {len(questions)} question(s)\n")
    
    def add_question(self):
        """Add a new question interactively"""
        print("\n" + "="*50)
        print("  Add New Question")
        print("="*50 + "\n")
        
        text = input("Question text: ").strip()
        if not text:
            print("✗ Question text is required")
            return
        
        # Show existing categories
        categories = self.db.get_categories()
        if categories:
            print(f"\nExisting categories: {', '.join(categories)}")
        
        category = input("Category (default: General): ").strip() or "General"
        
        try:
            age_min = int(input("Minimum age (default: 12): ") or "12")
            age_max = int(input("Maximum age (default: 100): ") or "100")
            difficulty = int(input("Difficulty 1-5 (default: 3): ") or "3")
            weight = float(input("Weight (default: 1.0): ") or "1.0")
            
            if age_min > age_max:
                print("✗ Min age cannot be greater than max age")
                return
            
            question_id = self.db.add_question(text, category, age_min, age_max, difficulty, weight)
            print(f"\n✓ Question added successfully! ID: {question_id}\n")
            
        except ValueError:
            print("✗ Invalid input values")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    def view_question(self, question_id):
        """View a specific question"""
        question = self.db.get_question_by_id(question_id)
        
        if not question:
            print(f"\n✗ Question with ID {question_id} not found\n")
            return
        
        print("\n" + "="*50)
        print(f"  Question #{question['id']}")
        print("="*50)
        print(f"\nText: {question['text']}")
        print(f"Category: {question['category']}")
        print(f"Age Range: {question['age_min']} - {question['age_max']}")
        print(f"Difficulty: {question['difficulty']}/5")
        print(f"Weight: {question['weight']}")
        print(f"Status: {'Active' if question['is_active'] == 1 else 'Inactive'}")
        print(f"Created: {question['created_at']}")
        print(f"Updated: {question['updated_at']}")
        print("="*50 + "\n")
    
    def update_question(self, question_id):
        """Update a question interactively"""
        question = self.db.get_question_by_id(question_id)
        
        if not question:
            print(f"\n✗ Question with ID {question_id} not found\n")
            return
        
        print("\n" + "="*50)
        print(f"  Update Question #{question_id}")
        print("="*50 + "\n")
        print(f"Current text: {question['text']}\n")
        
        text = input("New text (press Enter to keep current): ").strip()
        category = input(f"Category (current: {question['category']}): ").strip()
        age_min_input = input(f"Min age (current: {question['age_min']}): ").strip()
        age_max_input = input(f"Max age (current: {question['age_max']}): ").strip()
        difficulty_input = input(f"Difficulty (current: {question['difficulty']}): ").strip()
        weight_input = input(f"Weight (current: {question['weight']}): ").strip()
        
        try:
            text = text if text else None
            category = category if category else None
            age_min = int(age_min_input) if age_min_input else None
            age_max = int(age_max_input) if age_max_input else None
            difficulty = int(difficulty_input) if difficulty_input else None
            weight = float(weight_input) if weight_input else None
            
            if self.db.update_question(question_id, text, category, age_min, age_max, difficulty, weight):
                print(f"\n✓ Question updated successfully!\n")
            else:
                print(f"\n✗ No changes made\n")
                
        except ValueError:
            print("✗ Invalid input values")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    def delete_question(self, question_id):
        """Delete a question"""
        question = self.db.get_question_by_id(question_id)
        
        if not question:
            print(f"\n✗ Question with ID {question_id} not found\n")
            return
        
        print(f"\nQuestion: {question['text'][:100]}...")
        confirm = input("\nAre you sure you want to delete this question? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            if self.db.delete_question(question_id):
                print(f"\n✓ Question deleted successfully!\n")
            else:
                print(f"\n✗ Failed to delete question\n")
        else:
            print("\n✗ Deletion cancelled\n")
    
    def show_categories(self):
        """Show category statistics"""
        questions = self.db.get_all_questions()
        
        # Count by category
        category_counts = {}
        for q in questions:
            cat = q['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Prepare table
        table_data = [[cat, count] for cat, count in sorted(category_counts.items())]
        headers = ["Category", "Question Count"]
        
        print(f"\n{tabulate(table_data, headers=headers, tablefmt='grid')}\n")
        print(f"Total categories: {len(category_counts)}\n")
    
    def create_admin_user(self):
        """Create a new admin user"""
        print("\n" + "="*50)
        print("  Create New Admin User")
        print("="*50 + "\n")
        
        username = input("Username: ").strip()
        if not username:
            print("✗ Username is required")
            return
        
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        
        if password != confirm:
            print("✗ Passwords don't match")
            return
        
        if len(password) < 4:
            print("✗ Password must be at least 4 characters")
            return
        
        if self.db.create_admin(username, password):
            print(f"\n✓ Admin user '{username}' created successfully!\n")
        else:
            print(f"\n✗ Username already exists\n")

    def show_stats(self):
        """Show descriptive statistics for emotional scores"""
        print("\n" + "="*50)
        print("  Descriptive Statistics (Admin Only)")
        print("="*50 + "\n")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Stats for Total Score
            cursor.execute("SELECT total_score FROM scores WHERE total_score IS NOT NULL")
            total_scores = [row[0] for row in cursor.fetchall()]
            
            # Stats for Sentiment Score
            cursor.execute("SELECT sentiment_score FROM scores WHERE sentiment_score IS NOT NULL")
            sentiment_scores = [row[0] for row in cursor.fetchall()]
            
            if not total_scores and not sentiment_scores:
                print("No scores available.\n")
                return

            def calculate_stats(data, name):
                if not data:
                    return []
                arr = np.array(data)
                return [
                    [f"--- {name} ---", ""],
                    ["Count", len(data)],
                    ["Mean", f"{np.mean(arr):.2f}"],
                    ["Median", f"{np.median(arr):.2f}"],
                    ["Variance", f"{np.var(arr):.2f}"],
                    ["Min", f"{np.min(arr):.2f}"],
                    ["Max", f"{np.max(arr):.2f}"]
                ]

            data = []
            if total_scores:
                data.extend(calculate_stats(total_scores, "Total Score"))
                data.append(["", ""]) # Spacer
            
            if sentiment_scores:
                data.extend(calculate_stats(sentiment_scores, "Sentiment Score"))
            
            print(tabulate(data, headers=["Metric", "Value"], tablefmt="grid"))
            print("\n")
            
        except Exception as e:
            print(f"✗ Error calculating statistics: {e}\n")
        finally:
            conn.close()


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="SoulSense Admin CLI")
    parser.add_argument('command', choices=['list', 'add', 'view', 'update', 'delete', 'categories', 'create-admin','stats'],
                       help='Command to execute')
    parser.add_argument('--id', type=int, help='Question ID (for view, update, delete)')
    parser.add_argument('--category', help='Filter by category (for list)')
    parser.add_argument('--inactive', action='store_true', help='Include inactive questions (for list)')
    parser.add_argument('--no-auth', action='store_true', help='Skip authentication (for create-admin only)')
    
    args = parser.parse_args()
    
    cli = AdminCLI()
    
    # Authentication (skip for create-admin if --no-auth is set)
    if args.command == 'create-admin' and args.no_auth:
        cli.create_admin_user()
        return
    
    if not cli.authenticate():
        sys.exit(1)
    
    # Execute command
    if args.command == 'list':
        cli.list_questions(args.category, args.inactive)
    
    elif args.command == 'add':
        cli.add_question()
    
    elif args.command == 'view':
        if not args.id:
            print("✗ --id is required for view command")
            sys.exit(1)
        cli.view_question(args.id)
    
    elif args.command == 'update':
        if not args.id:
            print("✗ --id is required for update command")
            sys.exit(1)
        cli.update_question(args.id)
    
    elif args.command == 'delete':
        if not args.id:
            print("✗ --id is required for delete command")
            sys.exit(1)
        cli.delete_question(args.id)
    
    elif args.command == 'categories':
        cli.show_categories()
    
    elif args.command == 'create-admin':
        cli.create_admin_user()

    elif args.command == 'stats':
        cli.show_stats()
        
if __name__ == "__main__":
    main()
