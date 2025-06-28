"""
Groq API client for handling API communications.
"""

import requests
import json
from .config import Config

class GroqAPIClient:
    """Client for communicating with the Groq API."""
    
    def __init__(self):
        self.api_url = Config.GROQ_API_URL
        self.api_key = Config.GROQ_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def get_completion_stream(self, messages, model=None, temperature=None):
        """
        Get streaming completion from Groq API.
        
        Args:
            messages: List of message dictionaries
            model: Model to use (defaults to Config.DEFAULT_MODEL)
            temperature: Temperature setting (defaults to Config.DEFAULT_TEMPERATURE)
            
        Yields:
            str: Streaming content from the API
        """
        data = {
            "model": model or Config.DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature or Config.DEFAULT_TEMPERATURE,
            "stream": True
        }
        
        try:
            with requests.post(self.api_url, json=data, headers=self.headers, stream=True) as response:
                response.raise_for_status()
                
                for line in response.iter_lines(decode_unicode=True):
                    if line and line.startswith("data: "):
                        json_data = line[len("data: "):]
                        if json_data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(json_data)
                            delta = chunk.get('choices', [{}])[0].get('delta', {})
                            content = delta.get('content')
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            print(f"API streaming error: {e}")
            raise
