"""
General utility functions.
"""

import datetime

def format_date(date_obj=None):
    """
    Format a date object to a readable string.
    
    Args:
        date_obj: datetime object (defaults to current time)
        
    Returns:
        str: Formatted date string
    """
    if date_obj is None:
        date_obj = datetime.datetime.now()
    
    return date_obj.strftime("%A, %B %d, %Y")

def truncate_text(text, max_length=500, suffix="..."):
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length (default 500)
        suffix: Suffix to add if truncated (default "...")
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def clean_text(text):
    """
    Clean text by removing extra whitespace and newlines.
    
    Args:
        text: Text to clean
        
    Returns:
        str: Cleaned text
    """
    return ' '.join(text.split())

def extract_command_value(prompt, command_prefix):
    """
    Extract value from a command-style prompt.
    
    Args:
        prompt: Full prompt
        command_prefix: Command prefix to extract from
        
    Returns:
        str: Extracted value
    """
    if prompt.lower().startswith(command_prefix.lower()):
        return prompt[len(command_prefix):].strip()
    return ""

def is_empty_or_whitespace(text):
    """
    Check if text is empty or contains only whitespace.
    
    Args:
        text: Text to check
        
    Returns:
        bool: True if empty or whitespace only
    """
    return not text or text.isspace()

def safe_get_dict_value(dictionary, key, default=None):
    """
    Safely get a value from a dictionary.
    
    Args:
        dictionary: Dictionary to get value from
        key: Key to look for
        default: Default value if key not found
        
    Returns:
        Any: Value from dictionary or default
    """
    if not isinstance(dictionary, dict):
        return default
    
    return dictionary.get(key, default)