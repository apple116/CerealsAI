# intelligent_search_detector.py
# Simplified version without external dependencies (no spacy/nltk required)

import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

class IntelligentSearchDetector:
    def __init__(self):
        """Initialize the search detector with no external dependencies"""
        pass
    
    def should_search(self, prompt: str, user_context: Dict = None) -> Tuple[bool, str, Dict]:
        """
        Determines if a prompt requires web search or personal response.
        
        Returns:
            (should_search: bool, reason: str, search_info: dict)
        """
        
        # Step 1: Explicit search requests (highest priority)
        explicit_search = self._check_explicit_search_requests(prompt)
        if explicit_search['is_search']:
            return True, "explicit_request", explicit_search
        
        # Step 2: Personal questions (should NOT search)
        personal_question = self._check_personal_questions(prompt)
        if personal_question['is_personal']:
            return False, "personal_question", personal_question
        
        # Step 3: Current events and time-sensitive queries
        current_events = self._check_current_events(prompt)
        if current_events['is_current']:
            return True, "current_events", current_events
        
        # Step 4: Factual information requests
        factual_info = self._check_factual_requests(prompt)
        if factual_info['needs_facts']:
            return True, "factual_information", factual_info
        
        # Step 5: Context-based decisions
        context_decision = self._analyze_context(prompt, user_context)
        if context_decision['has_context']:
            return context_decision['should_search'], "context_based", context_decision
        
        # Default: conversational response
        return False, "conversational", {"type": "general_chat"}
    
    def _check_explicit_search_requests(self, prompt: str) -> Dict:
        """Check for explicit search commands"""
        explicit_patterns = [
            r"search\s+(for\s+)?(.+)",
            r"look\s+up\s+(.+)",
            r"find\s+(information\s+)?(about\s+)?(.+)",
            r"google\s+(.+)",
            r"what\s+can\s+you\s+find\s+(about\s+)?(.+)",
            r"research\s+(.+)",
            r"give\s+me\s+info\s+(on\s+|about\s+)?(.+)",
            r"can\s+you\s+search\s+",
            r"please\s+search\s+",
            r"i\s+need\s+information\s+about"
        ]
        
        lower_prompt = prompt.lower().strip()
        
        for pattern in explicit_patterns:
            match = re.search(pattern, lower_prompt)
            if match:
                # Extract the search query from the match
                query = match.groups()[-1] if match.groups() else prompt
                return {
                    'is_search': True,
                    'query': query.strip(),
                    'confidence': 0.95,
                    'type': 'explicit'
                }
        
        return {'is_search': False}
    
    def _check_personal_questions(self, prompt: str) -> Dict:
        """Detect questions asking about AI's personal preferences/opinions"""
        
        # Patterns that indicate personal questions about the AI
        personal_patterns = [
            r"(what('s| is)\s+)?your?\s+(favourite|favorite|fav)\s+",
            r"what\s+do\s+you\s+(like|enjoy|prefer|think|feel|recommend)",
            r"do\s+you\s+(like|enjoy|have|prefer|think|believe|recommend)",
            r"what('s| is)\s+your\s+(opinion|thought|view|take|preference)",
            r"how\s+do\s+you\s+(feel|think)\s+about",
            r"ur\s+(favourite|favorite|fav)\s+",
            r"tell\s+me\s+(about\s+)?your\s+",
            r"what\s+are\s+you\s+(into|interested)",
            r"describe\s+your\s+",
            r"what\s+would\s+you\s+(choose|pick|recommend)",
            r"if\s+you\s+(had\s+to\s+)?(choose|pick)",
            r"what('s| is)\s+your\s+(style|type|kind)",
            r"which\s+do\s+you\s+(like|prefer)",
            r"what\s+are\s+your\s+",
            r"can\s+you\s+recommend\s+your\s+favorite"
        ]
        
        # Personal topics that should get personal responses
        personal_topics = [
            "music", "song", "movie", "film", "food", "color", "hobby", "interest",
            "book", "game", "sport", "activity", "place", "travel", "style",
            "artist", "band", "genre", "album", "restaurant", "cuisine", "drink",
            "vacation", "holiday", "season", "weather", "animal", "pet"
        ]
        
        # Opinion/preference indicators
        opinion_words = [
            "opinion", "preference", "favorite", "favourite", "like", "dislike",
            "enjoy", "hate", "love", "think", "feel", "believe", "recommend",
            "suggest", "advise", "choose", "pick", "select"
        ]
        
        lower_prompt = prompt.lower().strip()
        
        # Check for personal question patterns
        for pattern in personal_patterns:
            if re.search(pattern, lower_prompt):
                # Check if it's about a personal topic
                has_personal_topic = any(topic in lower_prompt for topic in personal_topics)
                has_opinion_word = any(word in lower_prompt for word in opinion_words)
                
                confidence = 0.9 if has_personal_topic else 0.8 if has_opinion_word else 0.7
                
                return {
                    'is_personal': True,
                    'confidence': confidence,
                    'type': 'personal_preference',
                    'topic': self._extract_topic(lower_prompt, personal_topics),
                    'detected_pattern': pattern
                }
        
        return {'is_personal': False}
    
    def _check_current_events(self, prompt: str) -> Dict:
        """Check for current events and time-sensitive queries"""
        
        current_event_patterns = [
            r"(latest|recent|current|today('s)?|this\s+(week|month))\s+(news|events?|updates?)",
            r"what('s| is)\s+happening\s+(now|today|recently|lately)",
            r"current\s+(status|situation|state)\s+of",
            r"(breaking|recent)\s+news",
            r"(today|yesterday|this\s+week)\s+in",
            r"what('s| is)\s+(new|recent|latest)\s+(with|about|in)",
            r"update\s+on\s+",
            r"(stock|market|price)\s+(today|now|current)",
            r"news\s+about\s+",
            r"current\s+events"
        ]
        
        # Time indicators that suggest current info needed
        time_indicators = [
            "now", "today", "currently", "recent", "latest", "this week",
            "this month", "2024", "2025", "yesterday", "breaking", "live",
            "real-time", "up-to-date", "fresh", "new"
        ]
        
        # Topics that often need current info
        current_topics = [
            "news", "politics", "stock", "weather", "events", "crisis",
            "election", "pandemic", "war", "market", "price", "update",
            "cryptocurrency", "bitcoin", "covid", "virus", "outbreak",
            "government", "president", "minister", "policy", "law"
        ]
        
        lower_prompt = prompt.lower().strip()
        
        # Check patterns
        for pattern in current_event_patterns:
            if re.search(pattern, lower_prompt):
                return {
                    'is_current': True,
                    'confidence': 0.9,
                    'type': 'current_events',
                    'query': prompt.strip()
                }
        
        # Check for time + topic combinations
        has_time_indicator = any(indicator in lower_prompt for indicator in time_indicators)
        has_current_topic = any(topic in lower_prompt for topic in current_topics)
        
        if has_time_indicator and has_current_topic:
            return {
                'is_current': True,
                'confidence': 0.8,
                'type': 'time_sensitive',
                'query': prompt.strip()
            }
        
        return {'is_current': False}
    
    def _check_factual_requests(self, prompt: str) -> Dict:
        """Check for requests that need factual information"""
        
        # Question words that often indicate factual requests
        factual_question_patterns = [
            r"^(what|when|where|who|why|how)\s+(?!do\s+you|are\s+you|would\s+you)",
            r"tell\s+me\s+about\s+(?!your|you)",
            r"explain\s+(?!your|how\s+you)",
            r"define\s+",
            r"what\s+is\s+(?!your)",
            r"how\s+does\s+(?!it\s+feel|that\s+make\s+you)",
            r"when\s+did\s+",
            r"where\s+is\s+",
            r"who\s+is\s+(?!your)",
            r"how\s+to\s+(?!make\s+you|be\s+you)",
            r"what\s+are\s+the\s+(?!your)",
            r"list\s+of\s+",
            r"examples\s+of\s+"
        ]
        
        # Academic/technical topics that usually need facts
        factual_topics = [
            "definition", "history", "science", "technology", "medicine",
            "law", "mathematics", "physics", "chemistry", "biology",
            "geography", "statistics", "data", "research", "study",
            "theory", "concept", "principle", "formula", "equation",
            "university", "college", "education", "academic", "scholarly"
        ]
        
        # Avoid searching for common knowledge/philosophical questions
        common_knowledge = [
            "what is love", "what is happiness", "what is life", "what is death",
            "how to be happy", "how to make friends", "what is art", "what is beauty",
            "what is the meaning of life", "how to be successful", "what is friendship",
            "how to be confident", "what is wisdom", "how to be good person"
        ]
        
        lower_prompt = prompt.lower().strip()
        
        # Skip if it's common knowledge/philosophical
        if any(ck in lower_prompt for ck in common_knowledge):
            return {'needs_facts': False}
        
        # Check factual patterns
        for pattern in factual_question_patterns:
            if re.search(pattern, lower_prompt):
                has_factual_topic = any(topic in lower_prompt for topic in factual_topics)
                
                # Calculate basic specificity (specific terms, numbers, etc.)
                specificity_score = self._calculate_specificity(prompt)
                
                if specificity_score > 0.3 or has_factual_topic:
                    return {
                        'needs_facts': True,
                        'confidence': 0.7 + (specificity_score * 0.2),
                        'type': 'factual_request',
                        'query': prompt.strip()
                    }
        
        return {'needs_facts': False}
    
    def _analyze_context(self, prompt: str, user_context: Dict = None) -> Dict:
        """Analyze user context and conversation history"""
        
        if not user_context:
            return {'has_context': False}
        
        # Check recent conversation for context clues
        recent_messages = user_context.get('recent_messages', [])
        user_preferences = user_context.get('preferences', {})
        
        # If user recently asked for searches, they might expect more
        search_pattern_in_history = False
        if recent_messages:
            last_few = recent_messages[-3:]  # Last 3 messages
            for msg in last_few:
                if any(word in msg.get('message', '').lower() 
                      for word in ['search', 'find', 'look up', 'information']):
                    search_pattern_in_history = True
                    break
        
        # Check user's typical interaction style
        user_style = user_preferences.get('interaction_style', 'balanced')
        
        context_decision = {
            'has_context': True,
            'search_pattern_in_history': search_pattern_in_history,
            'user_style': user_style
        }
        
        # Decision logic based on context
        if search_pattern_in_history and user_style == 'information_seeker':
            context_decision['should_search'] = True
            context_decision['confidence'] = 0.6
        else:
            context_decision['should_search'] = False
            context_decision['confidence'] = 0.5
        
        return context_decision
    
    def _extract_topic(self, prompt: str, topic_list: List[str]) -> Optional[str]:
        """Extract the main topic from a prompt"""
        for topic in topic_list:
            if topic in prompt:
                return topic
        return None
    
    def _calculate_specificity(self, prompt: str) -> float:
        """Calculate how specific a prompt is (0.0 to 1.0) without external libraries"""
        
        # Basic specificity indicators
        specific_indicators = [
            "specific", "exactly", "precisely", "detailed", "comprehensive",
            "thorough", "complete", "full", "entire", "exact", "particular",
            "certain", "definite", "explicit", "clear"
        ]
        
        # Count numbers, capital letters (proper nouns), and specific terms
        numbers = len(re.findall(r'\d+', prompt))
        capitals = len(re.findall(r'[A-Z][a-zA-Z]+', prompt))
        specific_terms = sum(1 for indicator in specific_indicators 
                           if indicator in prompt.lower())
        
        # Calculate specificity
        total_words = len(prompt.split())
        if total_words == 0:
            return 0.0
        
        specificity = (numbers + capitals + specific_terms) / total_words
        return min(specificity, 1.0)

# Integration function for your groq_api.py
def integrate_with_groq_api(prompt: str, user_email: str, detector: IntelligentSearchDetector, 
                           load_memory_func, get_user_preference_func):
    """
    Integration function for your existing groq_api.py
    Call this before your current search logic
    """
    
    # Load user context (using your existing functions)
    user_context = {
        'recent_messages': load_memory_func(user_email)[-5:],  # Last 5 messages
        'preferences': {
            'interaction_style': get_user_preference_func("interaction_style", user_email) or "balanced",
            'chat_style': get_user_preference_func("chat_style", user_email) or "casual"
        }
    }
    
    # Get search decision
    should_search, reason, info = detector.should_search(prompt, user_context)
    
    # Log the decision for debugging
    print(f"🔍 SEARCH DECISION: {should_search}")
    print(f"📝 REASON: {reason}")
    print(f"ℹ️  INFO: {info}")
    
    return should_search, reason, info