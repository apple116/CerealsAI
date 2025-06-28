"""
Personality profiling and management functionality.
"""

class PersonalityManager:
    """Manages user personality profiling and statistics."""
    
    def __init__(self, personality_available=False):
        self.personality_available = personality_available
        
        if personality_available:
            self._import_personality_functions()
    
    def _import_personality_functions(self):
        """Import personality functions if available."""
        try:
            from personality_profiler import (
                update_user_personality, get_personality_system_prompt, 
                get_user_personality_stats
            )
            self.update_user_personality = update_user_personality
            self.get_personality_system_prompt = get_personality_system_prompt
            self.get_user_personality_stats = get_user_personality_stats
        except ImportError:
            self.personality_available = False
    
    def update_personality(self, user_email):
        """Update user personality profile."""
        if not self.personality_available:
            return False
        
        try:
            return self.update_user_personality(user_email)
        except Exception as e:
            print(f"Personality update error: {e}")
            return False
    
    def get_system_prompt(self, user_email):
        """Get personality-based system prompt."""
        if not self.personality_available:
            return "You are Cereal, a helpful AI assistant. Keep responses conversational and engaging."
        
        try:
            return self.get_personality_system_prompt(user_email)
        except Exception as e:
            print(f"Error getting personality system prompt: {e}")
            return "You are Cereal, a helpful AI assistant. Keep responses conversational and engaging."
    
    def get_personality_stats(self, user_email):
        """Get user personality statistics."""
        if not self.personality_available:
            return None
        
        try:
            return self.get_user_personality_stats(user_email)
        except Exception as e:
            print(f"Error getting personality stats: {e}")
            return None