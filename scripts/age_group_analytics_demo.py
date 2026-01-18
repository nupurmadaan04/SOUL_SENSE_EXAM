"""
Age Group Analytics Demonstration

This script demonstrates how to use the enhanced age group tagging
for emotional trend analysis across different demographic segments.

Features demonstrated:
    - Data retrieval with detailed age groups
    - Trend analysis by age cohort
    - Backward compatibility with legacy code
    - Visualization-ready data formatting
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.eda_export import EDAExporter
from app.utils import compute_age_group, compute_detailed_age_group
import json


def demonstrate_age_group_tagging():
    """Demonstrate the age group tagging functionality."""
    print("="*70)
    print("AGE GROUP TAGGING DEMONSTRATION")
    print("="*70)
    
    print("\n1. Legacy Age Groups (backward compatible):")
    print("-" * 50)
    test_ages = [5, 15, 22, 30, 40, 55, 70, None]
    
    for age in test_ages:
        legacy = compute_age_group(age)
        detailed = compute_detailed_age_group(age)
        age_str = str(age) if age is not None else "None"
        print(f"  Age {age_str:>4} → Legacy: {legacy:<10} | Detailed: {detailed:<10}")
    
    print("\n2. Detailed Age Groups (enhanced analytics):")
    print("-" * 50)
    print("  Age Range  | Group Category")
    print("  " + "-" * 46)
    categories = [
        ("< 13", "Children"),
        ("13-17", "Adolescents"),
        ("18-24", "Young Adults"),
        ("25-34", "Adults"),
        ("35-44", "Middle Age"),
        ("45-54", "Mature Adults"),
        ("55-64", "Pre-Senior"),
        ("65+", "Seniors"),
    ]
    for range_str, category in categories:
        print(f"  {range_str:<10} | {category}")
    
    print("\n")


def analyze_emotional_trends():
    """Analyze emotional trends by age group."""
    print("="*70)
    print("EMOTIONAL TRENDS BY AGE GROUP")
    print("="*70)
    
    # Get database path from config
    from app.config import DB_PATH
    
    if not os.path.exists(DB_PATH):
        print("\n⚠ No database found. Please run the application first to generate data.")
        return
    
    print(f"\nAnalyzing database: {DB_PATH}")
    
    with EDAExporter(DB_PATH) as exporter:
        # First, ensure all records have detailed age groups
        print("\n1. Ensuring data integrity...")
        results = exporter.backfill_detailed_age_groups()
        print(f"   ✓ Updated {results['scores_updated']} score records")
        print(f"   ✓ Updated {results['responses_updated']} response records")
        
        # Get aggregated statistics
        print("\n2. Computing aggregated metrics by age group...")
        aggregates = exporter.get_aggregated_by_age_group()
        
        if aggregates:
            print("\n   Age Group Emotional Intelligence Summary:")
            print("   " + "-" * 66)
            
            # Check if normalized_score is available
            has_normalized = 'avg_normalized_score' in aggregates[0]
            score_label = 'Avg Normalized' if has_normalized else 'Avg Total'
            
            print(f"   {'Group':<10} {'Users':<8} {'Tests':<8} {score_label:<12} {'Score Range':<15}")
            print("   " + "-" * 66)
            
            for agg in aggregates:
                group = agg['age_group']
                users = agg['user_count']
                tests = agg['total_tests']
                
                # Use normalized score if available, otherwise total score
                if has_normalized:
                    avg = f"{agg['avg_normalized_score']:.1f}" if agg.get('avg_normalized_score') else "N/A"
                else:
                    avg = f"{agg['avg_total_score']:.1f}" if agg.get('avg_total_score') else "N/A"
                
                score_range = f"{agg['min_score']}-{agg['max_score']}" if agg['min_score'] else "N/A"
                
                print(f"   {group:<10} {users:<8} {tests:<8} {avg:<12} {score_range:<15}")
            
            print("\n3. Key Insights:")
            print("   " + "-" * 66)
            
            # Find highest and lowest performing groups
            score_key = 'avg_normalized_score' if has_normalized else 'avg_total_score'
            valid_groups = [a for a in aggregates if a.get(score_key)]
            
            if valid_groups:
                highest = max(valid_groups, key=lambda x: x[score_key])
                lowest = min(valid_groups, key=lambda x: x[score_key])
                
                print(f"   ✓ Highest EQ Group: {highest['age_group']} "
                      f"(avg: {highest[score_key]:.1f})")
                print(f"   ✓ Lowest EQ Group: {lowest['age_group']} "
                      f"(avg: {lowest[score_key]:.1f})")
                
                # Engagement insights
                most_engaged = max(aggregates, key=lambda x: x['total_tests'])
                print(f"   ✓ Most Engaged: {most_engaged['age_group']} "
                      f"({most_engaged['total_tests']} tests)")
        else:
            print("   ℹ No age group data available yet.")
    
    print("\n")


def demonstrate_data_export():
    """Demonstrate data export for EDA tools."""
    print("="*70)
    print("DATA EXPORT FOR EDA")
    print("="*70)
    
    from app.config import DB_PATH
    
    if not os.path.exists(DB_PATH):
        print("\n⚠ No database found.")
        return
    
    print(f"\nUsing database: {DB_PATH}")
    
    with EDAExporter(DB_PATH) as exporter:
        dataset = exporter.get_eda_dataset()
        
        if dataset:
            print(f"\n✓ Retrieved {len(dataset)} records for analysis")
            
            # Show sample record structure
            if dataset:
                print("\nSample Record Structure:")
                print("-" * 70)
                sample = dataset[0]
                for key, value in sample.items():
                    print(f"  {key:<25} : {value}")
                
                # Show field descriptions
                print("\nField Descriptions:")
                print("-" * 70)
                fields = {
                    'score_id': 'Unique identifier for test session',
                    'username': 'User identifier',
                    'age': 'User age (numeric)',
                    'age_group_legacy': 'Legacy category (child/adult/senior)',
                    'age_group_detailed': 'Detailed category (13-17, 18-24, etc.)',
                    'total_score': 'Raw emotion score',
                    'normalized_score': 'Normalized EQ score (0-80)',
                    'question_id': 'Question identifier',
                    'response_value': 'User response (1-4)',
                    'timestamp': 'Response timestamp',
                    'export_timestamp': 'Data export timestamp'
                }
                
                for field, desc in fields.items():
                    print(f"  {field:<25} : {desc}")
        else:
            print("\n⚠ No data available for export")
    
    print("\n")


def show_export_commands():
    """Show example export commands."""
    print("="*70)
    print("EXPORT COMMANDS FOR EDA TOOLS")
    print("="*70)
    
    commands = [
        ("Export to CSV", 
         "python scripts/eda_export.py --format csv --output data/emotions_eda.csv"),
        
        ("Export to JSON", 
         "python scripts/eda_export.py --format json --output data/emotions_eda.json"),
        
        ("Backfill age groups", 
         "python scripts/eda_export.py --backfill"),
        
        ("Show database schema", 
         "python scripts/eda_export.py --show-schema"),
        
        ("Export without aggregates", 
         "python scripts/eda_export.py --format csv --output data/raw.csv --no-aggregates"),
    ]
    
    print("\nCommon Export Operations:")
    print("-" * 70)
    for i, (desc, cmd) in enumerate(commands, 1):
        print(f"\n{i}. {desc}:")
        print(f"   {cmd}")
    
    print("\n")


def show_integration_examples():
    """Show how to integrate with existing code."""
    print("="*70)
    print("INTEGRATION WITH EXISTING CODE")
    print("="*70)
    
    print("\nBackward Compatibility:")
    print("-" * 70)
    print("""
  # Legacy code continues to work unchanged:
  from app.utils import compute_age_group
  
  age_group = compute_age_group(user_age)
  # Returns: 'child', 'adult', 'senior', or 'unknown'
  
  # Existing code using these categories is NOT affected
  if age_group == 'adult':
      # This logic continues to work
      pass
    """)
    
    print("\nEnhanced Analytics:")
    print("-" * 70)
    print("""
  # New code can use detailed groupings:
  from app.utils import compute_detailed_age_group
  
  detailed_group = compute_detailed_age_group(user_age)
  # Returns: '<13', '13-17', '18-24', '25-34', '35-44', 
  #          '45-54', '55-64', '65+', or 'unknown'
  
  # Enables age-cohort analysis:
  emotional_trends_by_cohort = df.groupby('age_group_detailed').agg({
      'normalized_score': ['mean', 'std', 'min', 'max'],
      'username': 'count'
  })
    """)
    
    print("\nDatabase Schema:")
    print("-" * 70)
    print("""
  Scores Table:
    - id, username, age          (existing fields)
    - total_score, normalized_score, num_questions  (existing)
    - detailed_age_group         (NEW - added safely)
  
  Responses Table:
    - id, username, question_id, response_value  (existing)
    - age_group                  (existing - legacy format)
    - detailed_age_group         (NEW - added safely)
    - timestamp                  (existing)
  
  ✓ All existing columns preserved
  ✓ New columns added with ALTER TABLE (safe migration)
  ✓ No data loss or breaking changes
    """)
    
    print("\n")


def main():
    """Main demonstration function."""
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*15 + "SOULSENSE AGE GROUP ANALYTICS" + " "*24 + "║")
    print("║" + " "*15 + "Enhanced Demographic Analysis" + " "*24 + "║")
    print("╚" + "═"*68 + "╝")
    print("\n")
    
    # Run demonstrations
    demonstrate_age_group_tagging()
    analyze_emotional_trends()
    demonstrate_data_export()
    show_export_commands()
    show_integration_examples()
    
    print("="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nNext Steps:")
    print("  1. Run: python scripts/eda_export.py --backfill")
    print("  2. Export: python scripts/eda_export.py --format csv --output data/eda.csv")
    print("  3. Analyze the exported data using pandas, matplotlib, or your EDA tool")
    print("\n")


if __name__ == '__main__':
    main()
