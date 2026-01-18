"""
Synthetic Data Generator for SOUL_SENSE_EXAM
Generates realistic test data for analytics and ML model testing
FIXED VERSION - Matches actual database schema
"""

#  Run the generator (it will auto-create any missing tables):
# python -m scripts.generate_synthetic_data --users 50


import sys
import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from faker import Faker
import numpy as np
from tqdm import tqdm

class SyntheticDataGenerator:
    """Generates synthetic emotional intelligence test data"""
    
    def __init__(self, num_users=100, num_responses_per_user=1, 
                 start_date='2024-01-01', end_date='2025-01-07'):
        """
        Initialize the generator
        
        Args:
            num_users: Number of synthetic users to create
            num_responses_per_user: Number of test responses per user
            start_date: Start date for synthetic data
            end_date: End date for synthetic data
        """
        self.faker = Faker()
        self.num_users = num_users
        self.num_responses_per_user = num_responses_per_user
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Database path from centralized config
        from app.config import DB_PATH
        self.db_path = Path(DB_PATH)
        print(f"USING DB: {self.db_path}")
        
        # Emotional patterns for realistic data generation
        self.emotional_patterns = {
            'high_eq': {
                'response_bias': {'Never': 0.1, 'Sometimes': 0.3, 'Often': 0.4, 'Always': 0.2},
                'eq_score_range': (120, 150),
                'sentiment_range': (0.6, 0.9)
            },
            'medium_eq': {
                'response_bias': {'Never': 0.2, 'Sometimes': 0.4, 'Often': 0.3, 'Always': 0.1},
                'eq_score_range': (90, 119),
                'sentiment_range': (0.3, 0.7)
            },
            'low_eq': {
                'response_bias': {'Never': 0.4, 'Sometimes': 0.4, 'Often': 0.15, 'Always': 0.05},
                'eq_score_range': (60, 89),
                'sentiment_range': (0.1, 0.5)
            }
        }
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def generate_demographics(self):
        """Generate realistic user demographics"""
        age = random.randint(18, 70)
        if age <= 25:
            age_group = '18-25'
        elif age <= 35:
            age_group = '26-35'
        elif age <= 50:
            age_group = '36-50'
        else:
            age_group = '51+'
        
        return {
            'age': age,
            'age_group': age_group,
            'occupation': self.faker.job(),
            'location': self.faker.city()
        }
    
    def generate_emotional_pattern(self):
        """Assign emotional intelligence pattern to user"""
        patterns = list(self.emotional_patterns.keys())
        weights = [0.3, 0.5, 0.2]  # 30% high EQ, 50% medium, 20% low
        return random.choices(patterns, weights=weights, k=1)[0]
    
    def generate_responses(self, pattern, question_ids):
        """Generate responses based on emotional pattern"""
        pattern_config = self.emotional_patterns[pattern]
        responses = {}
        
        for q_id in question_ids:
            # Weighted random choice based on pattern
            choices = list(pattern_config['response_bias'].keys())
            weights = list(pattern_config['response_bias'].values())
            response_text = random.choices(choices, weights=weights, k=1)[0]
            
            # Map response text to score (1-4)
            score_map = {'Never': 1, 'Sometimes': 2, 'Often': 3, 'Always': 4}
            responses[q_id] = {
                'response': response_text,
                'score': score_map[response_text]
            }
        
        return responses
    
    def calculate_eq_score(self, responses, pattern):
        """Calculate realistic EQ score based on responses and pattern"""
        base_score_range = self.emotional_patterns[pattern]['eq_score_range']
        
        # Add some randomness within the pattern range
        base_score = random.randint(*base_score_range)
        
        # Calculate from responses
        total_possible = len(responses) * 4  # 4 points max per question
        actual_total = sum(r['score'] for r in responses.values())
        
        # Combine pattern-based score with actual response calculation
        response_based_score = (actual_total / total_possible) * 150
        
        # Weighted average: 70% pattern-based, 30% response-based
        final_score = int(0.7 * base_score + 0.3 * response_based_score)
        
        return min(max(final_score, 60), 150)  # Keep within 60-150 range
    
    def get_question_ids(self):
        """Get all question IDs from database - FIXED FOR YOUR SCHEMA"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if question_bank table exists (your actual table name)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='question_bank'
            """)
            
            if not cursor.fetchone():
                print("❌ 'question_bank' table not found!")
                print("Please run this first: python -m scripts.load_questions")
                return None
            
            # Get all question IDs from question_bank
            cursor.execute("SELECT id FROM question_bank ORDER BY id")
            question_ids = [row[0] for row in cursor.fetchall()]
            
            if not question_ids:
                print("❌ No questions found in question_bank!")
                print("Please run this first: python -m scripts.load_questions")
                return None
            
            print(f"✅ Found {len(question_ids)} questions in question_bank")
            return question_ids
            
        finally:
            conn.close()
    
    def check_tables_exist(self):
        """Check if all required tables exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        required_tables = ['users', 'question_bank', 'responses']
        existing_tables = []
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = [row[0] for row in cursor.fetchall()]
        
        print("\n📋 Database Tables Found:")
        for table in all_tables:
            print(f"  • {table}")
        
        conn.close()
        
        # Check for required tables
        for table in required_tables:
            if table not in all_tables:
                print(f"\n⚠️  Warning: '{table}' table not found")
        
        return all_tables
    
    def create_missing_tables(self):
        """Create missing tables if needed"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if users table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                print("Creating 'users' table...")
                cursor.execute("""
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        total_score INTEGER DEFAULT 0,
                        age INTEGER
                    )
                """)
                print("✅ Created 'users' table")
            
            # Check if responses table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='responses'")
            if not cursor.fetchone():
                print("Creating 'responses' table...")
                cursor.execute("""
                    CREATE TABLE responses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT,
                        question_id INTEGER,
                        response_value INTEGER,
                        age_group TEXT,
                        timestamp TEXT
                    )
                """)
                print("✅ Created 'responses' table")
            
            conn.commit()
            
        except Exception as e:
            print(f"Error creating tables: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def insert_synthetic_data(self, clear_existing=False):
        """
        Insert generated synthetic data into database
        
        Args:
            clear_existing: If True, clears existing synthetic users first
        """
        # First check database structure
        print("\n🔍 Checking database structure...")
        all_tables = self.check_tables_exist()
        
        # Create missing tables if needed
        self.create_missing_tables()
        
        # Get question IDs
        question_ids = self.get_question_ids()
        if not question_ids:
            return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if clear_existing:
                print("\n🗑️  Clearing existing synthetic data...")
                # Delete synthetic responses
                cursor.execute("""
                    DELETE FROM responses 
                    WHERE username LIKE 'synthetic_user_%'
                """)
                # Delete synthetic users
                cursor.execute("""
                    DELETE FROM users 
                    WHERE username LIKE 'synthetic_user_%'
                """)
                conn.commit()
                print("✅ Cleared existing synthetic data")
            
            print(f"\n🚀 Generating {self.num_users} synthetic users...")
            print(f"   Each user will have {self.num_responses_per_user} test session(s)")
            print(f"   Found {len(question_ids)} questions in question_bank")
            
            # Progress bar
            pbar = tqdm(total=self.num_users, desc="Generating users")
            
            total_responses = 0
            
            for user_idx in range(1, self.num_users + 1):
                # Generate demographics
                demos = self.generate_demographics()
                pattern = self.generate_emotional_pattern()
                
                # Create username
                username = f'synthetic_user_{user_idx:04d}'
                
                # Calculate total score based on pattern
                pattern_config = self.emotional_patterns[pattern]
                total_score = random.randint(*pattern_config['eq_score_range'])
                
                # Insert user
                cursor.execute("""
                    INSERT INTO users (username, total_score, age)
                    VALUES (?, ?, ?)
                """, (username, total_score, demos['age']))
                
                # Generate test sessions
                for session_num in range(self.num_responses_per_user):
                    timestamp = self.faker.date_time_between(
                        start_date=self.start_date, 
                        end_date=self.end_date
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Generate responses for all questions
                    responses = self.generate_responses(pattern, question_ids)
                    
                    # Insert each response
                    for q_id, response_data in responses.items():
                        cursor.execute("""
                            INSERT INTO responses 
                            (username, question_id, response_value, age_group, timestamp)
                            VALUES (?, ?, ?, ?, ?)
                        """, (username, q_id, response_data['score'], 
                              demos['age_group'], timestamp))
                        total_responses += 1
                
                pbar.update(1)
                
                # Commit in batches
                if user_idx % 20 == 0:
                    conn.commit()
            
            pbar.close()
            conn.commit()
            
            print(f"\n✅ Synthetic data generation complete!")
            print(f"   • Users created: {self.num_users}")
            print(f"   • Test sessions: {self.num_users * self.num_responses_per_user}")
            print(f"   • Responses: {total_responses}")
            print(f"   • Total records: {total_responses + self.num_users}")
            
            # Show summary
            cursor.execute("SELECT COUNT(*) FROM users WHERE username LIKE 'synthetic_user_%'")
            synth_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM responses WHERE username LIKE 'synthetic_user_%'")
            synth_responses = cursor.fetchone()[0]
            
            print(f"\n📊 Verification:")
            print(f"   • Synthetic users in DB: {synth_users}")
            print(f"   • Synthetic responses in DB: {synth_responses}")
            
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"\n❌ Error generating synthetic data: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            conn.close()
    
    def generate_analytics_sample(self, output_file='synthetic_analytics_sample.csv'):
        """
        Generate a CSV sample for immediate analytics testing
        without inserting into database
        """
        import pandas as pd
        
        print(f"\n📁 Generating analytics sample CSV: {output_file}")
        
        data = []
        for user_id in tqdm(range(1, self.num_users + 1), desc="Creating sample data"):
            demos = self.generate_demographics()
            pattern = self.generate_emotional_pattern()
            
            # Generate multiple test sessions per user
            for session_num in range(self.num_responses_per_user):
                test_date = self.faker.date_time_between(
                    start_date=self.start_date, 
                    end_date=self.end_date
                )
                
                # Simulate responses for 10 sample questions
                responses = {}
                for q_id in range(1, 11):
                    pattern_config = self.emotional_patterns[pattern]
                    choices = list(pattern_config['response_bias'].keys())
                    weights = list(pattern_config['response_bias'].values())
                    response = random.choices(choices, weights=weights, k=1)[0]
                    score_map = {'Never': 1, 'Sometimes': 2, 'Often': 3, 'Always': 4}
                    responses[f'Q{q_id}'] = score_map[response]
                
                avg_response_score = np.mean(list(responses.values()))
                eq_score = self.calculate_eq_score(
                    {k: {'score': v} for k, v in responses.items()},
                    pattern
                )
                
                row = {
                    'user_id': f'synth_{user_id:04d}',
                    'age': demos['age'],
                    'age_group': demos['age_group'],
                    'occupation': demos['occupation'],
                    'location': demos['location'],
                    'eq_pattern': pattern,
                    'test_date': test_date.strftime('%Y-%m-%d'),
                    'eq_score': eq_score,
                    'avg_response_score': round(avg_response_score, 2),
                    'test_session': session_num + 1
                }
                
                # Add individual question scores
                for q_num, score in responses.items():
                    row[q_num] = score
                
                data.append(row)
        
        df = pd.DataFrame(data)
        output_path = Path(__file__).parent.parent / output_file
        df.to_csv(output_path, index=False)
        
        print(f"✅ Sample CSV generated: {output_path}")
        print(f"   • Rows: {len(df)}")
        print(f"   • Columns: {len(df.columns)}")
        
        return df

def main():
    """Main function to run the synthetic data generator"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate synthetic data for SOUL_SENSE_EXAM analytics testing'
    )
    parser.add_argument(
        '--users', '-u', type=int, default=50,
        help='Number of synthetic users to generate (default: 50)'
    )
    parser.add_argument(
        '--sessions', '-s', type=int, default=1,
        help='Number of test sessions per user (default: 1)'
    )
    parser.add_argument(
        '--clear', '-c', action='store_true',
        help='Clear existing synthetic data before generating'
    )
    parser.add_argument(
        '--sample', action='store_true',
        help='Generate CSV sample only (does not modify database)'
    )
    parser.add_argument(
        '--output', '-o', default='synthetic_analytics_sample.csv',
        help='Output CSV filename for sample (default: synthetic_analytics_sample.csv)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SOUL SENSE - Synthetic Data Generator")
    print("FIXED VERSION - Matches your database schema")
    print("=" * 60)
    
    # Initialize generator
    generator = SyntheticDataGenerator(
        num_users=args.users,
        num_responses_per_user=args.sessions
    )
    
    if args.sample:
        # Generate CSV sample only
        generator.generate_analytics_sample(output_file=args.output)
    else:
        # Generate and insert into database
        success = generator.insert_synthetic_data(clear_existing=args.clear)
        
        if success:
            print("\n📊 Data Distribution Summary:")
            print("-" * 30)
            
            # Quick analysis
            patterns = ['high_eq', 'medium_eq', 'low_eq']
            estimated_dist = [0.3, 0.5, 0.2]
            
            for pattern, percent in zip(patterns, estimated_dist):
                count = int(args.users * percent)
                score_range = generator.emotional_patterns[pattern]['eq_score_range']
                print(f"• {pattern.replace('_', ' ').title()}:")
                print(f"  Estimated users: {count} ({percent*100:.0f}%)")
                print(f"  EQ score range: {score_range[0]}-{score_range[1]}")
            
            print("\n💡 Next steps:")
            print("1. Test with analytics: python analytics_dashboard.py")
            print("2. View data: Check db/soulsense.db with DB Browser")
            print("3. Generate more: python -m scripts.generate_synthetic_data --users 200")
            print("4. Quick CSV: python -m scripts.generate_synthetic_data --sample")
    
    print("=" * 60)

if __name__ == '__main__':
    # Install required packages if not already installed
    required_packages = ['faker', 'tqdm', 'numpy', 'pandas']
    
    try:
        main()
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("\nInstall required packages with:")
        print(f"pip install {' '.join(required_packages)}")
        print("\nOr add them to requirements.txt and run:")
        print("pip install -r requirements.txt")
        sys.exit(1)
