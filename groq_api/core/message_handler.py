"""
Main message processing and streaming handler.
"""

import datetime
from ..security.prompt_injection import is_prompt_injection_attempt, contains_system_info_leak
from ..commands.memory_commands import handle_memory_commands
from ..commands.preference_commands import handle_preference_commands
from ..commands.personality_commands import handle_personality_commands
from ..personality.system_prompts import SystemPromptGenerator
from ..search.search_detector import should_perform_search
from ..search.duckduckgo_search import perform_search_and_summarize
from .api_client import GroqAPIClient
from .config import Config

class MessageHandler:
    """Handles message processing, routing, and streaming responses."""
    
    def __init__(self, memory_available=False, search_detector_available=False, 
                 personality_available=False, search_detector=None):
        self.memory_available = memory_available
        self.search_detector_available = search_detector_available
        self.personality_available = personality_available
        self.search_detector = search_detector
        self.api_client = GroqAPIClient()
        self.system_prompt_generator = SystemPromptGenerator(personality_available)
        
        # Import memory functions if available
        if memory_available:
            self._import_memory_functions()
    
    def _import_memory_functions(self):
        """Import memory functions."""
        try:
            from memory import (
                load_memory, save_memory, append_to_memory, load_summaries,
                clear_user_memory, get_user_preference, set_user_preference,
                load_real_time_memory, save_real_time_memory
            )
            self.load_memory = load_memory
            self.append_to_memory = append_to_memory
            self.load_summaries = load_summaries
            self.clear_user_memory = clear_user_memory
            self.get_user_preference = get_user_preference
            self.set_user_preference = set_user_preference
            self.load_real_time_memory = load_real_time_memory
            self.save_real_time_memory = save_real_time_memory
        except ImportError:
            self.memory_available = False
    
    def process_message(self, prompt, user_email):
        """Main message processing pipeline."""
        
        # 1. Check for prompt injection attempts
        if is_prompt_injection_attempt(prompt):
            response = "That's an interesting thought! But let's keep our chat focused on more general topics. What's on your mind today?"
            yield response
            if self.memory_available:
                self.append_to_memory(prompt, "Redirected prompt injection attempt.", user_email)
            return
        
        # 2. Update personality profile if available
        if self.personality_available:
            self._update_personality_safely(user_email)
        
        # 3. Handle special commands
        command_response = self._handle_commands(prompt, user_email)
        if command_response:
            yield command_response
            return
        
        # 4. Check for search requirements
        if should_perform_search(prompt, user_email, self.search_detector, 
                                self.search_detector_available, self.memory_available,
                                self.get_user_preference if self.memory_available else None,
                                self.load_memory if self.memory_available else None):
            yield from perform_search_and_summarize(prompt, user_email, self.memory_available,
                                                   self.load_real_time_memory if self.memory_available else None,
                                                   self.save_real_time_memory if self.memory_available else None,
                                                   self.append_to_memory if self.memory_available else None)
            return
        
        # 5. Process normal chat message
        yield from self._process_chat_message(prompt, user_email)
    
    def _update_personality_safely(self, user_email):
        """Safely update personality profile."""
        try:
            from personality_profiler import update_user_personality
            update_user_personality(user_email)
        except Exception as e:
            print(f"Personality update warning: {e}")
    
    def _handle_commands(self, prompt, user_email):
        """Handle special commands (memory, preferences, personality)."""
        
        # Memory commands
        response = handle_memory_commands(prompt, user_email, self.memory_available,
                                        self.clear_user_memory if self.memory_available else None)
        if response:
            return response
        
        # Preference commands
        response = handle_preference_commands(prompt, user_email, self.memory_available,
                                            self.set_user_preference if self.memory_available else None)
        if response:
            if self.memory_available:
                self.append_to_memory(prompt, response, user_email)
            return response
        
        # Personality commands
        response = handle_personality_commands(prompt, user_email, self.personality_available)
        if response:
            if self.memory_available:
                self.append_to_memory(prompt, response, user_email)
            return response
        
        return None
    
    def _process_chat_message(self, prompt, user_email):
        """Process a normal chat message through the API."""
        
        # Build message context
        messages = self._build_message_context(prompt, user_email)
        
        try:
            ai_response = ""
            
            # Stream response from API
            for content in self.api_client.get_completion_stream(messages):
                # Filter out potential system info leaks
                if not contains_system_info_leak(content):
                    yield content
                    ai_response += content
                else:
                    print(f"DEBUG: Filtered out potential leak: '{content}'")
                    fallback = "I'm sorry, I cannot discuss that particular topic. What else can we chat about?"
                    yield fallback
                    ai_response += fallback
                    break
            
            # Save conversation to memory
            if self.memory_available:
                self.append_to_memory(prompt, ai_response, user_email)
                
        except Exception as e:
            print(f"Streaming error: {e}")
            error_msg = "Sorry, I'm having trouble processing that right now. Can we talk about something else?"
            yield error_msg
            if self.memory_available:
                self.append_to_memory(prompt, error_msg, user_email)
    
    def _build_message_context(self, prompt, user_email):
        """Build the context messages for the API call."""
        
        # Get user preferences
        user_prefs = (self.get_user_preference("chat_style", user_email) or Config.DEFAULT_CHAT_STYLE 
                     if self.memory_available else Config.DEFAULT_CHAT_STYLE)
        user_name = (self.get_user_preference("preferred_name", user_email) or Config.DEFAULT_USER_NAME 
                    if self.memory_available else Config.DEFAULT_USER_NAME)
        
        # Generate system prompt
        system_content = self.system_prompt_generator.generate_system_prompt(
            user_email, user_name, user_prefs
        )
        
        # Build messages
        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation summaries if available
        if self.memory_available:
            summaries = self.load_summaries(user_email)
            if summaries:
                messages.append({"role": "system", "content": "Previous conversation context (for continuity):"})
                for summary in summaries:
                    messages.append({"role": "system", "content": summary["message"]})
        
        # Add recent memory if available
        if self.memory_available:
            memory = self.load_memory(user_email)
            if memory:
                messages.append({"role": "system", "content": "Recent conversation:"})
                for item in memory:
                    role = "user" if item.get("role") == "user" else "assistant"
                    messages.append({"role": role, "content": item["message"]})
        
        # Add current user message
        messages.append({"role": "user", "content": prompt})
        
        return messages