"""
Import handling and fallback functionality.
"""

import os
import sys

def setup_imports():
    """
    Setup all necessary imports and return availability flags.
    
    Returns:
        tuple: (memory_available, search_detector_available, personality_available, search_detector)
    """
    
    # Add paths for imports
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parent_dir = os.path.dirname(current_dir)
    memory_path = os.path.join(parent_dir, "memory")
    
    for path in [current_dir, parent_dir, memory_path]:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    # Import memory functions
    memory_available = _setup_memory_imports()
    
    # Import search detector
    search_detector_available, search_detector = _setup_search_detector_imports()
    
    # Import personality profiler
    personality_available = _setup_personality_imports()
    
    print(f"Memory available: {memory_available}")
    print(f"Search detector available: {search_detector_available}")
    print(f"Personality module available: {personality_available}")
    
    return memory_available, search_detector_available, personality_available, search_detector

def _setup_memory_imports():
    """Setup memory imports."""
    try:
        from memory import (
            load_memory, save_memory, prune_memory, append_to_memory,
            load_summaries, clear_user_memory, get_user_preference, set_user_preference,
            summarize_with_groq, load_real_time_memory, save_real_time_memory
        )
        print("SUCCESS: Memory module imported successfully")
        return True
    except ImportError as e:
        print(f"ERROR: Could not import memory module: {e}")
        return False

def _setup_search_detector_imports():
    """Setup search detector imports."""
    try:
        from intelligent_search_detector import IntelligentSearchDetector, integrate_with_groq_api
        search_detector = IntelligentSearchDetector()
        print("SUCCESS: intelligent_search_detector imported successfully")
        return True, search_detector
    except ImportError as e:
        print(f"WARNING: Could not import intelligent_search_detector: {e}")
        
        # Create a basic fallback search detector
        class BasicSearchDetector:
            def should_search(self, prompt, user_context=None):
                # Basic search detection - look for explicit search terms
                search_terms = ['search for', 'look up', 'find information', 'what is happening', 'current', 'news', 'latest']
                lower_prompt = prompt.lower()
                should_search = any(term in lower_prompt for term in search_terms)
                return should_search, "basic_detection", {"query": prompt.strip()}
        
        return False, BasicSearchDetector()

def _setup_personality_imports():
    """Setup personality imports."""
    try:
        from personality_profiler import (
            update_user_personality, get_personality_system_prompt, get_user_personality_stats
        )
        print("SUCCESS: personality_profiler imported successfully")
        return True
    except ImportError as e:
        print(f"WARNING: Could not import personality_profiler: {e}")
        return False
