# personality_profiler.py
import json
import os
import re
import requests
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import statistics
from memory import get_user_files, load_memory, load_summaries, set_user_preference, get_user_preference

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

class PersonalityProfiler:
    def __init__(self):
        self.personality_traits = {
            'formality': 0.5,  # 0 = very casual, 1 = very formal
            'verbosity': 0.5,  # 0 = brief, 1 = verbose
            'emotiveness': 0.5,  # 0 = analytical, 1 = emotional
            'humor': 0.5,  # 0 = serious, 1 = humorous
            'directness': 0.5,  # 0 = indirect, 1 = direct
            'curiosity': 0.5,  # 0 = passive, 1 = questioning
            'politeness': 0.5,  # 0 = blunt, 1 = polite
            'creativity': 0.5,  # 0 = practical, 1 = creative
        }
        
        # Common patterns for analysis
        self.formal_indicators = [
            r'\b(please|thank you|kindly|would you|could you|may I)\b',
            r'\b(sir|madam|mr\.|ms\.|dr\.)\b',
            r'\b(appreciate|grateful|assistance|regarding)\b'
        ]
        
        self.casual_indicators = [
            r'\b(hey|hi|sup|yo|nah|yeah|ok|cool|awesome)\b',
            r'\b(gonna|wanna|gotta|dunno|kinda|sorta)\b',
            r'[!]{2,}|[?]{2,}',  # Multiple punctuation
            r'\b(lol|lmao|omg|wtf|tbh|imo)\b'
        ]
        
        self.emotional_indicators = [
            r'\b(love|hate|amazing|terrible|excited|worried|sad|happy)\b',
            r'[!]{1,}',  # Exclamation marks
            r'\b(feel|feeling|felt|emotions?|heart)\b',
            r'😀|😂|😭|😍|😔|😡|❤️|💔'  # Emojis
        ]
        
        self.humor_indicators = [
            r'\b(haha|lol|funny|joke|kidding|lmao)\b',
            r'😂|😆|🤣|😄|😁',
            r'\b(sarcasm|irony|witty|clever)\b'
        ]
        
        self.question_indicators = [
            r'\?',
            r'\b(what|why|how|when|where|who)\b',
            r'\b(curious|wonder|interested|explain)\b'
        ]

    def analyze_message_patterns(self, messages):
        """Analyze user messages for personality traits"""
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        
        if not user_messages:
            return self.personality_traits.copy()
        
        total_messages = len(user_messages)
        traits = self.personality_traits.copy()
        
        # Analyze each message
        formal_count = casual_count = 0
        emotional_count = analytical_count = 0
        humor_count = serious_count = 0
        question_count = 0
        total_words = 0
        total_chars = 0
        punctuation_count = 0
        
        for msg in user_messages:
            text = msg.get('message', '').lower()
            words = text.split()
            
            total_words += len(words)
            total_chars += len(text)
            
            # Count punctuation for directness
            punctuation_count += len(re.findall(r'[.!?]', text))
            
            # Formality analysis
            formal_matches = sum(len(re.findall(pattern, text)) for pattern in self.formal_indicators)
            casual_matches = sum(len(re.findall(pattern, text)) for pattern in self.casual_indicators)
            
            if formal_matches > casual_matches:
                formal_count += 1
            elif casual_matches > formal_matches:
                casual_count += 1
            
            # Emotional analysis
            emotional_matches = sum(len(re.findall(pattern, text)) for pattern in self.emotional_indicators)
            if emotional_matches > 0:
                emotional_count += 1
            else:
                analytical_count += 1
            
            # Humor analysis
            humor_matches = sum(len(re.findall(pattern, text)) for pattern in self.humor_indicators)
            if humor_matches > 0:
                humor_count += 1
            else:
                serious_count += 1
            
            # Question analysis
            question_matches = sum(len(re.findall(pattern, text)) for pattern in self.question_indicators)
            if question_matches > 0:
                question_count += 1
        
        # Calculate traits
        if formal_count + casual_count > 0:
            traits['formality'] = formal_count / (formal_count + casual_count)
        
        if total_words > 0:
            avg_words_per_message = total_words / total_messages
            traits['verbosity'] = min(1.0, avg_words_per_message / 50)  # Normalize to 50 words
        
        if emotional_count + analytical_count > 0:
            traits['emotiveness'] = emotional_count / (emotional_count + analytical_count)
        
        if humor_count + serious_count > 0:
            traits['humor'] = humor_count / (humor_count + serious_count)
        
        traits['curiosity'] = min(1.0, question_count / total_messages)
        
        # Directness based on punctuation and message length
        if total_messages > 0:
            avg_chars = total_chars / total_messages
            traits['directness'] = min(1.0, punctuation_count / total_messages) * (1 - min(1.0, avg_chars / 200))
        
        # Politeness (inverse of directness but considering formal language)
        traits['politeness'] = (traits['formality'] + (1 - traits['directness'])) / 2
        
        # Creativity (based on vocabulary diversity and unusual expressions)
        if total_words > 0:
            all_words = []
            for msg in user_messages:
                all_words.extend(msg.get('message', '').lower().split())
            
            unique_words = len(set(all_words))
            traits['creativity'] = min(1.0, unique_words / total_words * 2)  # Vocabulary diversity
        
        return traits

    def analyze_conversation_topics(self, messages, summaries):
        """Analyze conversation topics and interests"""
        all_text = ""
        
        # Combine messages and summaries
        for msg in messages:
            if msg.get('role') == 'user':
                all_text += msg.get('message', '') + " "
        
        for summary in summaries:
            all_text += summary.get('message', '') + " "
        
        # Use Groq to analyze interests and topics
        return self._analyze_interests_with_groq(all_text)

    def _analyze_interests_with_groq(self, text):
        """Use Groq API to analyze user interests and communication style"""
        if not text.strip():
            return {"interests": [], "communication_style": "neutral"}
        
        prompt = f"""Analyze the following text and extract:
1. Main interests and topics the person talks about
2. Communication style (formal/casual, emotional/analytical, direct/indirect)
3. Personality indicators (humor, curiosity, creativity, politeness)

Text: {text[:2000]}  # Limit text length

Respond in JSON format:
{{
    "interests": ["interest1", "interest2", ...],
    "communication_style": "description",
    "personality_indicators": {{
        "humor_level": 0.0-1.0,
        "curiosity_level": 0.0-1.0,
        "formality_level": 0.0-1.0,
        "emotional_level": 0.0-1.0
    }},
    "common_phrases": ["phrase1", "phrase2", ...],
    "preferred_topics": ["topic1", "topic2", ...]
}}"""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "stream": False
        }

        try:
            response = requests.post(GROQ_API_URL, json=data, headers=headers)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            
            # Try to extract JSON from response
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"interests": [], "communication_style": "neutral"}
                
        except Exception as e:
            print(f"Interest analysis error: {e}")
            return {"interests": [], "communication_style": "neutral"}

    def generate_personality_profile(self, user_email):
        """Generate comprehensive personality profile for user"""
        # Load user data
        memory = load_memory(user_email)
        summaries = load_summaries(user_email)
        
        # Analyze patterns
        traits = self.analyze_message_patterns(memory)
        interests_data = self.analyze_conversation_topics(memory, summaries)
        
        # Create comprehensive profile
        profile = {
            "personality_traits": traits,
            "interests": interests_data.get("interests", []),
            "communication_style": interests_data.get("communication_style", "neutral"),
            "common_phrases": interests_data.get("common_phrases", []),
            "preferred_topics": interests_data.get("preferred_topics", []),
            "groq_personality_indicators": interests_data.get("personality_indicators", {}),
            "last_updated": datetime.now().isoformat(),
            "message_count": len([m for m in memory if m.get('role') == 'user']),
            "conversation_count": len(summaries)
        }
        
        return profile

    def save_personality_profile(self, profile, user_email):
        """Save personality profile to user's data file"""
        user_dir, _, _, pref_file = get_user_files(user_email)
        os.makedirs(user_dir, exist_ok=True)
        
        # Load existing preferences
        try:
            with open(pref_file, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"email": user_email, "created_at": datetime.now().isoformat()}
        
        # Update with personality profile
        data["personality_profile"] = profile
        data["last_personality_update"] = datetime.now().isoformat()
        
        with open(pref_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_personality_profile(self, user_email):
        """Get personality profile for user"""
        _, _, _, pref_file = get_user_files(user_email)
        try:
            with open(pref_file, 'r') as f:
                data = json.load(f)
            return data.get("personality_profile", {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def should_update_profile(self, user_email):
        """Check if personality profile should be updated"""
        profile = self.get_personality_profile(user_email)
        
        if not profile:
            return True
        
        # Update if last update was more than 7 days ago
        last_update = profile.get("last_updated")
        if last_update:
            last_update_date = datetime.fromisoformat(last_update)
            if datetime.now() - last_update_date > timedelta(days=7):
                return True
        
        # Update if significant new conversation activity
        current_message_count = len([m for m in load_memory(user_email) if m.get('role') == 'user'])
        profile_message_count = profile.get("message_count", 0)
        
        if current_message_count > profile_message_count + 10:  # 10 new messages
            return True
        
        return False

    def generate_personality_prompt(self, user_email):
        """Generate a personality-based system prompt for the AI"""
        profile = self.get_personality_profile(user_email)
        
        if not profile:
            return "You are Cereal, a helpful AI assistant. Keep responses conversational and engaging."
        
        traits = profile.get("personality_traits", {})
        interests = profile.get("interests", [])
        common_phrases = profile.get("common_phrases", [])
        
        # Build personality-based prompt
        prompt_parts = ["You are Cereal, a helpful AI assistant. Adapt your communication style to match the user's personality:"]
        
        # Formality
        formality = traits.get("formality", 0.5)
        if formality > 0.7:
            prompt_parts.append("- Use formal, polite language with proper grammar")
        elif formality < 0.3:
            prompt_parts.append("- Use casual, relaxed language with contractions and informal expressions")
        
        # Verbosity
        verbosity = traits.get("verbosity", 0.5)
        if verbosity > 0.7:
            prompt_parts.append("- Provide detailed, comprehensive responses")
        elif verbosity < 0.3:
            prompt_parts.append("- Keep responses brief and to the point")
        
        # Emotiveness
        emotiveness = traits.get("emotiveness", 0.5)
        if emotiveness > 0.6:
            prompt_parts.append("- Use emotional language and express enthusiasm")
        elif emotiveness < 0.4:
            prompt_parts.append("- Keep responses analytical and factual")
        
        # Humor
        humor = traits.get("humor", 0.5)
        if humor > 0.6:
            prompt_parts.append("- Include appropriate humor and light-hearted comments")
        
        # Interests
        if interests:
            prompt_parts.append(f"- The user is interested in: {', '.join(interests[:5])}")
        
        # Common phrases
        if common_phrases:
            prompt_parts.append(f"- The user commonly uses phrases like: {', '.join(common_phrases[:3])}")
        
        return "\n".join(prompt_parts)


# Helper functions to integrate with existing system

def update_user_personality(user_email):
    """Update personality profile for user if needed"""
    profiler = PersonalityProfiler()
    
    if profiler.should_update_profile(user_email):
        profile = profiler.generate_personality_profile(user_email)
        profiler.save_personality_profile(profile, user_email)
        return True
    return False

def get_personality_system_prompt(user_email):
    """Get personality-based system prompt for user"""
    profiler = PersonalityProfiler()
    return profiler.generate_personality_prompt(user_email)

def get_user_personality_stats(user_email):
    """Get personality statistics for user"""
    profiler = PersonalityProfiler()
    return profiler.get_personality_profile(user_email)