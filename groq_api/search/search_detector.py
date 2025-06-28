"""
Search detection logic to determine when to perform web searches.
"""

def should_perform_search(prompt, user_email, search_detector=None, 
                         search_detector_available=False, memory_available=False,
                         get_user_preference_func=None, load_memory_func=None):
    """
    Determine if a search should be performed based on the prompt.
    
    Args:
        prompt: User's input prompt
        user_email: User's email for context
        search_detector: The search detector instance
        search_detector_available: Whether advanced search detection is available
        memory_available: Whether memory functions are available
        get_user_preference_func: Function to get user preferences
        load_memory_func: Function to load user memory
        
    Returns:
        bool: Whether to perform a search
    """
    
    if search_detector_available and search_detector:
        try:
            # Use intelligent search detector if available
            if hasattr(search_detector, 'should_search'):
                should_search, reason, search_info = search_detector.should_search(prompt)
                return should_search
            else:
                # Use integrate function if available
                from intelligent_search_detector import integrate_with_groq_api
                should_search, reason, search_info = integrate_with_groq_api(
                    prompt, user_email, search_detector, 
                    load_memory_func, get_user_preference_func
                )
                return should_search
        except Exception as e:
            print(f"Search detection error: {e}")
            # Fall back to basic detection
    
    # Basic search detection fallback
    search_terms = [
        'search for', 'look up', 'find information', 'what is happening', 
        'current', 'news', 'latest', 'recent', 'today', 'now'
    ]
    
    lower_prompt = prompt.lower()
    return any(term in lower_prompt for term in search_terms)