"""
Configuration and constants for the Groq API package.
"""

import os

class Config:
    """Configuration class for Groq API settings."""
    
    # API Configuration
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    
    # Model Configuration
    DEFAULT_MODEL = "llama3-8b-8192"
    DEFAULT_TEMPERATURE = 0.7
    
    # Memory Configuration
    FRESHNESS_THRESHOLD_HOURS = 24
    
    # Search Configuration
    MAX_SEARCH_RESULTS = 5
    SEARCH_REGION = 'wt-wt'
    
    # Chat Styles
    VALID_CHAT_STYLES = ["casual", "formal"]
    DEFAULT_CHAT_STYLE = "casual"
    DEFAULT_USER_NAME = "there"
