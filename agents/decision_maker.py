"""EntraFlow DecisionMaker agent for applying business rules and logic."""

from typing import Any, Dict, List
from enum import Enum
from .base_agent import BaseAgent
from utils.exceptions import ValidationError
from utils.llm import get_llm
from langchain_core.prompts import PromptTemplate


class Priority(Enum):
    """Priority levels for decisions."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionMaker(BaseAgent):
    """
    Agent responsible for making decisions based on analysis results.
    
    Applies business rules and thresholds to determine:
    - Priority levels
    - Required actions
    - Alert triggers
    - Recommendations
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("DecisionMaker", config)
        self.sentiment_threshold = self.config.get('sentiment_threshold', -0.3)
        self.priority_rules = self.config.get('priority_rules', {
            'critical': -0.5,
            'high': -0.3,
            'medium': 0.0,
            'low': 0.3
        })
        self.llm = None
        
        # Initialize LangChain LLM
        try:
            from utils.config import Config
            self.llm = get_llm(Config())
        except Exception as e:
            self.logger.warning(f"Could not initialize LangChain LLM: {str(e)}")
    
    def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make decisions based on analysis results.
        
        Args:
            inputs: Dictionary containing:
                - analysis_results: Output from Analyzer (required)
        
        Returns:
            Dictionary containing:
                - priority: Overall priority level
                - actions: List of recommended actions
                - alerts: List of triggered alerts
                - decisions: Detailed decision breakdown
        """
        # Extract analysis results
        analysis_results = inputs.get('analysis_results')
        if not analysis_results:
            raise ValidationError(self.name, "Missing 'analysis_results' in inputs")
        
        self.logger.info("Making decisions based on analysis results...")
        
        results = {
            'priority': Priority.MEDIUM.value,
            'actions': [],
            'alerts': [],
            'decisions': {},
            'summary': ''
        }
        
        # Analyze sentiment and make decisions
        sentiment_data = analysis_results.get('sentiment', {}).get('news', {})
        if sentiment_data:
            sentiment_decisions = self._decide_on_sentiment(sentiment_data)
            results['decisions']['sentiment'] = sentiment_decisions
            results['actions'].extend(sentiment_decisions.get('actions', []))
            results['alerts'].extend(sentiment_decisions.get('alerts', []))
            
            # Update overall priority
            sentiment_priority = sentiment_decisions.get('priority')
            if sentiment_priority:
                results['priority'] = sentiment_priority
        
        # Analyze keywords and make decisions
        keywords = analysis_results.get('keywords', {}).get('news', {})
        if keywords:
            keyword_decisions = self._decide_on_keywords(keywords)
            results['decisions']['keywords'] = keyword_decisions
            results['actions'].extend(keyword_decisions.get('actions', []))
        
        # Weather-based decisions
        weather_stats = analysis_results.get('statistics', {}).get('weather', {})
        if weather_stats:
            weather_decisions = self._decide_on_weather(weather_stats)
            results['decisions']['weather'] = weather_decisions
            results['actions'].extend(weather_decisions.get('actions', []))
        
        # Generate summary
        results['summary'] = self._generate_decision_summary(results)
        
        # Enhanced LLM Recommendations (LangChain)
        if self.llm:
            try:
                advisory = self._get_llm_recommendation(analysis_results, results)
                results['strategic_advisory'] = advisory
                results['actions'].append("✨ Strategic AI Advisory generated")
            except Exception as e:
                self.logger.warning(f"Failed to generate LLM recommendation: {str(e)}")
        
        self.logger.info(f"Decision complete: Priority={results['priority']}, "
                        f"Actions={len(results['actions'])}, Alerts={len(results['alerts'])}")
        
        return results

    def _get_llm_recommendation(self, analysis_results: Dict[str, Any], decision_results: Dict[str, Any]) -> str:
        """Use LangChain to generate a final strategic recommendation."""
        sentiment = analysis_results.get('sentiment', {}).get('news', {})
        # Truncate inputs to fit in context window (especially for small models like GPT-2)
        insights = "\n".join(analysis_results.get('insights', []))[:300]
        weather = analysis_results.get('statistics', {}).get('weather', {})
        enhanced = str(analysis_results.get('enhanced_insights', 'No deep analysis available'))[:400]
        
        template = """
        System: You are an Executive Risk & Strategy Advisor.
        
        Data:
        - Sentiment: {sentiment_label} (Score: {sentiment_score})
        - Insights: {insights}
        - Weather: {weather_desc}, {temp}°C
        - Market Analysis: {enhanced}
        
        Task: 
        Provide a final, authoritative strategic recommendation for the CEO. 
        Focus on whether to Proceed, Pivot, or Pause operations in this location.
        Keep it under 100 words.
        
        Recommendation:"""
        
        prompt = PromptTemplate(template=template, input_variables=["sentiment_label", "sentiment_score", "insights", "weather_desc", "temp", "enhanced"])
        chain = prompt | self.llm
        
        return chain.invoke({
            "sentiment_label": sentiment.get('sentiment_label', 'neutral'),
            "sentiment_score": sentiment.get('overall_sentiment', 0),
            "insights": insights,
            "weather_desc": weather.get('description', 'clear'),
            "temp": weather.get('temperature', 20),
            "enhanced": enhanced
        })
    
    def _decide_on_sentiment(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make decisions based on sentiment analysis.
        
        Args:
            sentiment_data: Sentiment analysis results
        
        Returns:
            Dictionary with decisions, actions, and alerts
        """
        sentiment_score = sentiment_data.get('overall_sentiment', 0.0)
        sentiment_label = sentiment_data.get('sentiment_label', 'neutral')
        confidence = sentiment_data.get('confidence', 0.0)
        
        decisions = {
            'sentiment_score': sentiment_score,
            'sentiment_label': sentiment_label,
            'confidence': confidence,
            'priority': None,
            'actions': [],
            'alerts': []
        }
        
        # Determine priority based on sentiment
        if sentiment_score <= self.priority_rules.get('critical', -0.5):
            decisions['priority'] = Priority.CRITICAL.value
            decisions['alerts'].append({
                'type': 'CRITICAL_NEGATIVE_SENTIMENT',
                'message': f'Critical negative sentiment detected (score: {sentiment_score:.2f})',
                'severity': 'critical'
            })
            decisions['actions'].append('Immediate review required - critical negative sentiment')
            decisions['actions'].append('Escalate to management for assessment')
            
        elif sentiment_score <= self.priority_rules.get('high', -0.3):
            decisions['priority'] = Priority.HIGH.value
            decisions['alerts'].append({
                'type': 'HIGH_NEGATIVE_SENTIMENT',
                'message': f'Significant negative sentiment detected (score: {sentiment_score:.2f})',
                'severity': 'high'
            })
            decisions['actions'].append('Monitor situation closely')
            decisions['actions'].append('Prepare contingency plans')
            
        elif sentiment_score <= self.priority_rules.get('medium', 0.0):
            decisions['priority'] = Priority.MEDIUM.value
            decisions['actions'].append('Continue regular monitoring')
            
        else:
            decisions['priority'] = Priority.LOW.value
            decisions['actions'].append('Maintain current strategy')
        
        # Additional actions based on confidence
        if confidence < 0.5:
            decisions['actions'].append('Low confidence - consider gathering more data')
        
        return decisions
    
    def _decide_on_keywords(self, keywords: Dict[str, int]) -> Dict[str, Any]:
        """
        Make decisions based on keyword analysis.
        
        Args:
            keywords: Dictionary of keywords and frequencies
        
        Returns:
            Dictionary with keyword-based decisions and actions
        """
        decisions = {
            'top_keywords': keywords,
            'actions': []
        }
        
        # Check for specific concerning keywords
        concerning_keywords = {
            'crisis', 'failure', 'breach', 'attack', 'threat',
            'decline', 'loss', 'problem', 'issue', 'concern'
        }
        
        found_concerning = [kw for kw in keywords.keys() if kw in concerning_keywords]
        
        if found_concerning:
            decisions['concerning_keywords'] = found_concerning
            decisions['actions'].append(
                f"Concerning keywords detected: {', '.join(found_concerning)} - investigate further"
            )
        
        # Check for positive keywords
        positive_keywords = {
            'growth', 'success', 'innovation', 'improvement',
            'achievement', 'breakthrough', 'opportunity'
        }
        
        found_positive = [kw for kw in keywords.keys() if kw in positive_keywords]
        
        if found_positive:
            decisions['positive_keywords'] = found_positive
            decisions['actions'].append(
                f"Positive trends identified: {', '.join(found_positive)}"
            )
        
        return decisions
    
    def _decide_on_weather(self, weather_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make decisions based on weather conditions.
        
        Args:
            weather_stats: Weather statistics
        
        Returns:
            Dictionary with weather-based decisions
        """
        temp_category = weather_stats.get('temperature_category', 'unknown')
        temperature = weather_stats.get('temperature', 0)
        
        decisions = {
            'temperature_category': temp_category,
            'actions': []
        }
        
        if temp_category == 'cold' and temperature < 0:
            decisions['actions'].append('Cold weather alert - prepare for potential operational impacts')
        elif temp_category == 'warm' and temperature > 30:
            decisions['actions'].append('High temperature - monitor equipment cooling systems')
        else:
            decisions['actions'].append('Weather conditions normal - no special actions required')
        
        return decisions
    
    def _generate_decision_summary(self, results: Dict[str, Any]) -> str:
        """
        Generate a human-readable decision summary.
        
        Args:
            results: Decision results dictionary
        
        Returns:
            Summary string
        """
        priority = results.get('priority', Priority.MEDIUM.value).upper()
        alert_count = len(results.get('alerts', []))
        action_count = len(results.get('actions', []))
        
        summary = f"Decision: {priority} priority"
        
        if alert_count > 0:
            summary += f" | {alert_count} alert(s) triggered"
        
        if action_count > 0:
            summary += f" | {action_count} action(s) recommended"
        
        # Add specific sentiment info if available
        sentiment_decision = results.get('decisions', {}).get('sentiment', {})
        if sentiment_decision:
            label = sentiment_decision.get('sentiment_label', 'neutral')
            score = sentiment_decision.get('sentiment_score', 0)
            summary += f" | Sentiment: {label} ({score:.2f})"
        
        return summary
    
    def validate_input(self, inputs: Dict[str, Any]) -> None:
        """Validate decision maker inputs."""
        super().validate_input(inputs)
        
        if 'analysis_results' not in inputs:
            raise ValidationError(self.name, "Missing required input 'analysis_results'")
