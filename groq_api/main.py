"""
Main entry point for the Groq API enhanced functionality.
"""

import os
import sys

# Add necessary paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
memory_path = os.path.join(parent_dir, "memory")

for path in [current_dir, parent_dir, memory_path]:
    if path not in sys.path:
        sys.path.insert(0, path)

from .core.message_handler import MessageHandler
from .utils.imports import setup_imports

# Initialize imports and get availability flags
(MEMORY_AVAILABLE, SEARCH_DETECTOR_AVAILABLE, 
 PERSONALITY_AVAILABLE, search_detector) = setup_imports()

# Initialize the main message handler
message_handler = MessageHandler(
    memory_available=MEMORY_AVAILABLE,
    search_detector_available=SEARCH_DETECTOR_AVAILABLE,
    personality_available=PERSONALITY_AVAILABLE,
    search_detector=search_detector
)

def get_groq_response_stream_enhanced(prompt, user_email):
    """Enhanced version with personality profiling and prompt injection protection."""
    yield from message_handler.process_message(prompt, user_email)

# Alias for backward compatibility
get_groq_response_stream = get_groq_response_stream_enhanced