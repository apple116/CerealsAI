"""
Prompt injection detection and system information leak prevention.
"""

import re

def is_prompt_injection_attempt(prompt):
    """Detect potential prompt injection attempts using regex patterns."""
    injection_patterns = [
        r"ignore previous instructions",
        r"forget (all )?what I told you",
        r"system prompt(s)?",
        r"you are now",
        r"new instructions",
        r"override( this)?",
        r"jailbreak",
        r"reveal your prompt(s)?",
        r"show me your instructions?",
        r"what are your guidelines?",
        r"disregard (previous )?instructions?",
        r"pretend you are",
        r"act as if",
        r"roleplay as",
        r"simulate",
        r"behave like",
        r"your creator",
        r"your developer",
        r"meta ai",
        r"anthropic",
        r"openai",
        r"what is your base prompt",
        r"tell me about your programming",
        r"what rules do you follow",
        r"how were you trained",
        r"access your internal settings",
        r"debug mode",
        r"print (all )?instructions",
        r"display (all )?rules",
        r"dump context",
        r"give me your initial setup",
        r"explain your directive"
    ]
    
    lower_prompt = prompt.lower()
    for pattern in injection_patterns:
        if re.search(pattern, lower_prompt):
            print(f"DEBUG: Detected prompt injection attempt with pattern: '{pattern}' in prompt: '{prompt}'")
            return True
    return False

def contains_system_info_leak(content):
    """Check if content contains system information that shouldn't be revealed."""
    leak_indicators = [
        r"system prompt(s)?",
        r"instructions?",
        r"guidelines?",
        r"your name is cereal",
        r"personality_prompt",
        r"current_date",
        r"user_prefs",
        r"chat_style",
        r"meta ai",
        r"anthropic",
        r"openai",
        r"base prompt",
        r"my programming",
        r"internal settings",
        r"rules I follow",
        r"how I was trained",
        r"my core directive",
        r"as an ai model",
        r"my pre-programmed response",
        r"my initial setup",
        r"the context I was given",
        r"as a language model",
        r"i am an ai",
        r"my underlying code",
        r"my design"
    ]
    
    lower_content = content.lower()
    for indicator in leak_indicators:
        if re.search(indicator, lower_content):
            return True
    return False