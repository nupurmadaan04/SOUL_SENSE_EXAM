"""
Score analysis module with work/study satisfaction scoring.
"""
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

class SatisfactionAnalyzer:
    """Analyzes work/study satisfaction scores."""
    
    # Core satisfaction domains and their weights
    CORE_DOMAINS = {
        'motivation': {
            'question_id': 101,
            'weight': 0.30,
            'description': 'Drive and enthusiasm for work/studies'
        },
        'engagement': {
            'question_id': 102,
            'weight': 0.25,
            'description': 'Focus and immersion in activities'
        },
        'progress': {
            'question_id': 103,
            'weight': 0.20,
            'description': 'Satisfaction with achievements and growth'
        },
        'environment': {
            'question_id': 104,
            'weight': 0.15,
            'description': 'Satisfaction with physical and social setting'
        },
        'balance': {
            'question_id': 105,
            'weight': 0.10,
            'description': 'Work-study-life balance'
        }
    }
    
    # Extended domains (optional)
    EXTENDED_DOMAINS = {
        'meaning': {
            'question_id': 106,
            'weight': 0.05,
            'description': 'Sense of purpose and value'
        },
        'support': {
            'question_id': 107,
            'weight': 0.05,
            'description': 'Availability of support system'
        },
        'clarity': {
            'question_id': 108,
            'weight': 0.05,
            'description': 'Clear goals and expectations'
        },
        'autonomy': {
            'question_id': 109,
            'weight': 0.05,
            'description': 'Freedom and control in approach'
        },
        'recommendation': {
            'question_id': 110,
            'weight': 0.05,
            'description': 'Overall endorsement likelihood'
        }
    }
    
    @staticmethod
    def calculate_satisfaction_score(responses: Dict[int, int]) -> Dict[str, Any]:
        """
        Calculate work/study satisfaction score from responses.
        
        Args:
            responses: Dictionary mapping question_id to response (1-5)
            
        Returns:
            Dictionary with comprehensive satisfaction analysis
        """
        try:
            # Validate responses
            validated_responses = SatisfactionAnalyzer._validate_responses(responses)
            if not validated_responses:
                return SatisfactionAnalyzer._create_error_response("No valid responses provided")
            
            # Calculate domain scores
            domain_scores = {}
            core_domains_used = []
            extended_domains_used = []
            
            # Process core domains
            for domain, config in SatisfactionAnalyzer.CORE_DOMAINS.items():
                qid = config['question_id']
                if qid in validated_responses:
                    raw_score = validated_responses[qid]
                    weighted_score = raw_score * config['weight']
                    domain_scores[domain] = {
                        'raw_score': raw_score,
                        'weighted_score': weighted_score,
                        'weight': config['weight'],
                        'description': config['description'],
                        'interpretation': SatisfactionAnalyzer._interpret_domain_score(raw_score),
                        'question_id': qid
                    }
                    core_domains_used.append(domain)
            
            # Process extended domains (if available)
            for domain, config in SatisfactionAnalyzer.EXTENDED_DOMAINS.items():
                qid = config['question_id']
                if qid in validated_responses:
                    raw_score = validated_responses[qid]
                    weighted_score = raw_score * config['weight']
                    domain_scores[domain] = {
                        'raw_score': raw_score,
                        'weighted_score': weighted_score,
                        'weight': config['weight'],
                        'description': config['description'],
                        'interpretation': SatisfactionAnalyzer._interpret_domain_score(raw_score),
                        'question_id': qid,
                        'is_extended': True
                    }
                    extended_domains_used.append(domain)
            
            if not domain_scores:
                return SatisfactionAnalyzer._create_error_response("No valid satisfaction responses found")
            
            # Calculate overall scores
            overall_score = SatisfactionAnalyzer._calculate_overall_score(domain_scores)
            
            # Generate interpretation and recommendations
            interpretation = SatisfactionAnalyzer._interpret_overall_score(overall_score['weighted_average_5'])
            recommendations = SatisfactionAnalyzer._generate_recommendations(domain_scores, overall_score)
            
            # Calculate benchmark comparison
            benchmark_comparison = SatisfactionAnalyzer._calculate_benchmark_comparison(
                overall_score['score_0_100']
            )
            
            # Identify strengths and areas for improvement
            strengths = SatisfactionAnalyzer._identify_strengths(domain_scores)
            areas_for_improvement = SatisfactionAnalyzer._identify_improvement_areas(domain_scores)
            
            return {
                'success': True,
                'overall_score': overall_score,
                'domain_scores': domain_scores,
                'interpretation': interpretation,
                'recommendations': recommendations,
                'benchmark_comparison': benchmark_comparison,
                'strengths': strengths,
                'areas_for_improvement': areas_for_improvement,
                'metadata': {
                    'core_domains_used': core_domains_used,
                    'extended_domains_used': extended_domains_used,
                    'total_domains': len(core_domains_used) + len(extended_domains_used),
                    'calculation_method': 'weighted_average',
                    'scale_used': '5-point Likert (1-5)',
                    'calculated_at': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating satisfaction score: {str(e)}")
            return SatisfactionAnalyzer._create_error_response(f"Calculation error: {str(e)}")
    
    @staticmethod
    def calculate_satisfaction_trend(user_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate satisfaction trend over time.
        
        Args:
            user_scores: List of previous satisfaction score results
            
        Returns:
            Dictionary with trend analysis
        """
        if len(user_scores) < 2:
            return {
                'has_sufficient_data': False,
                'message': 'Need at least 2 assessments to calculate trend'
            }
        
        try:
            # Extract scores over time
            timeline = []
            for score_data in sorted(user_scores, key=lambda x: x.get('timestamp', '')):
                if 'overall_score' in score_data and 'score_0_100' in score_data['overall_score']:
                    timeline.append({
                        'timestamp': score_data.get('timestamp', ''),
                        'score': score_data['overall_score']['score_0_100'],
                        'weighted_average': score_data['overall_score'].get('weighted_average_5', 0)
                    })
            
            if len(timeline) < 2:
                return {'has_sufficient_data': False}
            
            # Calculate trend metrics
            scores = [t['score'] for t in timeline]
            first_score = scores[0]
            last_score = scores[-1]
            score_change = last_score - first_score
            percent_change = (score_change / first_score * 100) if first_score > 0 else 0
            
            # Calculate moving average (last 3 scores)
            recent_scores = scores[-3:] if len(scores) >= 3 else scores
            moving_avg = sum(recent_scores) / len(recent_scores)
            
            # Determine trend direction
            if score_change > 5:
                trend_direction = 'improving'
                trend_strength = 'strong' if score_change > 15 else 'moderate'
            elif score_change < -5:
                trend_direction = 'declining'
                trend_strength = 'strong' if score_change < -15 else 'moderate'
            else:
                trend_direction = 'stable'
                trend_strength = 'stable'
            
            # Calculate volatility
            volatility = np.std(scores) if len(scores) > 1 else 0
            
            return {
                'has_sufficient_data': True,
                'timeline': timeline,
                'statistics': {
                    'first_score': round(first_score, 1),
                    'last_score': round(last_score, 1),
                    'score_change': round(score_change, 1),
                    'percent_change': round(percent_change, 1),
                    'moving_average': round(moving_avg, 1),
                    'volatility': round(volatility, 2),
                    'assessment_count': len(timeline)
                },
                'trend_analysis': {
                    'direction': trend_direction,
                    'strength': trend_strength,
                    'interpretation': SatisfactionAnalyzer._interpret_trend(
                        trend_direction, trend_strength, score_change
                    )
                },
                'pattern_detection': SatisfactionAnalyzer._detect_patterns(scores)
            }
            
        except Exception as e:
            logger.error(f"Error calculating trend: {str(e)}")
            return {'error': str(e), 'has_sufficient_data': False}
    
    @staticmethod
    def compare_with_benchmarks(score_0_100: float, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Compare user's score with typical benchmarks.
        
        Args:
            score_0_100: User's overall satisfaction score (0-100)
            context: Optional context (industry, role, experience)
            
        Returns:
            Benchmark comparison results
        """
        # Default benchmarks (based on general population)
        benchmarks = {
            'excellent': {'min': 80, 'description': 'Top 20%'},
            'good': {'min': 65, 'max': 79, 'description': 'Above average'},
            'average': {'min': 50, 'max': 64, 'description': 'Typical range'},
            'below_average': {'min': 40, 'max': 49, 'description': 'Needs attention'},
            'poor': {'max': 39, 'description': 'Immediate intervention needed'}
        }
        
        # Adjust benchmarks based on context if provided
        if context:
            if context.get('industry') == 'technology':
                # Tech industry typically has lower satisfaction
                benchmarks = {k: {**v, 'min': v.get('min', 0) - 5, 'max': v.get('max', 100) - 5} 
                            for k, v in benchmarks.items()}
            elif context.get('role') == 'student':
                # Students often have different satisfaction patterns
                benchmarks = {k: {**v, 'min': v.get('min', 0) - 3, 'max': v.get('max', 100) - 3} 
                            for k, v in benchmarks.items()}
        
        # Determine benchmark category
        user_benchmark = 'excellent'
        for category, range_info in benchmarks.items():
            min_score = range_info.get('min', 0)
            max_score = range_info.get('max', 100)
            
            if 'min' in range_info and 'max' in range_info:
                if min_score <= score_0_100 <= max_score:
                    user_benchmark = category
                    break
            elif 'min' in range_info:
                if score_0_100 >= min_score:
                    user_benchmark = category
                    break
            elif 'max' in range_info:
                if score_0_100 <= max_score:
                    user_benchmark = category
                    break
        
        percentile = SatisfactionAnalyzer._estimate_percentile(score_0_100)
        
        return {
            'user_score': round(score_0_100, 1),
            'benchmark_category': user_benchmark,
            'benchmark_description': benchmarks[user_benchmark]['description'],
            'percentile_estimate': percentile,
            'benchmarks': benchmarks,
            'comparison_notes': SatisfactionAnalyzer._generate_benchmark_notes(
                user_benchmark, context
            )
        }
    
    # ==================== HELPER METHODS ====================
    
    @staticmethod
    def _validate_responses(responses: Dict[int, int]) -> Dict[int, int]:
        """Validate and clean response values."""
        validated = {}
        for qid, response in responses.items():
            # Check if it's a satisfaction question (101-110)
            if 101 <= qid <= 110:
                # Ensure response is between 1-5
                clean_response = max(1, min(5, int(response)))
                validated[qid] = clean_response
        return validated
    
    @staticmethod
    def _calculate_overall_score(domain_scores: Dict) -> Dict[str, float]:
        """Calculate overall satisfaction scores."""
        total_weighted = 0
        total_weight = 0
        
        for domain, data in domain_scores.items():
            total_weighted += data['weighted_score']
            total_weight += data['weight']
        
        # Calculate weighted average on 1-5 scale
        weighted_average_5 = total_weighted / total_weight if total_weight > 0 else 0
        
        # Convert to 0-100 scale
        score_0_100 = weighted_average_5 * 20  # (1-5) * 20 = (0-100)
        
        # Calculate unweighted average for reference
        raw_scores = [data['raw_score'] for data in domain_scores.values()]
        unweighted_average = sum(raw_scores) / len(raw_scores) if raw_scores else 0
        
        return {
            'score_0_100': round(score_0_100, 1),
            'weighted_average_5': round(weighted_average_5, 2),
            'unweighted_average_5': round(unweighted_average, 2),
            'total_weight': round(total_weight, 2),
            'scale': {'min': 0, 'max': 100, 'unit': 'points'}
        }
    
    @staticmethod
    def _interpret_domain_score(score: int) -> str:
        """Interpret individual domain scores."""
        interpretations = {
            1: "Very Low - Significant dissatisfaction",
            2: "Low - Room for substantial improvement",
            3: "Moderate - Adequate but could be better",
            4: "High - Generally satisfied",
            5: "Very High - Excellent satisfaction"
        }
        return interpretations.get(score, "Unknown score")
    
    @staticmethod
    def _interpret_overall_score(weighted_average: float) -> Dict[str, Any]:
        """Interpret overall satisfaction score."""
        score_100 = weighted_average * 20
        
        if score_100 >= 80:
            return {
                'level': 'High Satisfaction',
                'description': 'Strong engagement and positive experience',
                'emotional_state': 'Engaged, motivated, fulfilled',
                'risk_level': 'Low'
            }
        elif score_100 >= 65:
            return {
                'level': 'Moderate Satisfaction',
                'description': 'Generally positive with some areas for enhancement',
                'emotional_state': 'Content, with occasional frustrations',
                'risk_level': 'Low to Moderate'
            }
        elif score_100 >= 50:
            return {
                'level': 'Average Satisfaction',
                'description': 'Mixed feelings, needs targeted improvements',
                'emotional_state': 'Neutral, with periods of disengagement',
                'risk_level': 'Moderate'
            }
        elif score_100 >= 40:
            return {
                'level': 'Below Average Satisfaction',
                'description': 'Significant areas of dissatisfaction',
                'emotional_state': 'Frustrated, disengaged, stressed',
                'risk_level': 'High'
            }
        else:
            return {
                'level': 'Critical Dissatisfaction',
                'description': 'Urgent attention needed in multiple areas',
                'emotional_state': 'Burnout risk, high stress, disengagement',
                'risk_level': 'Very High'
            }
    
    @staticmethod
    def _generate_recommendations(domain_scores: Dict, overall_score: Dict) -> List[Dict[str, Any]]:
        """Generate personalized recommendations."""
        recommendations = []
        
        # Overall recommendation based on score
        score_100 = overall_score['score_0_100']
        
        if score_100 < 40:
            recommendations.append({
                'priority': 'critical',
                'category': 'overall',
                'title': 'Seek Immediate Support',
                'description': 'Your satisfaction level indicates significant distress. Consider speaking with a supervisor, counselor, or mentor.',
                'actions': [
                    'Schedule a meeting with your supervisor/advisor',
                    'Contact HR or student support services',
                    'Consider professional counseling if stress persists'
                ]
            })
        
        # Domain-specific recommendations
        for domain, data in domain_scores.items():
            if data['raw_score'] <= 2:  # Low scores
                if domain == 'balance':
                    recommendations.append({
                        'priority': 'high',
                        'category': domain,
                        'title': f'Improve {domain.replace("_", " ").title()}',
                        'description': f'Your {data["description"]} is low. This can lead to burnout.',
                        'actions': [
                            'Set clear boundaries between work/study and personal time',
                            'Schedule regular breaks and self-care activities',
                            'Learn to say no to non-essential commitments'
                        ]
                    })
                elif domain == 'motivation':
                    recommendations.append({
                        'priority': 'high',
                        'category': domain,
                        'title': 'Boost Motivation',
                        'description': 'Low motivation can affect performance and satisfaction.',
                        'actions': [
                            'Reconnect with your "why" - remember your goals',
                            'Break large tasks into smaller, achievable steps',
                            'Find aspects of your work that align with personal values'
                        ]
                    })
        
        # General recommendations for moderate scores
        if 50 <= score_100 < 65:
            recommendations.append({
                'priority': 'medium',
                'category': 'general',
                'title': 'Enhance Engagement',
                'description': 'Small improvements can significantly boost satisfaction.',
                'actions': [
                    'Identify and leverage your strengths more intentionally',
                    'Seek feedback and recognition for your contributions',
                    'Build stronger connections with colleagues/peers'
                ]
            })
        
        # Limit to top 5 recommendations
        return sorted(recommendations, key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}[x['priority']])[:5]
    
    @staticmethod
    def _calculate_benchmark_comparison(score_100: float) -> Dict[str, Any]:
        """Calculate how user's score compares to benchmarks."""
        # Simple percentile estimation
        if score_100 >= 85:
            percentile = 90
            comparison = "Excellent - Top 10%"
        elif score_100 >= 75:
            percentile = 75
            comparison = "Very Good - Top 25%"
        elif score_100 >= 60:
            percentile = 50
            comparison = "Average - Typical range"
        elif score_100 >= 45:
            percentile = 30
            comparison = "Below Average - Bottom 30%"
        else:
            percentile = 10
            comparison = "Low - Bottom 10%"
        
        return {
            'percentile': percentile,
            'comparison_text': comparison,
            'benchmark_ranges': {
                'top_10_percent': 85,
                'top_25_percent': 75,
                'average_range': (60, 74),
                'below_average': (45, 59),
                'low_range': (0, 44)
            }
        }
    
    @staticmethod
    def _identify_strengths(domain_scores: Dict) -> List[Dict[str, Any]]:
        """Identify user's satisfaction strengths."""
        strengths = []
        for domain, data in domain_scores.items():
            if data['raw_score'] >= 4:
                strengths.append({
                    'domain': domain,
                    'score': data['raw_score'],
                    'description': data['description'],
                    'impact': 'High satisfaction in this area contributes positively to overall well-being'
                })
        return strengths[:3]  # Return top 3 strengths
    
    @staticmethod
    def _identify_improvement_areas(domain_scores: Dict) -> List[Dict[str, Any]]:
        """Identify areas needing improvement."""
        improvements = []
        for domain, data in domain_scores.items():
            if data['raw_score'] <= 3:
                improvements.append({
                    'domain': domain,
                    'score': data['raw_score'],
                    'description': data['description'],
                    'priority': 'high' if data['raw_score'] <= 2 else 'medium',
                    'suggested_action': SatisfactionAnalyzer._get_improvement_action(domain)
                })
        return sorted(improvements, key=lambda x: {'high': 0, 'medium': 1}[x['priority']])[:3]
    
    @staticmethod
    def _get_improvement_action(domain: str) -> str:
        """Get specific improvement action for a domain."""
        actions = {
            'motivation': "Reconnect with personal goals and find meaning in tasks",
            'engagement': "Implement focus techniques like Pomodoro or time-blocking",
            'progress': "Set smaller, achievable milestones and celebrate progress",
            'environment': "Improve workspace organization or address interpersonal issues",
            'balance': "Establish clearer boundaries and schedule regular downtime",
            'meaning': "Align tasks with personal values and larger purpose",
            'support': "Build support network and communicate needs clearly",
            'clarity': "Seek clarification on expectations and set clear personal goals",
            'autonomy': "Negotiate for more control over work methods or schedule"
        }
        return actions.get(domain, "Focus on incremental improvements in this area")
    
    @staticmethod
    def _interpret_trend(direction: str, strength: str, change: float) -> str:
        """Interpret trend direction and strength."""
        if direction == 'improving':
            if strength == 'strong':
                return "Significant positive trend - continuing current approaches is working well"
            else:
                return "Moderate improvement - small adjustments could enhance progress"
        elif direction == 'declining':
            if strength == 'strong':
                return "Concerning downward trend - intervention recommended"
            else:
                return "Slight decline - monitor closely and consider adjustments"
        else:
            return "Stable pattern - maintaining current satisfaction level"
    
    @staticmethod
    def _detect_patterns(scores: List[float]) -> Dict[str, Any]:
        """Detect patterns in score sequence."""
        if len(scores) < 3:
            return {'detected_patterns': []}
        
        patterns = []
        
        # Check for consistent improvement/decline
        differences = [scores[i+1] - scores[i] for i in range(len(scores)-1)]
        if all(diff > 0 for diff in differences):
            patterns.append('consistent_improvement')
        elif all(diff < 0 for diff in differences):
            patterns.append('consistent_decline')
        
        # Check for volatility
        volatility = np.std(scores)
        if volatility > 15:
            patterns.append('high_volatility')
        elif volatility < 5:
            patterns.append('low_volatility')
        
        # Check for cyclical pattern (every other assessment similar)
        if len(scores) >= 4:
            odd_scores = scores[::2]
            even_scores = scores[1::2]
            if np.std(odd_scores) < 5 and np.std(even_scores) < 5 and abs(np.mean(odd_scores) - np.mean(even_scores)) > 10:
                patterns.append('alternating_pattern')
        
        return {
            'detected_patterns': patterns,
            'volatility_score': round(volatility, 2),
            'consistency_score': round(1 - (volatility / 50), 2)  # Normalized 0-1
        }
    
    @staticmethod
    def _estimate_percentile(score_100: float) -> int:
        """Estimate percentile based on typical distribution."""
        # Based on normal distribution approximation
        if score_100 >= 90:
            return 95
        elif score_100 >= 80:
            return 85
        elif score_100 >= 70:
            return 70
        elif score_100 >= 60:
            return 50
        elif score_100 >= 50:
            return 35
        elif score_100 >= 40:
            return 20
        else:
            return 10
    
    @staticmethod
    def _generate_benchmark_notes(benchmark_category: str, context: Dict = None) -> List[str]:
        """Generate notes about benchmark comparison."""
        notes = []
        
        if benchmark_category == 'excellent':
            notes.append("You're in the top tier of satisfaction scores")
            notes.append("Consider mentoring others or sharing what works for you")
        elif benchmark_category == 'good':
            notes.append("Above average satisfaction - continue current practices")
            notes.append("Small improvements could move you into excellent range")
        elif benchmark_category == 'average':
            notes.append("Typical satisfaction level - room for growth")
            notes.append("Focus on 1-2 key areas for targeted improvement")
        elif benchmark_category == 'below_average':
            notes.append("Below typical satisfaction - attention needed")
            notes.append("Consider discussing concerns with supervisor/advisor")
        else:  # poor
            notes.append("Immediate attention recommended")
            notes.append("Consider professional support or significant changes")
        
        if context and context.get('role') == 'student':
            notes.append("Note: Student satisfaction often increases with academic progression")
        
        return notes
    
    @staticmethod
    def _create_error_response(message: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            'success': False,
            'error': message,
            'overall_score': None,
            'domain_scores': {},
            'interpretation': {'level': 'Unknown', 'description': 'Unable to calculate score'},
            'metadata': {
                'calculated_at': datetime.utcnow().isoformat(),
                'error': message
            }
        }


# ==================== MAIN SCORE ANALYZER CLASS ====================

class ScoreAnalyzer:
    """Main score analyzer integrating emotional intelligence and satisfaction."""
    
    @staticmethod
    def analyze_comprehensive(responses: Dict[int, int], user_context: Dict = None) -> Dict[str, Any]:
        """
        Comprehensive analysis of both emotional intelligence and satisfaction.
        
        Args:
            responses: Dictionary of question_id -> response
            user_context: User context (age, occupation, etc.)
            
        Returns:
            Integrated analysis results
        """
        # Separate emotional intelligence and satisfaction responses
        eq_responses = {qid: resp for qid, resp in responses.items() if 1 <= qid <= 10}
        sat_responses = {qid: resp for qid, resp in responses.items() if 101 <= qid <= 110}
        
        results = {
            'emotional_intelligence': ScoreAnalyzer._analyze_eq_scores(eq_responses),
            'satisfaction': SatisfactionAnalyzer.calculate_satisfaction_score(sat_responses),
            'integrated_insights': [],
            'metadata': {
                'analysis_date': datetime.utcnow().isoformat(),
                'total_questions': len(responses),
                'eq_questions': len(eq_responses),
                'satisfaction_questions': len(sat_responses)
            }
        }
        
        # Generate integrated insights if both analyses succeeded
        if (results['emotional_intelligence'].get('success', False) and 
            results['satisfaction'].get('success', False)):
            results['integrated_insights'] = ScoreAnalyzer._generate_integrated_insights(
                results['emotional_intelligence'],
                results['satisfaction']
            )
        
        return results
    
    @staticmethod
    def _analyze_eq_scores(responses: Dict[int, int]) -> Dict[str, Any]:
        """Analyze emotional intelligence scores (simplified version)."""
        if not responses:
            return {'success': False, 'error': 'No emotional intelligence responses'}
        
        # Simple EQ calculation (you can replace with your actual EQ logic)
        scores = list(responses.values())
        avg_score = sum(scores) / len(scores) if scores else 0
        total_score = sum(scores)
        
        return {
            'success': True,
            'average_score': round(avg_score, 2),
            'total_score': total_score,
            'question_count': len(responses),
            'interpretation': ScoreAnalyzer._interpret_eq_score(avg_score)
        }
    
    @staticmethod
    def _interpret_eq_score(avg_score: float) -> Dict[str, str]:
        """Interpret emotional intelligence score."""
        if avg_score >= 4:
            return {'level': 'High', 'description': 'Strong emotional awareness and regulation'}
        elif avg_score >= 3:
            return {'level': 'Moderate', 'description': 'Adequate emotional skills with room for growth'}
        else:
            return {'level': 'Developing', 'description': 'Opportunity to enhance emotional intelligence'}
    
    @staticmethod
    def _generate_integrated_insights(eq_analysis: Dict, sat_analysis: Dict) -> List[Dict[str, Any]]:
        """Generate insights combining EQ and satisfaction analysis."""
        insights = []
        
        eq_level = eq_analysis.get('interpretation', {}).get('level', 'Unknown')
        sat_level = sat_analysis.get('interpretation', {}).get('level', 'Unknown')
        sat_score = sat_analysis.get('overall_score', {}).get('score_0_100', 0)
        
        # Insight 1: Emotional regulation and satisfaction
        if eq_level == 'High' and sat_level in ['High Satisfaction', 'Moderate Satisfaction']:
            insights.append({
                'type': 'positive_correlation',
                'title': 'Strong Emotional Skills Support Satisfaction',
                'description': 'Your emotional intelligence appears to contribute positively to your work/study satisfaction.',
                'implication': 'Continue developing emotional skills as they enhance overall well-being.'
            })
        elif eq_level in ['Developing', 'Moderate'] and sat_score < 50:
            insights.append({
                'type': 'development_opportunity',
                'title': 'Emotional Skills Development Could Boost Satisfaction',
                'description': 'Improving emotional awareness and regulation might enhance your work/study satisfaction.',
                'suggestion': 'Consider emotional intelligence training or mindfulness practices.'
            })
        
        # Insight 2: Specific domain correlations
        if 'domain_scores' in sat_analysis:
            for domain, data in sat_analysis['domain_scores'].items():
                if data['raw_score'] <= 2:  # Low satisfaction domain
                    if domain in ['environment', 'support']:
                        insights.append({
                            'type': 'interpersonal_focus',
                            'title': f'Low {domain.title()} Satisfaction May Affect Relationships',
                            'description': f'Dissatisfaction with {domain} could impact your emotional interactions.',
                            'action': f'Consider addressing {domain} issues to improve both satisfaction and emotional well-being.'
                        })
        
        # Insight 3: Overall pattern
        if sat_score >= 70 and eq_level == 'High':
            insights.append({
                'type': 'optimal_state',
                'title': 'Optimal Well-being State',
                'description': 'You appear to have strong emotional skills paired with high satisfaction.',
                'encouragement': 'This combination supports resilience and long-term success.'
            })
        
        return insights[:3]  # Return top 3 insights


# ==================== QUICK UTILITY FUNCTIONS ====================

def quick_satisfaction_assessment(responses: Dict[int, int]) -> Dict[str, Any]:
    """Quick assessment for simple use cases."""
    return SatisfactionAnalyzer.calculate_satisfaction_score(responses)

def calculate_satisfaction_trend(history: List[Dict]) -> Dict[str, Any]:
    """Calculate trend from satisfaction history."""
    return SatisfactionAnalyzer.calculate_satisfaction_trend(history)

def compare_with_benchmarks(score: float, context: Dict = None) -> Dict[str, Any]:
    """Compare score with benchmarks."""
    return SatisfactionAnalyzer.compare_with_benchmarks(score, context)


# Example usage
if __name__ == "__main__":
    # Test with sample responses
    sample_responses = {
        101: 4,  # Motivation
        102: 3,  # Engagement
        103: 2,  # Progress
        104: 4,  # Environment
        105: 1,  # Balance
        106: 3,  # Meaning
        107: 2,  # Support
    }
    
    print("=== Satisfaction Analysis Example ===")
    result = SatisfactionAnalyzer.calculate_satisfaction_score(sample_responses)
    print(f"Overall Score: {result.get('overall_score', {}).get('score_0_100', 'N/A')}")
    print(f"Interpretation: {result.get('interpretation', {}).get('level', 'N/A')}")
    print(f"Recommendations: {len(result.get('recommendations', []))}")
    
    print("\n=== Comprehensive Analysis Example ===")
    comprehensive_responses = {
        1: 4, 2: 3, 3: 5, 4: 3, 5: 4,  # EQ questions
        101: 4, 102: 3, 103: 2, 104: 4, 105: 1  # Satisfaction questions
    }
    comp_result = ScoreAnalyzer.analyze_comprehensive(comprehensive_responses)
    print(f"EQ Score: {comp_result['emotional_intelligence'].get('average_score', 'N/A')}")
    print(f"Satisfaction Score: {comp_result['satisfaction'].get('overall_score', {}).get('score_0_100', 'N/A')}")
    print(f"Integrated Insights: {len(comp_result['integrated_insights'])}")