# modules/search/duckduckgo.py
"""
DuckDuckGo search functionality for the AI assistant.
Handles web searches, result processing, and real-time memory integration.
"""

import datetime
import os
import sys
from duckduckgo_search import DDGS

# Add memory path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
memory_path = os.path.join(parent_dir, "memory")

if memory_path not in sys.path:
    sys.path.append(memory_path)

# Try to import memory functions
try:
    from memory import (
        append_to_memory, summarize_with_groq, 
        load_real_time_memory, save_real_time_memory
    )
    MEMORY_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Could not import memory module in duckduckgo search: {e}")
    MEMORY_AVAILABLE = False
    
    # Create dummy functions to prevent crashes
    def append_to_memory(user_msg, ai_msg, user_email): pass
    def summarize_with_groq(messages, instruction=""): return {"message": "Summary not available"}
    def load_real_time_memory(user_email): return []
    def save_real_time_memory(entry, user_email): pass


class DuckDuckGoSearch:
    """DuckDuckGo search handler with real-time memory integration."""
    
    def __init__(self):
        self.memory_available = MEMORY_AVAILABLE
    
    def check_real_time_memory(self, search_query, user_email, freshness_hours=24):
        """
        Check if we have recent search results in real-time memory.
        
        Args:
            search_query (str): The search query to check
            user_email (str): User identifier
            freshness_hours (int): How many hours old results are still considered fresh
            
        Returns:
            str or None: Cached result if found and fresh, None otherwise
        """
        if not self.memory_available:
            return None
            
        real_time_memory = load_real_time_memory(user_email)
        freshness_threshold = datetime.timedelta(hours=freshness_hours)
        
        for rt_entry in real_time_memory:
            entry_timestamp_str = rt_entry.get("timestamp")
            if not entry_timestamp_str:
                continue
                
            try:
                entry_timestamp = datetime.datetime.fromisoformat(entry_timestamp_str)
                if datetime.datetime.now() - entry_timestamp < freshness_threshold:
                    # Check if this entry matches our search query
                    if (search_query.lower() in rt_entry["query"].lower() or 
                        any(kp.lower() in search_query.lower() 
                            for kp in rt_entry.get("key_points", []))):
                        return rt_entry['summary']
            except ValueError:
                continue  # Skip invalid timestamps
                
        return None
    
    def perform_search(self, query, max_results=5, region='wt-wt'):
        """
        Perform DuckDuckGo search and return results.
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to fetch
            region (str): Search region
            
        Returns:
            list: Search results
        """
        try:
            search_results = []
            with DDGS() as ddgs:
                for r in ddgs.text(keywords=query, region=region, max_results=max_results):
                    search_results.append(r)
            return search_results
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            return []
    
    def extract_content(self, search_results):
        """
        Extract content and sources from search results.
        
        Args:
            search_results (list): Raw search results
            
        Returns:
            tuple: (snippets, sources)
        """
        snippets = [result["body"] for result in search_results if "body" in result]
        sources = [result["href"] for result in search_results if "href" in result]
        return snippets, sources
    
    def summarize_results(self, snippets, query):
        """
        Summarize search results using Groq.
        
        Args:
            snippets (list): Text snippets from search results
            query (str): Original search query
            
        Returns:
            dict: Summary information
        """
        if not snippets:
            return {"message": "No content available for summarization."}
            
        combined_text = " ".join(snippets)
        summary_instruction = (
            f"Summarize the following search results for the query '{query}' concisely, "
            f"extract key points, and list the main sources."
        )
        
        if self.memory_available:
            return summarize_with_groq(
                [{"message": combined_text, "role": "system"}], 
                instruction=summary_instruction
            )
        else:
            # Fallback summary when memory/Groq summarization isn't available
            truncated_text = combined_text[:500]
            return {
                "message": f"Search results for '{query}': {truncated_text}...",
                "key_points": []
            }
    
    def save_to_real_time_memory(self, query, summary_info, sources, user_email):
        """
        Save search results to real-time memory.
        
        Args:
            query (str): Search query
            summary_info (dict): Summary information
            sources (list): Source URLs
            user_email (str): User identifier
        """
        if not self.memory_available:
            return
            
        real_time_entry = {
            "query": query,
            "summary": summary_info.get("message", "Could not generate a summary."),
            "key_points": summary_info.get("key_points", []),
            "sources": sources,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        save_real_time_memory(real_time_entry, user_email)
    
    def search_and_summarize(self, query, user_email, check_cache=True):
        """
        Complete search and summarization workflow.
        
        Args:
            query (str): Search query
            user_email (str): User identifier
            check_cache (bool): Whether to check real-time memory cache first
            
        Yields:
            str: Search results or status messages
        """
        # Check real-time memory first if enabled
        if check_cache:
            cached_result = self.check_real_time_memory(query, user_email)
            if cached_result:
                yield f"Here's what I found: {cached_result}"
                if self.memory_available:
                    append_to_memory(query, f"Search result: {cached_result}", user_email)
                return
        
        # Perform new search
        search_results = self.perform_search(query)
        
        if not search_results:
            yield "No relevant search results found."
            if self.memory_available:
                append_to_memory(query, "No search results found.", user_email)
            return
        
        # Extract content
        snippets, sources = self.extract_content(search_results)
        
        if not snippets:
            yield "Found results, but no extractable content to summarize."
            if self.memory_available:
                append_to_memory(query, "No extractable content for summarization.", user_email)
            return
        
        # Summarize results
        summary_info = self.summarize_results(snippets, query)
        
        # Save to real-time memory
        self.save_to_real_time_memory(query, summary_info, sources, user_email)
        
        # Yield result
        result_message = f"Here's what I found: {summary_info.get('message', 'Could not generate summary.')}"
        yield result_message
        
        # Save to conversation memory
        if self.memory_available:
            append_to_memory(query, f"Search result: {summary_info.get('message', 'Search completed.')}", user_email)


# Convenience function for backward compatibility
def duckduckgo_search_and_summarize(query, user_email):
    """
    Backward compatibility function for existing code.
    
    Args:
        query (str): Search query
        user_email (str): User identifier
        
    Yields:
        str: Search results
    """
    search_handler = DuckDuckGoSearch()
    yield from search_handler.search_and_summarize(query, user_email)


# Create default instance for easy importing
default_search = DuckDuckGoSearch()