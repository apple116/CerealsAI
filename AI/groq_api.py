# groq_api.py
# Simplified version using the new response module
import os
import sys
from duckduckgo_search import DDGS
import datetime

# Fix import paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
modules_dir = os.path.join(parent_dir, "modules")

# Add paths to sys.path if not already there
for path in [current_dir, parent_dir, modules_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import the main response function from the new module
try:
    from modules.core.response import get_groq_response_stream_enhanced, get_groq_response_stream
    print("SUCCESS: Response module imported successfully")
except ImportError as e:
    print(f"ERROR: Could not import response module: {e}")
    # Fallback function
    def get_groq_response_stream_enhanced(prompt, user_email):
        yield "Response module is not available. Please check your system configuration."
    
    get_groq_response_stream = get_groq_response_stream_enhanced

# Import memory functions for backward compatibility
try:
    from memory import (
        load_memory, save_memory, prune_memory, append_to_memory,
        load_summaries, clear_user_memory, get_user_preference, set_user_preference,
        summarize_with_groq, load_real_time_memory, save_real_time_memory
    )
    MEMORY_AVAILABLE = True
    print("SUCCESS: Memory module imported successfully")
except ImportError as e:
    print(f"ERROR: Could not import memory module: {e}")
    MEMORY_AVAILABLE = False

# Legacy search function for backward compatibility
def duckduckgo_search_and_summarize(query, user_email):
    """Search functionality without the 'Searching...' message"""
    
    try:
        search_results = []
        with DDGS() as ddgs:
            for r in ddgs.text(keywords=query, region='wt-wt', max_results=5):
                search_results.append(r)

        if not search_results:
            yield "No relevant search results found."
            if MEMORY_AVAILABLE:
                append_to_memory(query, "No search results found.", user_email)
            return

        snippets = [result["body"] for result in search_results if "body" in result]
        sources = [result["href"] for result in search_results if "href" in result]

        if not snippets:
            yield "Found results, but no extractable content to summarize."
            if MEMORY_AVAILABLE:
                append_to_memory(query, "No extractable content for summarization.", user_email)
            return

        combined_text = " ".join(snippets)
        
        summary_instruction = f"Summarize the following search results for the query '{query}' concisely, extract key points, and list the main sources."
        
        if MEMORY_AVAILABLE:
            summary_info = summarize_with_groq([{"message": combined_text, "role": "system"}], instruction=summary_instruction)
        else:
            summary_info = {"message": f"Search results for '{query}': {combined_text[:500]}..."}

        real_time_entry = {
            "query": query,
            "summary": summary_info.get("message", "Could not generate a summary."),
            "key_points": summary_info.get("key_points", []),
            "sources": sources,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        if MEMORY_AVAILABLE:
            save_real_time_memory(real_time_entry, user_email)
        
        yield f"Here's what I found: {real_time_entry['summary']}"
        if MEMORY_AVAILABLE:
            append_to_memory(query, f"Search result: {real_time_entry['summary']}", user_email)
            
    except Exception as e:
        print(f"Search error: {e}")
        yield "Sorry, I had trouble searching for that information. Please try again."

# Debug information
print(f"Current working directory: {os.getcwd()}")
print(f"Script directory: {current_dir}")
print(f"Modules directory: {modules_dir}")
print("groq_api.py loaded successfully - main functionality moved to modules/core/response.py")