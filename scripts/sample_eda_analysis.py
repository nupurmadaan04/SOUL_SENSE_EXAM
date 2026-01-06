"""
Sample EDA Analysis Script

This script demonstrates a complete EDA workflow using the exported
emotional health data with enhanced age group segmentation.

Prerequisites:
    pip install pandas matplotlib seaborn (optional)

Usage:
    python scripts/sample_eda_analysis.py
"""

import os
import sys

def check_dependencies():
    """Check if required libraries are available."""
    try:
        import pandas as pd
        return True, pd
    except ImportError:
        return False, None


def analyze_with_pandas():
    """Perform analysis using pandas."""
    import pandas as pd
    
    print("\n" + "="*70)
    print("EMOTIONAL HEALTH DATA ANALYSIS")
    print("="*70)
    
    # Check if data files exist
    if not os.path.exists('data/emotions_eda.csv'):
        print("\n⚠ Data not found. Please export first:")
        print("  python scripts/eda_export.py --format csv --output data/emotions_eda.csv")
        return
    
    # Load data
    print("\n1. Loading Data...")
    df = pd.read_csv('data/emotions_eda.csv')
    print(f"   ✓ Loaded {len(df)} records")
    
    # Basic statistics
    print("\n2. Dataset Overview:")
    print("-" * 70)
    print(df.info())
    
    # Age distribution
    print("\n3. Age Distribution:")
    print("-" * 70)
    if 'age' in df.columns:
        print(df['age'].describe())
    
    # Age group analysis (detailed)
    print("\n4. Emotional Scores by Detailed Age Group:")
    print("-" * 70)
    if 'age_group_detailed' in df.columns and 'total_score' in df.columns:
        age_analysis = df.groupby('age_group_detailed')['total_score'].agg([
            ('count', 'count'),
            ('mean', 'mean'),
            ('std', 'std'),
            ('min', 'min'),
            ('max', 'max')
        ]).round(2)
        print(age_analysis)
    
    # Age group analysis (legacy)
    print("\n5. Emotional Scores by Legacy Age Group:")
    print("-" * 70)
    if 'age_group_legacy' in df.columns and 'total_score' in df.columns:
        legacy_analysis = df.groupby('age_group_legacy')['total_score'].agg([
            ('count', 'count'),
            ('mean', 'mean'),
            ('std', 'std')
        ]).round(2)
        print(legacy_analysis)
    
    # Load aggregates if available
    if os.path.exists('data/emotions_eda_aggregates.csv'):
        print("\n6. Pre-computed Aggregates by Age Group:")
        print("-" * 70)
        agg_df = pd.read_csv('data/emotions_eda_aggregates.csv')
        print(agg_df.to_string(index=False))
    
    # Correlation analysis
    print("\n7. Correlation Analysis:")
    print("-" * 70)
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    if len(numeric_cols) > 1:
        print(df[numeric_cols].corr().round(3))
    
    # Summary insights
    print("\n8. Key Insights:")
    print("-" * 70)
    
    if 'age_group_detailed' in df.columns and 'total_score' in df.columns:
        group_means = df.groupby('age_group_detailed')['total_score'].mean()
        
        if len(group_means) > 0:
            highest_group = group_means.idxmax()
            lowest_group = group_means.idxmin()
            
            print(f"   ✓ Highest avg score: {highest_group} ({group_means[highest_group]:.2f})")
            print(f"   ✓ Lowest avg score: {lowest_group} ({group_means[lowest_group]:.2f})")
            
            age_counts = df.groupby('age_group_detailed').size()
            most_common = age_counts.idxmax()
            print(f"   ✓ Most represented: {most_common} ({age_counts[most_common]} records)")
    
    print("\n")


