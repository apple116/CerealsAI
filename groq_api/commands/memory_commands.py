"""
Memory-related command handling.
"""

def handle_memory_commands(prompt, user_email, memory_available, clear_user_memory_func):
    """
    Handle memory-related commands.
    
    Args:
        prompt: User's input
        user_email: User's email
        memory_available: Whether memory system is available
        clear_user_memory_func: Function to clear user memory
        
    Returns:
        str or None: Response if command was handled, None otherwise
    """
    
    if prompt.lower().strip() == "forget all memory":
        if memory_available and clear_user_memory_func:
            clear_user_memory_func(user_email)
            return "All your memory has been wiped as you requested."
        else:
            return "Memory system is not available."
    
    return None
