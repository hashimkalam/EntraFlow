"""EntraFlow Analyzer agent for performing ML-based analysis on data."""

from typing import Any, Dict, List
from collections import Counter
import re
from .base_agent import BaseAgent
from utils.exceptions import ValidationError
from utils.llm import get_llm
from langchain_core.prompts import PromptTemplate


class Analyzer(BaseAgent):
    """
    Agent responsible for analyzing data using ML models and statistical methods.
    
    Capabilities:
    - Sentiment analysis using pre-trained transformers
    - Keyword extraction and scoring
    - Statistical analysis
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("Analyzer", config)
        self.sentiment_model = None
        self.sentiment_tokenizer = None
        self.llm = None
        
        # Initialize LangChain LLM
        try:
            from utils.config import Config
            self.llm = get_llm(Config())
        except Exception as e:
            self.logger.warning(f"Could not initialize LangChain LLM: {str(e)}")
            
        self._load_ml_models()
    
    def _load_ml_models(self):
        """Load pre-trained ML models for analysis."""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            model_name = self.config.get(
                'model_name',
                'distilbert-base-uncased-finetuned-sst-2-english'
            )
            
            self.logger.info(f"Loading sentiment analysis model: {model_name}")
            self.sentiment_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.sentiment_model.eval()  # Set to evaluation mode
            self.logger.info("ML models loaded successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to load ML models: {str(e)}. Will use fallback analysis.")
            self.sentiment_model = None
            self.sentiment_tokenizer = None
    
    def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform analysis on fetched data.
        
        Args:
            inputs: Dictionary containing:
                - raw_data: Output from DataFetcher (required)
        
        Returns:
            Dictionary containing:
                - sentiment: Overall sentiment analysis
                - keywords: Extracted keywords with scores
                - statistics: Statistical summaries
                - insights: Generated insights
        """
        # Extract data from inputs
        raw_data = inputs.get('raw_data')
        if not raw_data:
            raise ValidationError(self.name, "Missing 'raw_data' in inputs")
        
        data = raw_data.get('data', {})
        
        results = {
            'sentiment': {},
            'keywords': {},
            'statistics': {},
            'insights': []
        }
        
        # Analyze news articles for sentiment
        news_data = data.get('news')
        if news_data and news_data.get('articles'):
            self.logger.info("Analyzing news articles...")
            news_sentiment = self._analyze_news_sentiment(news_data['articles'])
            results['sentiment']['news'] = news_sentiment
            
            # Extract keywords from news
            keywords = self._extract_keywords(news_data['articles'])
            results['keywords']['news'] = keywords
        
        # Analyze weather data
        weather_data = data.get('weather')
        if weather_data:
            self.logger.info("Analyzing weather data...")
            weather_analysis = self._analyze_weather(weather_data)
            results['statistics']['weather'] = weather_analysis
        
        # Generate insights
        results['insights'] = self._generate_insights(results)
        
        # Enhanced LLM Insights (LangChain)
        if self.llm and news_data and news_data.get('articles'):
            try:
                llm_insights = self._generate_llm_insights(news_data['articles'])
                results['enhanced_insights'] = llm_insights
                results['insights'].append("✨ Enhanced LLM analysis included")
            except Exception as e:
                self.logger.warning(f"Failed to generate LLM insights: {str(e)}")
        
        self.logger.info("Analysis completed successfully")
        return results
    
    def _generate_llm_insights(self, articles: List[Dict[str, Any]]) -> str:
        """Use LangChain to extract deeper meaning from articles."""
        # Limit to 3 articles and truncate descriptions to 200 chars to fit context
        context = "\n".join([f"- {a['title']}: {a['description'][:200]}" for a in articles[:3]])
        
        template = """
        You are a business intelligence analyst. Analyze the following news headlines and descriptions:
        {context}
        
        Provide a concise 3-sentence summary that identifies:
        1. The primary business trend.
        2. Potential risks for an enterprise.
        3. One strategic opportunity.
        
        Summary:"""
        
        prompt = PromptTemplate(template=template, input_variables=["context"])
        chain = prompt | self.llm
        
        return chain.invoke({"context": context})
    
    def _analyze_news_sentiment(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze sentiment of news articles.
        
        Args:
            articles: List of article dictionaries
        
        Returns:
            Sentiment analysis results
        """
        if not articles:
            return {
                'overall_sentiment': 0.0,
                'sentiment_label': 'neutral',
                'confidence': 0.0,
                'article_sentiments': []
            }
        
        article_sentiments = []
        
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            sentiment = self._analyze_text_sentiment(text)
            article_sentiments.append({
                'title': article.get('title', 'Untitled'),
                'sentiment_score': sentiment['score'],
                'sentiment_label': sentiment['label'],
                'confidence': sentiment['confidence']
            })
        
        # Calculate overall sentiment
        avg_sentiment = sum(s['sentiment_score'] for s in article_sentiments) / len(article_sentiments)
        avg_confidence = sum(s['confidence'] for s in article_sentiments) / len(article_sentiments)
        
        # Determine overall label
        if avg_sentiment < -0.3:
            label = 'negative'
        elif avg_sentiment > 0.3:
            label = 'positive'
        else:
            label = 'neutral'
        
        return {
            'overall_sentiment': round(avg_sentiment, 3),
            'sentiment_label': label,
            'confidence': round(avg_confidence, 3),
            'article_sentiments': article_sentiments,
            'total_articles': len(articles)
        }
    
    def _analyze_text_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a single text using ML model or fallback.
        
        Args:
            text: Text to analyze
        
        Returns:
            Dictionary with score, label, and confidence
        """
        if not text or not text.strip():
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.0}
        
        # Use ML model if available
        if self.sentiment_model and self.sentiment_tokenizer:
            try:
                import torch
                
                # Tokenize and predict
                inputs = self.sentiment_tokenizer(
                    text,
                    return_tensors='pt',
                    truncation=True,
                    max_length=512,
                    padding=True
                )
                
                with torch.no_grad():
                    outputs = self.sentiment_model(**inputs)
                    predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                
                # DistilBERT outputs: [negative, positive]
                negative_score = predictions[0][0].item()
                positive_score = predictions[0][1].item()
                
                # Convert to -1 to 1 scale
                sentiment_score = positive_score - negative_score
                confidence = max(positive_score, negative_score)
                
                if sentiment_score < -0.3:
                    label = 'negative'
                elif sentiment_score > 0.3:
                    label = 'positive'
                else:
                    label = 'neutral'
                
                return {
                    'score': round(sentiment_score, 3),
                    'label': label,
                    'confidence': round(confidence, 3)
                }
                
            except Exception as e:
                self.logger.warning(f"ML sentiment analysis failed: {str(e)}, using fallback")
        
        # Fallback: Simple keyword-based sentiment
        return self._fallback_sentiment(text)
    
    def _fallback_sentiment(self, text: str) -> Dict[str, Any]:
        """Simple keyword-based sentiment analysis as fallback."""
        text_lower = text.lower()
        
        positive_words = ['good', 'great', 'excellent', 'positive', 'success', 'improvement',
                         'growth', 'innovation', 'efficient', 'effective', 'benefit']
        negative_words = ['bad', 'poor', 'negative', 'failure', 'problem', 'issue',
                         'decline', 'risk', 'threat', 'challenge', 'concern']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.5}
        
        score = (positive_count - negative_count) / max(total, 1)
        confidence = min(total / 10, 1.0)  # Simple confidence based on keyword count
        
        if score < -0.2:
            label = 'negative'
        elif score > 0.2:
            label = 'positive'
        else:
            label = 'neutral'
        
        return {
            'score': round(score, 3),
            'label': label,
            'confidence': round(confidence, 3)
        }
    
    def _extract_keywords(self, articles: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Extract and score keywords from articles.
        
        Args:
            articles: List of article dictionaries
        
        Returns:
            Dictionary of keywords with frequency scores
        """
        all_text = ' '.join(
            f"{article.get('title', '')} {article.get('description', '')}"
            for article in articles
        )
        
        # Simple keyword extraction: find words, remove common words
        words = re.findall(r'\b[a-z]{4,}\b', all_text.lower())
        
        # Common words to exclude
        stopwords = {'that', 'this', 'with', 'from', 'have', 'been', 'were',
                    'their', 'about', 'would', 'there', 'which', 'when', 'where'}
        
        filtered_words = [w for w in words if w not in stopwords]
        
        # Count frequencies
        word_counts = Counter(filtered_words)
        
        # Get top keywords
        max_keywords = self.config.get('max_keywords', 10)
        top_keywords = dict(word_counts.most_common(max_keywords))
        
        return top_keywords
    
    def _analyze_weather(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform statistical analysis on weather data.
        
        Args:
            weather_data: Weather data dictionary
        
        Returns:
            Weather analysis results
        """
        temp = weather_data.get('temperature', 0)
        humidity = weather_data.get('humidity', 0)
        wind_speed = weather_data.get('wind_speed', 0)
        
        # Simple categorization
        if temp < 10:
            temp_category = 'cold'
        elif temp < 20:
            temp_category = 'mild'
        else:
            temp_category = 'warm'
        
        return {
            'location': weather_data.get('location', 'Unknown'),
            'temperature': temp,
            'temperature_category': temp_category,
            'humidity': humidity,
            'wind_speed': wind_speed,
            'description': weather_data.get('description', '')
        }
    
    def _generate_insights(self, results: Dict[str, Any]) -> List[str]:
        """
        Generate actionable insights from analysis results.
        
        Args:
            results: Analysis results dictionary
        
        Returns:
            List of insight strings
        """
        insights = []
        
        # Sentiment insights
        news_sentiment = results.get('sentiment', {}).get('news', {})
        if news_sentiment:
            sentiment_label = news_sentiment.get('sentiment_label', 'neutral')
            sentiment_score = news_sentiment.get('overall_sentiment', 0)
            total_articles = news_sentiment.get('total_articles', 0)
            
            insights.append(
                f"Analyzed {total_articles} articles with overall {sentiment_label} "
                f"sentiment (score: {sentiment_score:.2f})"
            )
            
            if sentiment_label == 'negative':
                insights.append("⚠️ Negative sentiment detected - recommend further investigation")
            elif sentiment_label == 'positive':
                insights.append("✓ Positive sentiment indicates favorable conditions")
        
        # Keyword insights
        keywords = results.get('keywords', {}).get('news', {})
        if keywords:
            top_keyword = max(keywords.items(), key=lambda x: x[1]) if keywords else None
            if top_keyword:
                insights.append(f"Top trending keyword: '{top_keyword[0]}' (mentioned {top_keyword[1]} times)")
        
        # Weather insights
        weather_stats = results.get('statistics', {}).get('weather', {})
        if weather_stats:
            temp_category = weather_stats.get('temperature_category', 'unknown')
            insights.append(f"Weather conditions: {temp_category} temperature")
        
        return insights
    
    def validate_input(self, inputs: Dict[str, Any]) -> None:
        """Validate analyzer inputs."""
        super().validate_input(inputs)
        
        if 'raw_data' not in inputs:
            raise ValidationError(self.name, "Missing required input 'raw_data'")
