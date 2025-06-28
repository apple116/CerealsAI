"""
Personality-related command handling.
"""

def _is_personality_command(prompt):
    """Check if the prompt is a personality-related command."""
    lower_prompt = prompt.lower().strip()
    personality_commands = [
        "show my personality", "personality profile", "my communication style",
        "how do I talk", "analyze my personality", "personality stats"
    ]
    return any(cmd in lower_prompt for cmd in personality_commands)

def handle_personality_commands(prompt, user_email, personality_available):
    """
    Handle personality-related commands.
    
    Args:
        prompt: User's input
        user_email: User's email
        personality_available: Whether personality system is available
        
    Returns:
        str or None: Response if command was handled, None otherwise
    """
    
    if not _is_personality_command(prompt):
        return None
    
    if not personality_available:
        return "Personality profiling is not available right now. Please check your system configuration."
    
    lower_prompt = prompt.lower().strip()
    
    if any(cmd in lower_prompt for cmd in ["show my personality", "personality profile", "personality stats"]):
        try:
            from personality_profiler import get_user_personality_stats
            stats = get_user_personality_stats(user_email)
            
            if not stats:
                return "I haven't analyzed your personality yet. Keep chatting with me and I'll learn your communication style!"
            
            traits = stats.get("personality_traits", {})
            interests = stats.get("interests", [])
            
            response = "Here's what I've learned about your communication style:\n\n"
            
            # Format personality traits
            trait_descriptions = {
                'formality': ('Very casual 🤙', 'Somewhat casual', 'Balanced', 'Somewhat formal', 'Very formal 🎩'),
                'verbosity': ('Brief & concise', 'Somewhat brief', 'Balanced', 'Somewhat detailed', 'Very detailed 📝'),
                'emotiveness': ('Analytical 🔬', 'Somewhat analytical', 'Balanced', 'Somewhat emotional', 'Very emotional ❤️'),
                'humor': ('Serious 😐', 'Somewhat serious', 'Balanced', 'Somewhat humorous', 'Very humorous 😄'),
                'curiosity': ('Passive', 'Somewhat passive', 'Balanced', 'Somewhat curious', 'Very curious 🤔'),
                'directness': ('Indirect', 'Somewhat indirect', 'Balanced', 'Somewhat direct', 'Very direct 🎯'),
                'politeness': ('Blunt', 'Somewhat blunt', 'Balanced', 'Somewhat polite', 'Very polite 🙏'),
                'creativity': ('Practical', 'Somewhat practical', 'Balanced', 'Somewhat creative', 'Very creative 🎨')
            }
            
            for trait, value in traits.items():
                if trait in trait_descriptions:
                    index = min(4, int(value * 5))
                    description = trait_descriptions[trait][index]
                    response += f"• {trait.title()}: {description}\n"
            
            if interests:
                response += f"\nYour main interests: {', '.join(interests[:5])}\n"
            
            response += f"\nBased on {stats.get('message_count', 0)} messages across {stats.get('conversation_count', 0)} conversations."
            
            return response
            
        except Exception as e:
            print(f"Error getting personality stats: {e}")
            return "Sorry, I had trouble accessing your personality profile. Please try again later."
    
    return "I can show you your personality profile by saying 'show my personality' or 'personality stats'."

# ===========================================================================================

# groq_api/utils/__init__.py
"""
Utility functions and import handling.
"""

from .imports import setup_imports
from .helpers import format_date, truncate_text

__all__ = ["setup_imports", "format_date", "truncate_text"]