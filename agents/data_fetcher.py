"""DataFetcher agent for retrieving data from external APIs."""

import requests
import os
from typing import Any, Dict, List
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from utils.exceptions import APIError, ValidationError


class DataFetcher(BaseAgent):
    """
    Agent responsible for fetching data from multiple external sources.
    
    Supported data sources:
    - Weather data (OpenWeatherMap API)
    - News articles (NewsAPI)
    - Mock data for demo purposes
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("DataFetcher", config)
        self.cache = {}
        self.cache_enabled = self.config.get('cache_enabled', True)
        self.cache_ttl = self.config.get('cache_ttl', 300)  # 5 minutes default
    
    def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch data from configured sources.
        
        Args:
            inputs: Dictionary with optional keys:
                - sources: List of data sources to fetch (default: all)
                - location: Location for weather data (default: 'London')
                - news_query: Query for news search (default: 'technology')
        
        Returns:
            Dictionary containing:
                - weather: Weather data
                - news: News articles
                - metadata: Fetch metadata
        """
        sources = inputs.get('sources', ['weather', 'news'])
        results = {
            'data': {},
            'metadata': {
                'fetch_time': datetime.now().isoformat(),
                'sources_requested': sources,
                'sources_fetched': []
            }
        }
        
        # Fetch weather data
        if 'weather' in sources:
            try:
                location = inputs.get('location', 'London')
                weather_data = self._fetch_weather(location)
                results['data']['weather'] = weather_data
                results['metadata']['sources_fetched'].append('weather')
                self.logger.info(f"Successfully fetched weather data for {location}")
            except Exception as e:
                self.logger.error(f"Failed to fetch weather data: {str(e)}")
                results['data']['weather'] = None
        
        # Fetch news data
        if 'news' in sources:
            try:
                query = inputs.get('news_query', 'technology')
                news_data = self._fetch_news(query)
                results['data']['news'] = news_data
                results['metadata']['sources_fetched'].append('news')
                self.logger.info(f"Successfully fetched {len(news_data.get('articles', []))} news articles")
            except Exception as e:
                self.logger.error(f"Failed to fetch news data: {str(e)}")
                results['data']['news'] = None
        
        # Check if at least one source was fetched successfully
        if not results['metadata']['sources_fetched']:
            raise APIError(
                self.name,
                "All data sources",
                message="Failed to fetch data from any source"
            )
        
        return results
    
    def _fetch_weather(self, location: str) -> Dict[str, Any]:
        """
        Fetch weather data from OpenWeatherMap API.
        
        Args:
            location: City name
        
        Returns:
            Weather data dictionary
        """
        cache_key = f"weather_{location}"
        
        # Check cache
        if self.cache_enabled and cache_key in self.cache:
            cached_data, cache_time = self.cache[cache_key]
            if datetime.now() - cache_time < timedelta(seconds=self.cache_ttl):
                self.logger.debug(f"Using cached weather data for {location}")
                return cached_data
        
        # Get API configuration from environment or config
        api_key = os.getenv('OPENWEATHER_API_KEY', '')
        
        # Use mock data if no API key is provided or it's a placeholder
        if not api_key or 'your_' in api_key:
            self.logger.warning("No OpenWeatherMap API key found (or placeholder detected), using mock data")
            mock_data = {
                'location': location,
                'temperature': 15.5,
                'description': 'Partly cloudy',
                'humidity': 65,
                'wind_speed': 12.5,
                'mock': True
            }
            # Cache mock data
            if self.cache_enabled:
                self.cache[cache_key] = (mock_data, datetime.now())
            return mock_data
        
        # Fetch from API
        base_url = self.config.get('weather_api_url', 'https://api.openweathermap.org/data/2.5/weather')
        params = {
            'q': location,
            'appid': api_key,
            'units': 'metric'
        }
        timeout = self.config.get('api_timeout', 10)
        
        try:
            response = requests.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            weather_data = {
                'location': data['name'],
                'temperature': data['main']['temp'],
                'description': data['weather'][0]['description'],
                'humidity': data['main']['humidity'],
                'wind_speed': data['wind']['speed'],
                'mock': False
            }
            
            # Cache the result
            if self.cache_enabled:
                self.cache[cache_key] = (weather_data, datetime.now())
            
            return weather_data
            
        except requests.RequestException as e:
            raise APIError(self.name, "OpenWeatherMap", message=str(e))
    
    def _fetch_news(self, query: str) -> Dict[str, Any]:
        """
        Fetch news articles from NewsAPI.
        
        Args:
            query: Search query
        
        Returns:
            News data dictionary with articles
        """
        cache_key = f"news_{query}"
        
        # Check cache
        if self.cache_enabled and cache_key in self.cache:
            cached_data, cache_time = self.cache[cache_key]
            if datetime.now() - cache_time < timedelta(seconds=self.cache_ttl):
                self.logger.debug(f"Using cached news data for query: {query}")
                return cached_data
        
        # Get API configuration
        api_key = os.getenv('NEWS_API_KEY', '')
        
        # Use mock data if no API key is provided or it's a placeholder
        if not api_key or 'your_' in api_key:
            self.logger.warning("No NewsAPI key found (or placeholder detected), using mock data")
            mock_data = {
                'query': query,
                'articles': [
                    {
                        'title': 'AI Revolution in Enterprise Software',
                        'description': 'Companies are increasingly adopting AI-powered solutions to streamline operations.',
                        'content': 'The integration of artificial intelligence in enterprise software has led to significant improvements in efficiency and decision-making processes.',
                        'source': 'Tech News Daily',
                        'publishedAt': datetime.now().isoformat()
                    },
                    {
                        'title': 'Cloud Computing Trends for 2026',
                        'description': 'Latest trends show continued growth in cloud adoption across industries.',
                        'content': 'Cloud computing continues to transform how businesses operate, with multi-cloud strategies becoming the norm.',
                        'source': 'Enterprise Tech',
                        'publishedAt': datetime.now().isoformat()
                    },
                    {
                        'title': 'Cybersecurity Challenges in Modern Enterprises',
                        'description': 'Organizations face increasing threats in the digital landscape.',
                        'content': 'As digital transformation accelerates, cybersecurity remains a top priority for enterprises worldwide.',
                        'source': 'Security Today',
                        'publishedAt': datetime.now().isoformat()
                    }
                ],
                'totalResults': 3,
                'mock': True
            }
            
            # Cache mock data
            if self.cache_enabled:
                self.cache[cache_key] = (mock_data, datetime.now())
            return mock_data
        
        # Fetch from API
        base_url = self.config.get('news_api_url', 'https://newsapi.org/v2/everything')
        params = {
            'q': query,
            'apiKey': api_key,
            'pageSize': 10,
            'sortBy': 'publishedAt'
        }
        timeout = self.config.get('api_timeout', 10)
        
        try:
            response = requests.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            news_data = {
                'query': query,
                'articles': [
                    {
                        'title': article.get('title', ''),
                        'description': article.get('description', ''),
                        'content': article.get('content', article.get('description', '')),
                        'source': article.get('source', {}).get('name', 'Unknown'),
                        'publishedAt': article.get('publishedAt', '')
                    }
                    for article in data.get('articles', [])
                ],
                'totalResults': data.get('totalResults', 0),
                'mock': False
            }
            
            # Cache the result
            if self.cache_enabled:
                self.cache[cache_key] = (news_data, datetime.now())
            
            return news_data
            
        except requests.RequestException as e:
            raise APIError(self.name, "NewsAPI", message=str(e))
    
    def validate_output(self, outputs: Dict[str, Any]) -> None:
        """Validate that outputs contain required data."""
        super().validate_output(outputs)
        
        if 'data' not in outputs:
            raise ValidationError(self.name, "Output must contain 'data' key")
        
        if 'metadata' not in outputs:
            raise ValidationError(self.name, "Output must contain 'metadata' key")