def analyze_without_pandas():
    """Perform basic analysis using standard library only."""
    import csv
    from collections import defaultdict
    
    print("\n" + "="*70)
    print("EMOTIONAL HEALTH DATA ANALYSIS (Basic)")
    print("="*70)
    
    if not os.path.exists('data/emotions_eda.csv'):
        print("\n⚠ Data not found. Please export first:")
        print("  python scripts/eda_export.py --format csv --output data/emotions_eda.csv")
        return
    
    # Read and analyze
    print("\n1. Reading data...")
    
    data = []
    with open('data/emotions_eda.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    
    print(f"   ✓ Loaded {len(data)} records")
    
    # Group by age
    print("\n2. Grouping by detailed age groups...")
    age_groups = defaultdict(list)
    
    for row in data:
        age_group = row.get('age_group_detailed', 'unknown')
        try:
            score = int(row.get('total_score', 0))
            age_groups[age_group].append(score)
        except (ValueError, TypeError):
            pass
    
    # Calculate statistics
    print("\n3. Statistics by Age Group:")
    print("-" * 70)
    print(f"   {'Age Group':<15} {'Count':<10} {'Avg Score':<12} {'Min':<8} {'Max':<8}")
    print("   " + "-" * 66)
    
    for group in sorted(age_groups.keys()):
        scores = age_groups[group]
        if scores:
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)
            print(f"   {group:<15} {len(scores):<10} {avg_score:<12.2f} {min_score:<8} {max_score:<8}")
    
    print("\n")


def create_visualizations():
    """Create visualizations if matplotlib is available."""
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n⚠ Matplotlib not available. Skipping visualizations.")
        print("  Install with: pip install matplotlib")
        return
    
    if not os.path.exists('data/emotions_eda_aggregates.csv'):
        print("\n⚠ Aggregates file not found. Skipping visualizations.")
        return
    
    print("\n" + "="*70)
    print("CREATING VISUALIZATIONS")
    print("="*70)
    
    # Load aggregates
    agg_df = pd.read_csv('data/emotions_eda_aggregates.csv')
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Emotional Health Analysis by Age Group', fontsize=16, fontweight='bold')
    
    # 1. Average scores by age group
    ax1 = axes[0, 0]
    agg_df.plot(x='age_group', y='avg_total_score', kind='bar', ax=ax1, color='steelblue')
    ax1.set_title('Average Emotional Score by Age Group')
    ax1.set_xlabel('Age Group')
    ax1.set_ylabel('Average Score')
    ax1.legend().remove()
    ax1.tick_params(axis='x', rotation=45)
    
    # 2. User count by age group
    ax2 = axes[0, 1]
    agg_df.plot(x='age_group', y='user_count', kind='bar', ax=ax2, color='coral')
    ax2.set_title('User Distribution by Age Group')
    ax2.set_xlabel('Age Group')
    ax2.set_ylabel('Number of Users')
    ax2.legend().remove()
    ax2.tick_params(axis='x', rotation=45)
    
    # 3. Total tests by age group
    ax3 = axes[1, 0]
    agg_df.plot(x='age_group', y='total_tests', kind='bar', ax=ax3, color='lightgreen')
    ax3.set_title('Total Tests by Age Group')
    ax3.set_xlabel('Age Group')
    ax3.set_ylabel('Number of Tests')
    ax3.legend().remove()
    ax3.tick_params(axis='x', rotation=45)
    
    # 4. Score range (min-max) by age group
    ax4 = axes[1, 1]
    agg_df.plot(x='age_group', y=['min_score', 'max_score'], kind='bar', ax=ax4)
    ax4.set_title('Score Range by Age Group')
    ax4.set_xlabel('Age Group')
    ax4.set_ylabel('Score')
    ax4.legend(['Min Score', 'Max Score'])
    ax4.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    # Save figure
    output_path = 'data/age_group_analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Visualizations saved to: {output_path}")
    
    # Try to display
    try:
        plt.show()
    except:
        print("  (Could not display plot, but file was saved)")


def main():
    """Main analysis workflow."""
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*20 + "EMOTIONAL HEALTH EDA" + " "*29 + "║")
    print("╚" + "═"*68 + "╝")
    
    # Check for pandas
    has_pandas, pd = check_dependencies()
    
    if has_pandas:
        print("\n✓ Using pandas for enhanced analysis")
        analyze_with_pandas()
        
        # Try to create visualizations
        create_visualizations()
    else:
        print("\n⚠ Pandas not available. Using basic analysis.")
        print("  For enhanced analysis, install: pip install pandas matplotlib")
        analyze_without_pandas()
    
    print("="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nNext Steps:")
    print("  • Review the statistics above")
    print("  • Check data/age_group_analysis.png for visualizations")
    print("  • Use the exported CSV files for deeper analysis")
    print("  • Consider segmenting by age groups for targeted insights")
    print("\n")


if __name__ == '__main__':
    main()
