"""
Search functionality including detection and DuckDuckGo integration.
"""

from .search_detector import should_perform_search
from .duckduckgo_search import perform_search_and_summarize

__all__ = ["should_perform_search", "perform_search_and_summarize"]
