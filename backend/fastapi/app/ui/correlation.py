# app/ui/correlation.py
import tkinter as tk
from tkinter import ttk, scrolledtext
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# App imports
from app.models import Score, JournalEntry
from app.db import get_session, safe_db_context

class CorrelationTab:
    def __init__(self, parent_frame, username):
        self.parent = parent_frame
        self.username = username
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the correlation analysis tab UI"""
        # Title
        title = tk.Label(self.parent, text="🔗 Correlation Analysis", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Description
        desc = tk.Label(self.parent, 
                       text="Analyze relationships between your EQ scores, journal sentiment, and patterns",
                       font=("Arial", 11), wraplength=550)
        desc.pack(pady=5)
        
        # Control Frame
        control_frame = tk.Frame(self.parent)
        control_frame.pack(pady=10, fill=tk.X)
        
        # Analyze button
        tk.Button(control_frame, text="Run Correlation Analysis", 
                 command=self.run_analysis, bg="#4CAF50", fg="white",
                 font=("Arial", 11, "bold")).pack(pady=5)
        
        # Results area
        self.results_text = scrolledtext.ScrolledText(self.parent, 
                                                     wrap=tk.WORD, 
                                                     height=20,
                                                     font=("Arial", 11))
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Visualization frame
        self.viz_frame = tk.Frame(self.parent)
        self.viz_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def run_analysis(self):
        """Run correlation analysis"""
        try:
            self.results_text.delete(1.0, tk.END)

            # Clear previous visualization
            for widget in self.viz_frame.winfo_children():
                widget.destroy()

            # Fetch data
            with safe_db_context() as session:
                scores_data = session.query(Score).filter(
                    Score.username == self.username
                ).order_by(Score.timestamp).all()
            
            if len(scores_data) < 2:
                self.results_text.insert(tk.END, "⚠️ Need at least 2 EQ tests for correlation analysis.\n")
                return
            
            scores = [s.total_score for s in scores_data]
            
            # Start analysis
            self.results_text.insert(tk.END, "📊 **CORRELATION ANALYSIS RESULTS**\n")
            self.results_text.insert(tk.END, "="*60 + "\n\n")
            
            # 1. Basic statistics
            self.results_text.insert(tk.END, "📈 **EQ Score Statistics:**\n")
            self.results_text.insert(tk.END, f"• Number of tests: {len(scores)}\n")
            self.results_text.insert(tk.END, f"• Average score: {np.mean(scores):.2f}/25\n")
            self.results_text.insert(tk.END, f"• Score range: {min(scores)} to {max(scores)}\n")
            self.results_text.insert(tk.END, f"• Standard deviation: {np.std(scores):.2f}\n\n")
            
            # 2. Trend analysis
            if len(scores) >= 3:
                x = np.arange(len(scores))
                z = np.polyfit(x, scores, 1)
                trend = z[0]
                
                self.results_text.insert(tk.END, "📈 **Trend Analysis:**\n")
                self.results_text.insert(tk.END, f"• Trend slope: {trend:.3f} points per test\n")
                
                if trend > 0.5:
                    self.results_text.insert(tk.END, "✅ **Strong positive trend** - Consistent improvement!\n")
                elif trend > 0.1:
                    self.results_text.insert(tk.END, "↗️ **Positive trend** - Gradual improvement\n")
                elif trend < -0.5:
                    self.results_text.insert(tk.END, "📉 **Strong negative trend** - Review strategies\n")
                elif trend < -0.1:
                    self.results_text.insert(tk.END, "↘️ **Negative trend** - Needs attention\n")
                else:
                    self.results_text.insert(tk.END, "⚖️ **Stable performance**\n")
                self.results_text.insert(tk.END, "\n")
            
            # 3. Consistency analysis
            cv = (np.std(scores) / np.mean(scores) * 100) if np.mean(scores) > 0 else 0
            
            self.results_text.insert(tk.END, "🎯 **Consistency Analysis:**\n")
            self.results_text.insert(tk.END, f"• Coefficient of variation: {cv:.1f}%\n")
            
            if cv < 15:
                self.results_text.insert(tk.END, "✅ **Excellent consistency** - Very stable scores\n")
            elif cv < 25:
                self.results_text.insert(tk.END, "👍 **Good consistency** - Reliable performance\n")
            elif cv < 35:
                self.results_text.insert(tk.END, "⚠️ **Moderate variation** - Some fluctuations\n")
            else:
                self.results_text.insert(tk.END, "🔀 **High variation** - Inconsistent performance\n")
            self.results_text.insert(tk.END, "\n")
            
            # 4. Score distribution
            self.results_text.insert(tk.END, "📊 **Score Distribution:**\n")
            score_ranges = {
                "Very Low (1-8)": len([s for s in scores if 1 <= s <= 8]),
                "Low (9-12)": len([s for s in scores if 9 <= s <= 12]),
                "Average (13-18)": len([s for s in scores if 13 <= s <= 18]),
                "Good (19-22)": len([s for s in scores if 19 <= s <= 22]),
                "Excellent (23-25)": len([s for s in scores if 23 <= s <= 25])
            }
            
            for range_name, count in score_ranges.items():
                if count > 0:
                    percentage = (count / len(scores)) * 100
                    self.results_text.insert(tk.END, f"• {range_name}: {count} tests ({percentage:.1f}%)\n")
            
            # 5. Progress analysis
            if len(scores) >= 4:
                half = len(scores) // 2
                first_half_avg = np.mean(scores[:half])
                second_half_avg = np.mean(scores[half:])
                improvement = second_half_avg - first_half_avg
                
                self.results_text.insert(tk.END, "\n📈 **Progress Analysis:**\n")
                self.results_text.insert(tk.END, f"• First {half} tests average: {first_half_avg:.2f}\n")
                self.results_text.insert(tk.END, f"• Last {len(scores)-half} tests average: {second_half_avg:.2f}\n")
                self.results_text.insert(tk.END, f"• Improvement: {improvement:+.2f} points\n")
                
                if improvement > 2:
                    self.results_text.insert(tk.END, "🎉 **Significant improvement** over time!\n")
                elif improvement > 0.5:
                    self.results_text.insert(tk.END, "📈 **Noticeable improvement**\n")
                elif improvement < -2:
                    self.results_text.insert(tk.END, "⚠️ **Significant decline** - Review approach\n")
            
            # 6. Create visualizations
            self.create_visualizations(scores)
            
            # 7. Check journal correlation if available
            with safe_db_context() as session:
                journal_data = session.query(JournalEntry).filter(
                    JournalEntry.username == self.username
                ).all()

            if journal_data:
                self.analyze_journal_correlation(scores, journal_data)
            
            self.results_text.insert(tk.END, "\n" + "="*60 + "\n")
            self.results_text.insert(tk.END, "✅ **Analysis complete!** Check visualizations below.\n")
            
        except Exception as e:
            self.results_text.insert(tk.END, f"❌ **Error in analysis:** {str(e)}\n")
    
    def create_visualizations(self, scores):
        """Create correlation visualizations"""
        if len(scores) < 2:
            return
        
        # Create figure with subplots
        fig = Figure(figsize=(10, 8))
        
        # Plot 1: Score trend
        ax1 = fig.add_subplot(221)
        x_values = range(1, len(scores) + 1)
        ax1.plot(x_values, scores, 'o-', color='#4CAF50', linewidth=2, markersize=6)
        ax1.set_title('EQ Score Trend', fontweight='bold')
        ax1.set_xlabel('Test Number')
        ax1.set_ylabel('Score')
        ax1.grid(True, alpha=0.3)
        
        # Add trend line if enough points
        if len(scores) >= 3:
            z = np.polyfit(x_values, scores, 1)
            p = np.poly1d(z)
            ax1.plot(x_values, p(x_values), "r--", alpha=0.5)
            ax1.text(0.5, 0.05, f'Trend: {z[0]:.2f}/test', 
                    transform=ax1.transAxes, fontsize=10,
                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
        
        # Plot 2: Score distribution histogram
        ax2 = fig.add_subplot(222)
        ax2.hist(scores, bins=5, color='#2196F3', edgecolor='black', alpha=0.7)
        ax2.set_title('Score Distribution', fontweight='bold')
        ax2.set_xlabel('Score')
        ax2.set_ylabel('Frequency')
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Moving average
        ax3 = fig.add_subplot(223)
        if len(scores) >= 3:
            window = min(3, len(scores))
            moving_avg = [np.mean(scores[max(0, i-window+1):i+1]) 
                         for i in range(len(scores))]
            ax3.plot(x_values, moving_avg, 's-', color='#9C27B0', linewidth=2)
            ax3.set_title(f'{window}-Test Moving Average', fontweight='bold')
            ax3.set_xlabel('Test Number')
            ax3.set_ylabel('Average Score')
            ax3.grid(True, alpha=0.3)
        
        # Plot 4: Performance comparison
        ax4 = fig.add_subplot(224)
        if len(scores) >= 4:
            half = len(scores) // 2
            positions = ['First Half', 'Second Half']
            averages = [np.mean(scores[:half]), np.mean(scores[half:])]
            colors = ['#FF9800', '#4CAF50']
            bars = ax4.bar(positions, averages, color=colors)
            ax4.set_title('Performance Comparison', fontweight='bold')
            ax4.set_ylabel('Average Score')
            
            # Add value labels
            for bar, avg in zip(bars, averages):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{avg:.1f}', ha='center', va='bottom')
        
        fig.tight_layout()
        
        # Embed the figure
        canvas = FigureCanvasTkAgg(fig, self.viz_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def analyze_journal_correlation(self, eq_scores, journal_data):
        """Analyze correlation with journal data"""
        sentiments = [j.sentiment_score for j in journal_data if j.sentiment_score is not None]
        
        if sentiments and len(eq_scores) >= 2 and len(sentiments) >= 2:
            self.results_text.insert(tk.END, "\n📝 **Journal Correlation Analysis:**\n")
            
            avg_sentiment = np.mean(sentiments)
            self.results_text.insert(tk.END, f"• Average journal sentiment: {avg_sentiment:.2f}\n")
            
            # Simple correlation analysis
            recent_eq_avg = np.mean(eq_scores[-min(3, len(eq_scores)):])
            recent_sentiment_avg = np.mean(sentiments[-min(3, len(sentiments)):])
            
            if recent_sentiment_avg > 0 and recent_eq_avg > np.mean(eq_scores):
                self.results_text.insert(tk.END, "✅ Positive sentiment correlates with higher EQ scores\n")
            elif recent_sentiment_avg < 0 and recent_eq_avg < np.mean(eq_scores):
                self.results_text.insert(tk.END, "⚠️ Negative sentiment may affect EQ performance\n")
            else:
                self.results_text.insert(tk.END, "🔍 No clear correlation with journal sentiment\n")
    

