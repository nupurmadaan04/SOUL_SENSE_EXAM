"""
EDA Export Utility for SoulSense Emotional Data Pipeline

This module provides functionality to export emotional health data
in a structured format ready for Exploratory Data Analysis (EDA).

Features:
    - Backward-compatible with existing data schema
    - Adds detailed age group tagging without breaking existing columns
    - Exports data in multiple formats (CSV, JSON)
    - Preserves data integrity and referential relationships
    - Handles missing/invalid age data gracefully

Usage:
    python scripts/eda_export.py --format csv --output data/eda_export.csv
    python scripts/eda_export.py --format json --output data/eda_export.json
    python scripts/eda_export.py --backfill  # Backfill detailed_age_group for existing records
"""

import sqlite3
import csv
import json
import argparse
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import compute_age_group, compute_detailed_age_group
from app.models import ensure_scores_schema, ensure_responses_schema

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/eda_export.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EDAExporter:
    """Export emotional health data for Exploratory Data Analysis."""
    
    def __init__(self, db_path: str = "soulsense_db"):
        """
        Initialize the EDA exporter.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def __enter__(self):
        """Context manager entry."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self.cursor = self.conn.cursor()
        
        # Ensure schema is up to date
        ensure_scores_schema(self.cursor)
        ensure_responses_schema(self.cursor)
        self.conn.commit()
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.conn:
            self.conn.close()
    
    def backfill_detailed_age_groups(self) -> Dict[str, int]:
        """
        Backfill detailed_age_group for existing records.
        
        This ensures all historical data has the new age group categorization
        without breaking existing 'age_group' column values.
        
        Returns:
            Dict with counts of updated records per table
        """
        logger.info("Starting backfill of detailed_age_group...")
        results = {}
        
        # Backfill scores table
        self.cursor.execute("""
            SELECT id, age FROM scores 
            WHERE detailed_age_group IS NULL OR detailed_age_group = ''
        """)
        scores_to_update = self.cursor.fetchall()
        
        for row in scores_to_update:
            detailed_group = compute_detailed_age_group(row['age'])
            self.cursor.execute(
                "UPDATE scores SET detailed_age_group = ? WHERE id = ?",
                (detailed_group, row['id'])
            )
        
        results['scores_updated'] = len(scores_to_update)
        logger.info(f"Updated {len(scores_to_update)} score records")
        
        # Backfill responses table (infer age from scores if needed)
        self.cursor.execute("""
            SELECT r.id, r.username, r.timestamp, s.age
            FROM responses r
            LEFT JOIN scores s ON r.username = s.username 
                AND date(r.timestamp) = date(s.id)
            WHERE r.detailed_age_group IS NULL OR r.detailed_age_group = ''
        """)
        responses_to_update = self.cursor.fetchall()
        
        for row in responses_to_update:
            detailed_group = compute_detailed_age_group(row['age'])
            self.cursor.execute(
                "UPDATE responses SET detailed_age_group = ? WHERE id = ?",
                (detailed_group, row['id'])
            )
        
        results['responses_updated'] = len(responses_to_update)
        logger.info(f"Updated {len(responses_to_update)} response records")
        
        self.conn.commit()
        logger.info("Backfill completed successfully")
        
        return results
    
    def get_eda_dataset(self) -> List[Dict[str, Any]]:
        """
        Retrieve comprehensive dataset for EDA.
        
        Returns enriched data combining scores, responses, and demographic info
        with both legacy and detailed age groups for backward compatibility.
        
        Returns:
            List of dictionaries containing the complete dataset
        """
        logger.info("Retrieving EDA dataset...")
        
        # Check which columns exist in scores table
        self.cursor.execute("PRAGMA table_info(scores)")
        cols = [c[1] for c in self.cursor.fetchall()]
        has_normalized = 'normalized_score' in cols
        has_num_questions = 'num_questions' in cols
        
        # Build query based on available columns
        normalized_field = 's.normalized_score,' if has_normalized else ''
        num_q_field = 's.num_questions,' if has_num_questions else ''
        
        query = f"""
        SELECT 
            s.id as score_id,
            s.username,
            s.age,
            s.detailed_age_group,
            s.total_score,
            {normalized_field}
            {num_q_field}
            r.question_id,
            r.response_value,
            r.age_group as legacy_age_group,
            r.timestamp
        FROM scores s
        LEFT JOIN responses r ON s.username = r.username
        ORDER BY s.id, r.question_id
        """
        
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        
        dataset = []
        for row in rows:
            record = {
                'score_id': row['score_id'],
                'username': row['username'],
                'age': row['age'],
                'age_group_legacy': compute_age_group(row['age']),  # Backward compatible
                'age_group_detailed': row['detailed_age_group'] or compute_detailed_age_group(row['age']),
                'total_score': row['total_score'],
                'question_id': row['question_id'],
                'response_value': row['response_value'],
                'timestamp': row['timestamp'],
                'export_timestamp': datetime.now().isoformat()
            }
            
            # Add optional fields if they exist
            if has_normalized:
                record['normalized_score'] = row['normalized_score']
            if has_num_questions:
                record['num_questions'] = row['num_questions']
            
            dataset.append(record)
        
        logger.info(f"Retrieved {len(dataset)} records for EDA")
        return dataset
    
    def get_aggregated_by_age_group(self) -> List[Dict[str, Any]]:
        """
        Get aggregated emotional metrics by detailed age group.
        
        Returns:
            List of aggregated statistics per age group
        """
        logger.info("Computing aggregated metrics by age group...")
        
        # Check which columns exist in scores table
        self.cursor.execute("PRAGMA table_info(scores)")
        cols = [c[1] for c in self.cursor.fetchall()]
        has_normalized = 'normalized_score' in cols
        
        # Build query based on available columns
        score_field = 'normalized_score' if has_normalized else 'total_score'
        
        query = f"""
        SELECT 
            detailed_age_group,
            COUNT(DISTINCT username) as user_count,
            COUNT(*) as total_tests,
            AVG(total_score) as avg_total_score,
            {'AVG(normalized_score) as avg_normalized_score,' if has_normalized else ''}
            MIN(total_score) as min_score,
            MAX(total_score) as max_score,
            AVG(age) as avg_age
        FROM scores
        WHERE detailed_age_group IS NOT NULL AND detailed_age_group != 'unknown'
        GROUP BY detailed_age_group
        ORDER BY 
            CASE detailed_age_group
                WHEN '<13' THEN 1
                WHEN '13-17' THEN 2
                WHEN '18-24' THEN 3
                WHEN '25-34' THEN 4
                WHEN '35-44' THEN 5
                WHEN '45-54' THEN 6
                WHEN '55-64' THEN 7
                WHEN '65+' THEN 8
                ELSE 9
            END
        """
        
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        
        aggregated = []
        for row in rows:
            result = {
                'age_group': row['detailed_age_group'],
                'user_count': row['user_count'],
                'total_tests': row['total_tests'],
                'avg_total_score': round(row['avg_total_score'], 2) if row['avg_total_score'] else None,
                'min_score': row['min_score'],
                'max_score': row['max_score'],
                'avg_age': round(row['avg_age'], 1) if row['avg_age'] else None
            }
            
            # Only add normalized score if it exists
            if has_normalized:
                result['avg_normalized_score'] = round(row['avg_normalized_score'], 2) if row['avg_normalized_score'] else None
            
            aggregated.append(result)
        
        logger.info(f"Computed aggregates for {len(aggregated)} age groups")
        return aggregated
    
    def export_to_csv(self, output_path: str, include_aggregates: bool = True):
        """
        Export data to CSV format.
        
        Args:
            output_path: Path for the output CSV file
            include_aggregates: Whether to create a separate aggregates file
        """
        logger.info(f"Exporting to CSV: {output_path}")
        
        # Export detailed dataset
        dataset = self.get_eda_dataset()
        
        if dataset:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            
            output_dir = os.path.dirname(output_path)

            if output_dir and not os.path.exists(output_dir):
                raise FileNotFoundError(
                    f"Output directory does not exist: {output_dir}"
                )

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
                writer.writeheader()
                writer.writerows(dataset)
            
            logger.info(f"Exported {len(dataset)} records to {output_path}")
        else:
            logger.warning("No data to export")
        
        # Export aggregates if requested
        if include_aggregates:
            agg_path = output_path.replace('.csv', '_aggregates.csv')
            aggregated = self.get_aggregated_by_age_group()
            
            if aggregated:
                with open(agg_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=aggregated[0].keys())
                    writer.writeheader()
                    writer.writerows(aggregated)
                
                logger.info(f"Exported aggregates to {agg_path}")
    
    def export_to_json(self, output_path: str, include_aggregates: bool = True):
        """
        Export data to JSON format.
        
        Args:
            output_path: Path for the output JSON file
            include_aggregates: Whether to include aggregates in the output
        """
        logger.info(f"Exporting to JSON: {output_path}")
        
        dataset = self.get_eda_dataset()
        
        output = {
            'metadata': {
                'export_timestamp': datetime.now().isoformat(),
                'record_count': len(dataset),
                'database': self.db_path
            },
            'data': dataset
        }
        
        if include_aggregates:
            output['aggregates_by_age_group'] = self.get_aggregated_by_age_group()
        
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported to {output_path}")
    
    def print_schema_info(self):
        """Print information about the current database schema."""
        print("\n" + "="*70)
        print("DATABASE SCHEMA INFORMATION")
        print("="*70)
        
        # Scores table
        self.cursor.execute("PRAGMA table_info(scores)")
        scores_cols = self.cursor.fetchall()
        print("\nScores Table Columns:")
        for col in scores_cols:
            print(f"  - {col['name']:<25} {col['type']:<10}")
        
        # Responses table
        self.cursor.execute("PRAGMA table_info(responses)")
        responses_cols = self.cursor.fetchall()
        print("\nResponses Table Columns:")
        for col in responses_cols:
            print(f"  - {col['name']:<25} {col['type']:<10}")
        
        # Data counts
        self.cursor.execute("SELECT COUNT(*) as cnt FROM scores")
        scores_count = self.cursor.fetchone()['cnt']
        
        self.cursor.execute("SELECT COUNT(*) as cnt FROM responses")
        responses_count = self.cursor.fetchone()['cnt']
        
        print(f"\nData Counts:")
        print(f"  - Scores: {scores_count}")
        print(f"  - Responses: {responses_count}")
        
        print("="*70 + "\n")


