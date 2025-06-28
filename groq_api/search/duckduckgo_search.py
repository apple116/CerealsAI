"""
DuckDuckGo search functionality with real-time memory integration.
"""

import datetime
from duckduckgo_search import DDGS
from ..core.config import Config

def perform_search_and_summarize(query, user_email, memory_available=False,
                                load_real_time_memory_func=None,
                                save_real_time_memory_func=None,
                                append_to_memory_func=None):
    """
    Perform DuckDuckGo search and return summarized results.
    
    Args:
        query: Search query
        user_email: User's email
        memory_available: Whether memory functions are available
        load_real_time_memory_func: Function to load real-time memory
        save_real_time_memory_func: Function to save real-time memory
        append_to_memory_func: Function to append to memory
        
    Yields:
        str: Search results and summary
    """
    
    # Check real-time memory first if available
    if memory_available and load_real_time_memory_func:
        real_time_memory = load_real_time_memory_func(user_email)
        for rt_entry in real_time_memory:
            entry_timestamp_str = rt_entry.get("timestamp")
            if entry_timestamp_str:
                try:
                    entry_timestamp = datetime.datetime.fromisoformat(entry_timestamp_str)
                    freshness_threshold = datetime.timedelta(hours=Config.FRESHNESS_THRESHOLD_HOURS)
                    if datetime.datetime.now() - entry_timestamp < freshness_threshold:
                        if (query.lower() in rt_entry["query"].lower() or 
                            any(kp.lower() in query.lower() for kp in rt_entry.get("key_points", []))):
                            yield f"Here's what I found: {rt_entry['summary']}"
                            if append_to_memory_func:
                                append_to_memory_func(query, f"Search result: {rt_entry['summary']}", user_email)
                            return
                except ValueError:
                    continue  # Skip invalid timestamps
    
    # Perform new search
    try:
        search_results = []
        with DDGS() as ddgs:
            for r in ddgs.text(keywords=query, region=Config.SEARCH_REGION, 
                              max_results=Config.MAX_SEARCH_RESULTS):
                search_results.append(r)

        if not search_results:
            yield "No relevant search results found."
            if memory_available and append_to_memory_func:
                append_to_memory_func(query, "No search results found.", user_email)
            return

        snippets = [result["body"] for result in search_results if "body" in result]
        sources = [result["href"] for result in search_results if "href" in result]

        if not snippets:
            yield "Found results, but no extractable content to summarize."
            if memory_available and append_to_memory_func:
                append_to_memory_func(query, "No extractable content for summarization.", user_email)
            return

        combined_text = " ".join(snippets)
        
        # Generate summary
        summary_info = _generate_search_summary(combined_text, query, memory_available)
        
        # Save to real-time memory if available
        if memory_available and save_real_time_memory_func:
            real_time_entry = {
                "query": query,
                "summary": summary_info.get("message", "Could not generate a summary."),
                "key_points": summary_info.get("key_points", []),
                "sources": sources,
                "timestamp": datetime.datetime.now().isoformat()
            }
            save_real_time_memory_func(real_time_entry, user_email)
        
        summary_text = summary_info.get("message", f"Search results for '{query}': {combined_text[:500]}...")
        yield f"Here's what I found: {summary_text}"
        
        if memory_available and append_to_memory_func:
            append_to_memory_func(query, f"Search result: {summary_text}", user_email)
            
    except Exception as e:
        print(f"Search error: {e}")
        yield "Sorry, I had trouble searching for that information. Please try again."

def _generate_search_summary(combined_text, query, memory_available):
    """Generate a summary of search results."""
    summary_instruction = f"Summarize the following search results for the query '{query}' concisely, extract key points, and list the main sources."
    
    if memory_available:
        try:
            from memory import summarize_with_groq
            return summarize_with_groq([{"message": combined_text, "role": "system"}], 
                                     instruction=summary_instruction)
        except ImportError:
            pass
    
    # Fallback summary
    return {"message": f"Search results for '{query}': {combined_text[:500]}..."}