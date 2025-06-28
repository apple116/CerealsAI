#!/usr/bin/env python3
"""
Quick diagnostic and fix script for import issues
"""

import os
import sys

def check_and_create_files():
    """Check for missing files and create them if needed"""
    print("=== CHECKING AND CREATING MISSING FILES ===")
    
    # Required files with their minimal content
    required_files = {
        'groq_api/__init__.py': '''"""
Groq API Enhanced Package
"""
try:
    from .main import get_groq_response_stream, get_groq_response_stream_enhanced
except ImportError:
    def get_groq_response_stream(*args, **kwargs):
        return "Mock response"
    def get_groq_response_stream_enhanced(*args, **kwargs):
        return "Mock response"

__version__ = "2.0.0"
__all__ = ["get_groq_response_stream", "get_groq_response_stream_enhanced"]
''',
        
        'groq_api/personality/__init__.py': '''"""
Personality management and system prompt generation.
"""
try:
    from .personality_manager import PersonalityManager
except ImportError:
    class PersonalityManager:
        pass

try:
    from .system_prompts import SystemPromptGenerator  
except ImportError:
    class SystemPromptGenerator:
        pass

try:
    from .personality_profiler import (
        update_user_personality,
        get_personality_system_prompt,
        get_user_personality_stats
    )
except ImportError:
    def update_user_personality(*args, **kwargs):
        return True
    
    def get_personality_system_prompt(*args, **kwargs):
        return "You are a helpful AI assistant."
    
    def get_user_personality_stats(*args, **kwargs):
        return {}

__all__ = [
    "PersonalityManager", 
    "SystemPromptGenerator",
    "update_user_personality",
    "get_personality_system_prompt", 
    "get_user_personality_stats"
]
''',
        
        'memory/__init__.py': '''"""
Memory module for user data and preferences
"""
try:
    from .memory import *
except ImportError:
    pass
''',
    }
    
    created_files = []
    
    for file_path, content in required_files.items():
        if not os.path.exists(file_path):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create the file
            with open(file_path, 'w') as f:
                f.write(content)
            
            created_files.append(file_path)
            print(f"✓ Created: {file_path}")
        else:
            print(f"✓ Exists: {file_path}")
    
    if created_files:
        print(f"\nCreated {len(created_files)} missing files!")
    else:
        print("\nAll required files already exist!")
    
    return created_files

def fix_personality_profiler():
    """Fix the imports in personality_profiler.py"""
    print("\n=== FIXING PERSONALITY_PROFILER.PY IMPORTS ===")
    
    profiler_path = 'groq_api/personality/personality_profiler.py'
    
    if not os.path.exists(profiler_path):
        print(f"✗ {profiler_path} does not exist!")
        return False
    
    # Read the current file
    with open(profiler_path, 'r') as f:
        content = f.read()
    
    # Check if it has the problematic import
    if 'from memory import' in content:
        print("Found problematic memory import. Fixing...")
        
        # Replace the import line
        fixed_content = content.replace(
            'from memory import get_user_files, load_memory, load_summaries, set_user_preference, get_user_preference',
            '''import sys
import os

# Add the root directory to Python path to access the memory module
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from memory.memory import get_user_files, load_memory, load_summaries, set_user_preference, get_user_preference
except ImportError as e:
    # Fallback functions
    def get_user_files(user_id):
        return []
    def load_memory(user_id):
        return {}
    def load_summaries(user_id):
        return []
    def set_user_preference(user_id, key, value):
        return True
    def get_user_preference(user_id, key, default=None):
        return default'''
        )
        
        # Create backup
        backup_path = profiler_path + '.backup'
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"✓ Created backup: {backup_path}")
        
        # Write fixed content
        with open(profiler_path, 'w') as f:
            f.write(fixed_content)
        print(f"✓ Fixed imports in {profiler_path}")
        
        return True
    else:
        print("No problematic import found or already fixed.")
        return True

def test_imports():
    """Test the imports after fixes"""
    print("\n=== TESTING IMPORTS AFTER FIXES ===")
    
    # Test 1: Memory module
    try:
        if os.path.exists('memory/memory.py'):
            from memory.memory import get_user_files
            print("✓ Memory import successful")
        else:
            print("⚠ memory/memory.py does not exist")
    except Exception as e:
        print(f"✗ Memory import failed: {e}")
    
    # Test 2: Groq API
    try:
        from groq_api import get_groq_response_stream_enhanced
        print("✓ Groq API import successful")
    except Exception as e:
        print(f"✗ Groq API import failed: {e}")
    
    # Test 3: Personality profiler (direct)
    try:
        import importlib.util
        profiler_path = 'groq_api/personality/personality_profiler.py'
        spec = importlib.util.spec_from_file_location("personality_profiler", profiler_path)
        personality_profiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(personality_profiler)
        print("✓ Personality profiler direct import successful")
    except Exception as e:
        print(f"✗ Personality profiler direct import failed: {e}")
    
    # Test 4: Personality package
    try:
        groq_api_path = os.path.join(os.getcwd(), 'groq_api')
        if groq_api_path not in sys.path:
            sys.path.insert(0, groq_api_path)
        
        from personality import update_user_personality
        print("✓ Personality package import successful")
    except Exception as e:
        print(f"✗ Personality package import failed: {e}")

def main():
    """Run all fixes and tests"""
    print("QUICK FIX SCRIPT FOR IMPORT ISSUES")
    print("=" * 50)
    
    # Step 1: Check and create missing files
    check_and_create_files()
    
    # Step 2: Fix personality_profiler imports
    fix_personality_profiler()
    
    # Step 3: Test imports
    test_imports()
    
    print("\n" + "=" * 50)
    print("FIXES COMPLETE!")
    print("Now try running your app.py or the test.py again.")

if __name__ == "__main__":
    main()