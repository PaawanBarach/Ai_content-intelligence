import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import requests
from typing import List, Dict
from functools import lru_cache
from src.error_handler import ErrorHandler
import time

load_dotenv()

class Config:
    """Enhanced configuration with API health monitoring"""
    @staticmethod
    def _get(name: str, default: str = "") -> str:
        try:
            return st.secrets.get(name, os.getenv(name, default))
        except Exception:
            return os.getenv(name, default)
    
    # API Configuration
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # LLM Settings
    MODEL_NAME = "deepseek/deepseek-r1:free"
    API_BASE_URL = "https://openrouter.ai/api/v1"
    TEMPERATURE = 0
    MAX_TOKENS = 1000
    
    # Performance Settings
    MAX_ARTICLES = 2
    CACHE_TTL = 3600  # 1 hour
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    
    # Rate Limiting
    DAILY_ANALYSIS_LIMIT = 50
    ANALYSIS_COOLDOWN = 10  # seconds
    
    @staticmethod
    def validate_config() -> Dict[str, bool]:
        """Validate configuration and API availability"""
        validation_results = {
            "openrouter_key": bool(Config.OPENROUTER_API_KEY),
            "news_api_key": bool(Config.NEWS_API_KEY),
            "google_api_key": bool(Config.GOOGLE_API_KEY),
            "openrouter_api": False,
            "news_api": False,
            "google_api": False
        }
        
        # Test API connectivity
        try:
            if Config.OPENROUTER_API_KEY:
                response = requests.get(
                    f"{Config.API_BASE_URL}/models",
                    headers={"Authorization": f"Bearer {Config.OPENROUTER_API_KEY}"},
                    timeout=5
                )
                validation_results["openrouter_api"] = response.status_code == 200
        except:
            pass
        
        try:
            if Config.NEWS_API_KEY:
                resp = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={"country": "us", "pageSize": 1, "apiKey": Config.NEWS_API_KEY},
                timeout=6
            )
            validation_results["news_api"] = (resp.status_code == 200)
        except Exception:
            pass

         # Google Fact Check: one Claim Search ping
        try:
            if Config.GOOGLE_API_KEY:
             resp = requests.get(
                "https://factchecktools.googleapis.com/v1alpha1/claims:search",
                params={"key": Config.GOOGLE_API_KEY, "query": "test", "pageSize": 1},
                timeout=6
            )
            validation_results["google_api"] = (resp.status_code == 200)
        except Exception:
            pass
        
        return validation_results

config = Config()

class APIClient:
    """Robust API client with connection pooling and retries"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = config.REQUEST_TIMEOUT
        # Add connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=requests.adapters.Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504]
            )
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with improved retry logic"""
        last_exception = None
        
        for attempt in range(config.MAX_RETRIES):
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 2 ** attempt))
                    time.sleep(min(retry_after, 30))
                    continue
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout:
                last_exception = Exception(f"Request timed out after {config.REQUEST_TIMEOUT}s")
                if attempt < config.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
            except Exception as e:
                last_exception = e
                if attempt < config.MAX_RETRIES - 1:
                    time.sleep(min(2 ** attempt, 10))
                    continue
        
        raise last_exception or Exception("Request failed after retries")

# Enhanced LLM client with error handling
@st.cache_resource
def get_llm_client():
    """Create LLM client with comprehensive error handling"""
    try:
        if not config.OPENROUTER_API_KEY:
            st.error("🔑 OpenRouter API key is required!")
            return None
        
        llm = ChatOpenAI(
            model=config.MODEL_NAME,
            openai_api_key=config.OPENROUTER_API_KEY,
            openai_api_base=config.API_BASE_URL,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
            request_timeout=config.REQUEST_TIMEOUT,
            model_kwargs={"response_format": {"type": "json_object"}}  # Force JSON
        )
        
        # Don't test connection on init - let it fail on first use
        return llm
            
    except Exception as e:
        ErrorHandler.log_error(e, {"component": "llm_initialization"})
        st.error(f"❌ LLM initialization failed: {str(e)}")
        return None

# Enhanced cached API calls with better error handling
@st.cache_data(ttl=config.CACHE_TTL, show_spinner=False)
def cached_news_search(query: str, _client: APIClient = None) -> List[Dict]:
    """Enhanced news search with error handling"""
    if not config.NEWS_API_KEY:
        return []
    
    try:
        client = _client or APIClient()
        response = client._make_request_with_retry(
            "GET",
            "https://newsapi.org/v2/everything",
            params={
                "q": query[:100],
                "pageSize": config.MAX_ARTICLES,
                "apiKey": config.NEWS_API_KEY,
                "sortBy": "relevancy",
                "language": "en"
            }
        )
        
        articles = response.json().get("articles", [])
        return [
            {
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "url": article.get("url", ""),
                "publishedAt": article.get("publishedAt", "")
            }
            for article in articles[:config.MAX_ARTICLES]
        ]
        
    except Exception as e:
        ErrorHandler.handle_api_error(e, "news")
        return []

@st.cache_data(ttl=config.CACHE_TTL, show_spinner=False)
def cached_fact_check(query: str, _client: APIClient = None) -> List[Dict]:
    """Enhanced fact-check with error handling"""
    if not config.GOOGLE_API_KEY:
        return []
    
    try:
        client = _client or APIClient()
        response = client._make_request_with_retry(
            "GET",
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            params={
                "query": query[:100],
                "key": config.GOOGLE_API_KEY,
                "maxAgeDays": 30
            }
        )
        
        claims = response.json().get("claims", [])
        return [
            {
                "text": claim.get("text", ""),
                "claimant": claim.get("claimant", ""),
                "rating": claim.get("claimReview", [{}])[0].get("textualRating", ""),
                "url": claim.get("claimReview", [{}])[0].get("url", "")
            }
            for claim in claims[:3]
        ]
        
    except Exception as e:
        ErrorHandler.handle_api_error(e, "fact_check")
        return []
