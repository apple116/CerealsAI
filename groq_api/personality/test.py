#!/usr/bin/env python3
"""
Test script to verify all module imports are working correctly.
This script tests the import structure for your Flask app.
"""

import os
import sys
import traceback
from datetime import datetime

def print_separator(title):
    """Print a formatted separator with title"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def test_file_structure():
    """Test that all required files exist"""
    print_separator("TESTING FILE STRUCTURE")
    
    required_files = [
        'app.py',
        'database.py',
        'memory/memory.py',
        'groq_api/__init__.py',
        'groq_api/main.py',
        'groq_api/personality/__init__.py',
        'groq_api/personality/personality_profiler.py',
        'groq_api/personality/personality_manager.py',
        'groq_api/personality/system_prompts.py'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} - EXISTS")
        else:
            print(f"✗ {file_path} - MISSING")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\nWARNING: {len(missing_files)} files are missing!")
        return False
    else:
        print(f"\nSUCCESS: All {len(required_files)} required files exist!")
        return True

def test_python_path():
    """Test Python path configuration"""
    print_separator("TESTING PYTHON PATH")
    
    print("Current working directory:", os.getcwd())
    print("Python path entries:")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")

def test_memory_import():
    """Test importing from memory module"""
    print_separator("TESTING MEMORY MODULE IMPORT")
    
    try:
        # Test direct import
        from memory.memory import get_user_files, load_memory, load_summaries, set_user_preference, get_user_preference
        print("✓ Successfully imported all memory functions")
        
        # Test function calls (if they don't require database)
        try:
            result = get_user_files("test_user")
            print(f"✓ get_user_files('test_user') returned: {type(result)}")
        except Exception as e:
            print(f"⚠ get_user_files test failed: {e}")
            
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import memory module: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_groq_api_import():
    """Test importing from groq_api module"""
    print_separator("TESTING GROQ_API MODULE IMPORT")
    
    try:
        from groq_api import get_groq_response_stream_enhanced
        print("✓ Successfully imported get_groq_response_stream_enhanced")
        return True
    except ImportError as e:
        print(f"✗ Failed to import groq_api: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_personality_profiler_import():
    """Test importing personality profiler with path fixes"""
    print_separator("TESTING PERSONALITY PROFILER IMPORT")
    
    # Method 1: Direct file import
    try:
        import importlib.util
        
        profiler_path = os.path.join('groq_api', 'personality', 'personality_profiler.py')
        print(f"Attempting to load from: {profiler_path}")
        print(f"File exists: {os.path.exists(profiler_path)}")
        
        spec = importlib.util.spec_from_file_location("personality_profiler", profiler_path)
        personality_profiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(personality_profiler)
        
        # Check if required functions exist
        required_functions = ['update_user_personality', 'get_personality_system_prompt', 'get_user_personality_stats']
        for func_name in required_functions:
            if hasattr(personality_profiler, func_name):
                print(f"✓ Found function: {func_name}")
            else:
                print(f"✗ Missing function: {func_name}")
        
        print("✓ Successfully loaded personality_profiler module")
        return True
        
    except Exception as e:
        print(f"✗ Failed to import personality_profiler: {e}")
        print("Traceback:")
        traceback.print_exc()
        return False

def test_personality_package_import():
    """Test importing from personality package after path manipulation"""
    print_separator("TESTING PERSONALITY PACKAGE IMPORT")
    
    try:
        # Get the correct path to groq_api
        current_dir = os.path.dirname(os.path.abspath(__file__))
        groq_api_path = os.path.join(current_dir, 'groq_api')
        
        print(f"Current directory: {current_dir}")
        print(f"Groq API path: {groq_api_path}")
        print(f"Groq API exists: {os.path.exists(groq_api_path)}")
        
        if groq_api_path not in sys.path:
            sys.path.insert(0, groq_api_path)
            print(f"Added to path: {groq_api_path}")
        
        # Check what's in the groq_api directory
        if os.path.exists(groq_api_path):
            print(f"Contents of groq_api: {os.listdir(groq_api_path)}")
            personality_path = os.path.join(groq_api_path, 'personality')
            if os.path.exists(personality_path):
                print(f"Contents of personality: {os.listdir(personality_path)}")
        
        # Try importing from personality package
        from personality.personality_profiler import (
            update_user_personality,
            get_personality_system_prompt,
            get_user_personality_stats
        )
        print("✓ Successfully imported from personality package")
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import from personality package: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_database_import():
    """Test database module import"""
    print_separator("TESTING DATABASE MODULE IMPORT")
    
    try:
        import database
        print("✓ Successfully imported database module")
        
        # Test if database has expected functions/classes
        if hasattr(database, 'get_db'):
            print("✓ Found get_db function")
        else:
            print("⚠ No get_db function found")
            
        return True
    except ImportError as e:
        print(f"✗ Failed to import database: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def main():
    """Run all tests"""
    print(f"Module Import Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing directory: {os.getcwd()}")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Path", test_python_path),
        ("Database Import", test_database_import),
        ("Memory Import", test_memory_import),
        ("Groq API Import", test_groq_api_import),
        ("Personality Profiler Direct Import", test_personality_profiler_import),
        ("Personality Package Import", test_personality_package_import),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            if test_name == "Python Path":
                test_func()  # This test doesn't return a boolean
                results[test_name] = True
            else:
                results[test_name] = test_func()
        except Exception as e:
            print(f"✗ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    # Summary
    print_separator("TEST SUMMARY")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your module structure should work.")
    else:
        print("⚠ Some tests failed. Check the errors above.")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)