"""
User preference command handling.
"""

def _is_preference_command(prompt):
    """Check if the prompt is a preference setting command."""
    lower_prompt = prompt.lower().strip()
    return (lower_prompt.startswith("set my name to") or 
            lower_prompt.startswith("call me") or 
            lower_prompt.startswith("my name is") or
            "chat style" in lower_prompt or
            "prefer" in lower_prompt and ("casual" in lower_prompt or "formal" in lower_prompt))

def handle_preference_commands(prompt, user_email, memory_available, set_user_preference_func):
    """
    Handle user preference setting commands.
    
    Args:
        prompt: User's input
        user_email: User's email
        memory_available: Whether memory system is available
        set_user_preference_func: Function to set user preferences
        
    Returns:
        str or None: Response if command was handled, None otherwise
    """
    
    if not _is_preference_command(prompt):
        return None
    
    if not memory_available or not set_user_preference_func:
        return "Preference settings are not available right now."
    
    lower_prompt = prompt.lower().strip()
    
    if lower_prompt.startswith("set my name to") or lower_prompt.startswith("call me"):
        if lower_prompt.startswith("set my name to"):
            name = prompt[14:].strip()
        else:
            name = prompt[8:].strip()
        
        set_user_preference_func("preferred_name", name, user_email)
        return f"Got it! I'll call you {name} from now on."
    
    elif lower_prompt.startswith("my name is"):
        name = prompt[10:].strip()
        set_user_preference_func("preferred_name", name, user_email)
        return f"Nice to meet you, {name}! I'll remember that."
    
    elif "chat style" in lower_prompt:
        if "casual" in lower_prompt:
            set_user_preference_func("chat_style", "casual", user_email)
            return "Switched to casual chat style! 😊"
        elif "formal" in lower_prompt:
            set_user_preference_func("chat_style", "formal", user_email)
            return "Switched to formal chat style."
    
    return "I didn't quite understand that preference. Try 'call me [name]' or 'set chat style to casual/formal'."
