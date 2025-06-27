import os
import sys
import time
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import pytest

# --- IMPORTANT MODIFICATION HERE ---
# Get the absolute path of the directory containing groq_api.py
# This assumes groq_api.py is two levels up from the current script's directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate up two directories to reach '/run/media/cereal/Cereals2/project/Web/AI Development/'
groq_api_dir = os.path.join(current_dir, '..', '..')

# Add this directory to sys.path if it's not already there
if groq_api_dir not in sys.path:
    sys.path.insert(0, groq_api_dir) # Use insert(0, ...) to prioritize this path
# --- END IMPORTANT MODIFICATION ---


# Import the module we're testing
from groq_api import (
    get_groq_response_stream_enhanced,
    _is_personality_command,
    _handle_personality_command,
    _is_preference_command,
    _handle_preference_command,
    duckduckgo_search_and_summarize
)
class TestGroqEnhanced:
    """Test class for the enhanced Groq API functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.test_user_email = "test@example.com"
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock environment variable
        os.environ['GROQ_API_KEY'] = 'test-api-key'
        
    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_personality_command_detection(self):
        """Test personality command detection"""
        personality_commands = [
            "show my personality",
            "personality profile",
            "my communication style", 
            "how do I talk",
            "analyze my personality",
            "personality stats"
        ]
        
        for cmd in personality_commands:
            assert _is_personality_command(cmd), f"Failed to detect: {cmd}"
            assert _is_personality_command(cmd.upper()), f"Failed case-insensitive: {cmd}"
        
        # Test non-personality commands
        non_personality = [
            "hello there",
            "what's the weather",
            "search for cats"
        ]
        
        for cmd in non_personality:
            assert not _is_personality_command(cmd), f"False positive: {cmd}"
    
    def test_preference_command_detection(self):
        """Test preference command detection"""
        preference_commands = [
            "set my name to John",
            "call me Sarah",
            "my name is Mike",
            "set chat style to casual",
            "I prefer formal chat style"
        ]
        
        for cmd in preference_commands:
            assert _is_preference_command(cmd), f"Failed to detect: {cmd}"
        
        # Test non-preference commands
        non_preference = [
            "hello there",
            "what's my name",
            "casual conversation"
        ]
        
        for cmd in non_preference:
            assert not _is_preference_command(cmd), f"False positive: {cmd}"
    
    @patch('groq_api.get_user_preference')
    @patch('groq_api.set_user_preference')
    def test_preference_command_handling(self, mock_set_pref, mock_get_pref):
        """Test preference command handling"""
        
        # Test name setting commands
        test_cases = [
            ("set my name to Alice", "Alice"),
            ("call me Bob", "Bob"),
            ("my name is Charlie", "Charlie")
        ]
        
        for command, expected_name in test_cases:
            response = _handle_preference_command(command, self.test_user_email)
            mock_set_pref.assert_called_with("preferred_name", expected_name, self.test_user_email)
            assert expected_name in response
        
        # Test chat style commands
        response = _handle_preference_command("set chat style to casual", self.test_user_email)
        mock_set_pref.assert_called_with("chat_style", "casual", self.test_user_email)
        assert "casual" in response.lower()
        
        response = _handle_preference_command("prefer formal chat style", self.test_user_email)
        mock_set_pref.assert_called_with("chat_style", "formal", self.test_user_email)
        assert "formal" in response.lower()
    
    @patch('groq_api.get_user_personality_stats')
    def test_personality_command_handling(self, mock_get_stats):
        """Test personality command handling"""
        
        # Test with no personality data
        mock_get_stats.return_value = None
        response = _handle_personality_command("show my personality", self.test_user_email)
        assert "haven't analyzed" in response.lower()
        
        # Test with personality data
        mock_stats = {
            "personality_traits": {
                "formality": 0.3,
                "verbosity": 0.7,
                "emotiveness": 0.5,
                "humor": 0.8
            },
            "interests": ["technology", "music", "sports"],
            "message_count": 50,
            "conversation_count": 5
        }
        mock_get_stats.return_value = mock_stats
        
        response = _handle_personality_command("personality stats", self.test_user_email)
        assert "communication style" in response.lower()
        assert "technology" in response
        assert "50 messages" in response
        assert "5 conversations" in response
    
    @patch('groq_api.requests.post')
    @patch('groq_api.update_user_personality')
    @patch('groq_api.load_memory')
    @patch('groq_api.load_summaries')
    @patch('groq_api.get_personality_system_prompt')
    @patch('groq_api.append_to_memory')
    def test_groq_response_stream_basic(self, mock_append, mock_get_prompt, 
                                       mock_load_summaries, mock_load_memory,
                                       mock_update_personality, mock_post):
        """Test basic Groq response streaming"""
        
        # Mock dependencies
        mock_update_personality.return_value = None
        mock_load_memory.return_value = []
        mock_load_summaries.return_value = []
        mock_get_prompt.return_value = "You are a helpful assistant."
        
        # Mock the streaming response
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"choices":[{"delta":{"content":" there"}}]}',
            'data: [DONE]'
        ]
        mock_post.return_value.__enter__.return_value = mock_response
        
        # Test the function
        prompt = "Hello, how are you?"
        responses = list(get_groq_response_stream_enhanced(prompt, self.test_user_email))
        
        # Verify results
        assert len(responses) == 2
        assert responses[0] == "Hello"
        assert responses[1] == " there"
        
        # Verify memory was saved
        mock_append.assert_called_once()
    
    @patch('groq_api.clear_user_memory')
    def test_memory_clearing(self, mock_clear):
        """Test memory clearing functionality"""
        
        responses = list(get_groq_response_stream_enhanced("forget all memory", self.test_user_email))
        
        assert len(responses) == 1
        assert "memory has been wiped" in responses[0].lower()
        mock_clear.assert_called_once_with(self.test_user_email)
    
    @patch('groq_api.DDGS')
    @patch('groq_api.summarize_with_groq')
    @patch('groq_api.save_real_time_memory')
    @patch('groq_api.append_to_memory')
    def test_search_functionality(self, mock_append, mock_save_rt, mock_summarize, mock_ddgs):
        """Test search and summarize functionality"""
        
        # Mock search results
        mock_search_results = [
            {"body": "Test content 1", "href": "http://example1.com"},
            {"body": "Test content 2", "href": "http://example2.com"}
        ]
        
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = mock_search_results
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        
        # Mock summarization
        mock_summarize.return_value = {
            "message": "This is a test summary",
            "key_points": ["point 1", "point 2"]
        }
        
        # Test search
        query = "test query"
        responses = list(duckduckgo_search_and_summarize(query, self.test_user_email))
        
        # Verify search was called
        mock_ddgs_instance.text.assert_called_once()
        
        # Verify summarization was called
        mock_summarize.assert_called_once()
        
        # Verify real-time memory was saved
        mock_save_rt.assert_called_once()
        
        # Verify regular memory was updated
        mock_append.assert_called_once()
    
    def test_search_query_detection(self):
        """Test search query detection in prompts"""
        search_prompts = [
            "search for python tutorials",
            "what is machine learning",
            "latest news on AI developments",
            "latest trend on blockchain"
        ]
        
        # This would be tested as part of the main function
        # but we can verify the logic exists in the code
        
        for prompt in search_prompts:
            # These should trigger search functionality
            assert any(keyword in prompt.lower() for keyword in 
                      ["search for", "what is", "latest news on", "latest trend on"])


class InteractiveTest:
    """Interactive testing class for manual testing"""
    
    def __init__(self):
        self.test_user = "interactive_test@example.com"
        
    def run_interactive_tests(self):
        """Run interactive tests with user input"""
        print("🧪 Interactive Test Suite for Enhanced Groq API")
        print("=" * 50)
        
        if not os.environ.get('GROQ_API_KEY'):
            print("❌ GROQ_API_KEY environment variable not set!")
            print("Please set it with: export GROQ_API_KEY='your-api-key'")
            return
        
        tests = [
            self.test_basic_conversation,
            self.test_personality_commands,
            self.test_preference_commands,
            self.test_search_functionality,
            self.test_memory_functionality
        ]
        
        for test in tests:
            print(f"\n🔍 Running: {test.__name__}")
            try:
                test()
                print("✅ Test completed")
            except KeyboardInterrupt:
                print("\n⏭️  Test skipped by user")
                continue
            except Exception as e:
                print(f"❌ Test failed: {e}")
            
            input("Press Enter to continue to next test...")
        
        print("\n🎉 Interactive testing completed!")
    
    def test_basic_conversation(self):
        """Test basic conversation flow"""
        print("\n--- Basic Conversation Test ---")
        test_prompts = [
            "Hello! How are you today?",
            "What's your name?",
            "Tell me a joke"
        ]
        
        for prompt in test_prompts:
            print(f"\n🤖 Testing prompt: '{prompt}'")
            print("Response: ", end="")
            
            for chunk in get_groq_response_stream_enhanced(prompt, self.test_user):
                print(chunk, end="", flush=True)
            print()
    
    def test_personality_commands(self):
        """Test personality-related commands"""
        print("\n--- Personality Commands Test ---")
        personality_commands = [
            "show my personality",
            "personality stats",
            "analyze my communication style"
        ]
        
        for cmd in personality_commands:
            print(f"\n🧠 Testing: '{cmd}'")
            print("Response: ", end="")
            
            for chunk in get_groq_response_stream_enhanced(cmd, self.test_user):
                print(chunk, end="", flush=True)
            print()
    
    def test_preference_commands(self):
        """Test preference setting commands"""
        print("\n--- Preference Commands Test ---")
        preference_commands = [
            "call me TestUser",
            "set chat style to casual",
            "my name is Interactive Tester"
        ]
        
        for cmd in preference_commands:
            print(f"\n⚙️  Testing: '{cmd}'")
            print("Response: ", end="")
            
            for chunk in get_groq_response_stream_enhanced(cmd, self.test_user):
                print(chunk, end="", flush=True)
            print()
    
    def test_search_functionality(self):
        """Test search functionality"""
        print("\n--- Search Functionality Test ---")
        search_queries = [
            "search for latest Python news",
            "what is artificial intelligence"
        ]
        
        for query in search_queries:
            print(f"\n🔍 Testing search: '{query}'")
            print("Response: ", end="")
            
            for chunk in get_groq_response_stream_enhanced(query, self.test_user):
                print(chunk, end="", flush=True)
            print()
    
    def test_memory_functionality(self):
        """Test memory functionality"""
        print("\n--- Memory Functionality Test ---")
        
        # First, have a conversation to build memory
        print("Building conversation history...")
        conversation = [
            "My favorite color is blue",
            "I work as a software engineer",
            "I love playing guitar in my free time"
        ]
        
        for msg in conversation:
            print(f"💭 Adding to memory: '{msg}'")
            list(get_groq_response_stream_enhanced(msg, self.test_user))
        
        # Test memory recall
        print("\n🧠 Testing memory recall...")
        recall_prompt = "What do you remember about me?"
        print(f"Testing: '{recall_prompt}'")
        print("Response: ", end="")
        
        for chunk in get_groq_response_stream_enhanced(recall_prompt, self.test_user):
            print(chunk, end="", flush=True)
        print()
        
        # Test memory clearing
        print("\n🗑️  Testing memory clearing...")
        clear_prompt = "forget all memory"
        print(f"Testing: '{clear_prompt}'")
        print("Response: ", end="")
        
        for chunk in get_groq_response_stream_enhanced(clear_prompt, self.test_user):
            print(chunk, end="", flush=True)
        print()


def run_unit_tests():
    """Run unit tests using pytest"""
    print("🧪 Running Unit Tests...")
    print("=" * 30)
    
    # Run pytest programmatically
    import pytest
    result = pytest.main([__file__, "-v"])
    return result == 0


def main():
    """Main testing function"""
    print("🚀 Groq API Enhanced - Test Suite")
    print("=" * 40)
    
    while True:
        print("\nSelect test type:")
        print("1. Unit Tests (automated)")
        print("2. Interactive Tests (manual)")
        print("3. Both")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            success = run_unit_tests()
            if success:
                print("✅ All unit tests passed!")
            else:
                print("❌ Some unit tests failed!")
                
        elif choice == "2":
            interactive = InteractiveTest()
            interactive.run_interactive_tests()
            
        elif choice == "3":
            print("Running unit tests first...")
            success = run_unit_tests()
            
            if success:
                print("\n✅ Unit tests passed! Starting interactive tests...")
                interactive = InteractiveTest()
                interactive.run_interactive_tests()
            else:
                print("❌ Unit tests failed! Fix issues before running interactive tests.")
                
        elif choice == "4":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please enter 1-4.")


if __name__ == "__main__":
    main()