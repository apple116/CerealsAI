"""
Personality management and system prompt generation.
"""
from .personality_manager import PersonalityManager
from .system_prompts import SystemPromptGenerator

# Add these lines:
try:
    from .personality_profiler import (
        update_user_personality,
        get_personality_system_prompt,
        get_user_personality_stats
    )
except ImportError:
    # Define fallback functions if personality_profiler doesn't exist or has issues
    def update_user_personality(*args, **kwargs):
        return True
    
    def get_personality_system_prompt(*args, **kwargs):
        return "You are a helpful AI assistant."
    
    def get_user_personality_stats(*args, **kwargs):
        return {}

__all__ = [
    "PersonalityManager", 
    "SystemPromptGenerator",
    "update_user_personality",
    "get_personality_system_prompt", 
    "get_user_personality_stats"
]