def main():
    """Main entry point for the EDA export utility."""
    parser = argparse.ArgumentParser(
        description='Export SoulSense emotional data for EDA',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Export to CSV:
    python scripts/eda_export.py --format csv --output data/eda_export.csv
  
  Export to JSON:
    python scripts/eda_export.py --format json --output data/eda_export.json
  
  Backfill detailed age groups:
    python scripts/eda_export.py --backfill
  
  Show schema information:
    python scripts/eda_export.py --show-schema
        """
    )
    
    parser.add_argument(
        '--db',
        default='soulsense_db',
        help='Path to SQLite database (default: soulsense_db)'
    )
    parser.add_argument(
        '--format',
        choices=['csv', 'json'],
        help='Export format'
    )
    parser.add_argument(
        '--output',
        help='Output file path'
    )
    parser.add_argument(
        '--backfill',
        action='store_true',
        help='Backfill detailed_age_group for existing records'
    )
    parser.add_argument(
        '--show-schema',
        action='store_true',
        help='Display database schema information'
    )
    parser.add_argument(
        '--no-aggregates',
        action='store_true',
        help='Do not include aggregate statistics in export'
    )
    
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    try:
        with EDAExporter(args.db) as exporter:
            
            if args.show_schema:
                exporter.print_schema_info()
            
            if args.backfill:
                results = exporter.backfill_detailed_age_groups()
                print(f"\nBackfill Results:")
                print(f"  Scores updated: {results['scores_updated']}")
                print(f"  Responses updated: {results['responses_updated']}")
            
            if args.format and args.output:
                include_agg = not args.no_aggregates
                
                if args.format == 'csv':
                    exporter.export_to_csv(args.output, include_aggregates=include_agg)
                elif args.format == 'json':
                    exporter.export_to_json(args.output, include_aggregates=include_agg)
                
                print(f"\n✓ Export completed successfully: {args.output}")
            
            elif not args.backfill and not args.show_schema:
                parser.print_help()
    
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
