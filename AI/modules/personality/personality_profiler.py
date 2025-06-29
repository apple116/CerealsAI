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
        
        # Pre-compile regex patterns for efficiency
        self.formal_patterns = [
            re.compile(r'\b(please|thank you|kindly|would you|could you|may I)\b', re.IGNORECASE),
            re.compile(r'\b(sir|madam|mr\.|ms\.|dr\.)\b', re.IGNORECASE),
            re.compile(r'\b(appreciate|grateful|assistance|regarding)\b', re.IGNORECASE)
        ]
        
        self.casual_patterns = [
            re.compile(r'\b(hey|hi|sup|yo|nah|yeah|ok|cool|awesome)\b', re.IGNORECASE),
            re.compile(r'\b(gonna|wanna|gotta|dunno|kinda|sorta)\b', re.IGNORECASE),
            re.compile(r'[!]{2,}|[?]{2,}'),  # Multiple punctuation
            re.compile(r'\b(lol|lmao|omg|wtf|tbh|imo)\b', re.IGNORECASE)
        ]
        
        self.emotional_patterns = [
            re.compile(r'\b(love|hate|amazing|terrible|excited|worried|sad|happy)\b', re.IGNORECASE),
            re.compile(r'[!]{1,}'),  # Exclamation marks
            re.compile(r'\b(feel|feeling|felt|emotions?|heart)\b', re.IGNORECASE),
            re.compile(r'😀|😂|😭|😍|😔|😡|❤️|💔')  # Emojis
        ]
        
        self.humor_patterns = [
            re.compile(r'\b(haha|lol|funny|joke|kidding|lmao)\b', re.IGNORECASE),
            re.compile(r'😂|😆|🤣|😄|😁'),
            re.compile(r'\b(sarcasm|irony|witty|clever)\b', re.IGNORECASE)
        ]
        
        self.question_patterns = [
            re.compile(r'\?'),
            re.compile(r'\b(what|why|how|when|where|who)\b', re.IGNORECASE),
            re.compile(r'\b(curious|wonder|interested|explain)\b', re.IGNORECASE)
        ]

    def analyze_message_patterns(self, messages):
        """Analyze user messages for personality traits - handles different message formats"""
        # Handle both old format (role key) and new format (no role key, user messages only)
        user_messages = []
        
        for msg in messages:
            # Check if this is a user message
            if isinstance(msg, dict):
                # If it has a role key, check if it's user
                if 'role' in msg and msg['role'] == 'user':
                    user_messages.append(msg)
                # If no role key, assume it's a user message (from memory format)
                elif 'role' not in msg and 'message' in msg:
                    user_messages.append(msg)
        
        print(f"DEBUG: Found {len(user_messages)} user messages out of {len(messages)} total messages")
        
        if not user_messages:
            print("DEBUG: No user messages found, returning default traits")
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
            text = msg.get('message', '')
            if not text:  # Skip empty messages
                continue
                
            words = text.split()
            
            total_words += len(words)
            total_chars += len(text)
            
            # Count punctuation for directness
            punctuation_count += len(re.findall(r'[.!?]', text))
            
            # Formality analysis using pre-compiled patterns
            formal_matches = sum(len(pattern.findall(text)) for pattern in self.formal_patterns)
            casual_matches = sum(len(pattern.findall(text)) for pattern in self.casual_patterns)
            
            if formal_matches > casual_matches:
                formal_count += 1
            elif casual_matches > formal_matches:
                casual_count += 1
            
            # Emotional analysis
            emotional_matches = sum(len(pattern.findall(text)) for pattern in self.emotional_patterns)
            if emotional_matches > 0:
                emotional_count += 1
            else:
                analytical_count += 1
            
            # Humor analysis
            humor_matches = sum(len(pattern.findall(text)) for pattern in self.humor_patterns)
            if humor_matches > 0:
                humor_count += 1
            else:
                serious_count += 1
            
            # Question analysis
            question_matches = sum(len(pattern.findall(text)) for pattern in self.question_patterns)
            if question_matches > 0:
                question_count += 1
        
        print(f"DEBUG: Analysis counts - formal: {formal_count}, casual: {casual_count}, emotional: {emotional_count}, humor: {humor_count}")
        
        # Calculate traits with better normalization
        if formal_count + casual_count > 0:
            traits['formality'] = formal_count / (formal_count + casual_count)
        
        if total_words > 0:
            avg_words_per_message = total_words / total_messages
            traits['verbosity'] = min(1.0, max(0.1, avg_words_per_message / 25))  # Normalized to 25 words, min 0.1
        
        if emotional_count + analytical_count > 0:
            traits['emotiveness'] = emotional_count / (emotional_count + analytical_count)
        
        if humor_count + serious_count > 0:
            traits['humor'] = humor_count / (humor_count + serious_count)
        
        traits['curiosity'] = min(1.0, question_count / total_messages)
        
        # Directness based on punctuation and message length
        if total_messages > 0:
            avg_chars = total_chars / total_messages
            traits['directness'] = min(1.0, (punctuation_count / total_messages) + (1 - min(1.0, avg_chars / 100)))
        
        # Politeness (inverse of directness but considering formal language)
        traits['politeness'] = (traits['formality'] + (1 - traits['directness'])) / 2
        
        # Creativity (based on vocabulary diversity and unusual expressions)
        if total_words > 10:  # Need minimum words for analysis
            all_words = []
            for msg in user_messages:
                message_text = msg.get('message', '')
                if message_text:
                    all_words.extend(message_text.lower().split())
            
            if all_words:
                unique_words = len(set(all_words))
                traits['creativity'] = min(1.0, unique_words / len(all_words) * 3)  # Vocabulary diversity
        
        print(f"DEBUG: Final traits: {traits}")
        return traits

    def analyze_conversation_topics(self, messages, summaries):
        """Analyze conversation topics and interests"""
        all_text = ""
        
        # Combine messages and summaries
        for msg in messages:
            if isinstance(msg, dict):
                # Handle both formats
                if msg.get('role') == 'user' or ('role' not in msg and 'message' in msg):
                    all_text += msg.get('message', '') + " "
        
        for summary in summaries:
            if isinstance(summary, dict):
                all_text += summary.get('message', '') + " "
        
        # Use Groq to analyze interests and topics
        return self._analyze_interests_with_groq(all_text)

    def _analyze_interests_with_groq(self, text):
        """Use Groq API to analyze user interests and communication style"""
        if not text.strip():
            return {"interests": [], "communication_style": "neutral"}
        
        if not GROQ_API_KEY:
            print("WARNING: GROQ_API_KEY not found, skipping interest analysis")
            return {"interests": [], "communication_style": "neutral"}
        
        prompt = f"""Analyze the following text and extract:
1. Main interests and topics the person talks about
2. Communication style (formal/casual, emotional/analytical, direct/indirect)
3. Personality indicators (humor, curiosity, creativity, politeness)

Text: {text[:2000]}

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
            response = requests.post(GROQ_API_URL, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"interests": [], "communication_style": "neutral"}
                
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return {"interests": [], "communication_style": "neutral"}
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Response parsing error: {e}")
            return {"interests": [], "communication_style": "neutral"}
        except Exception as e:
            print(f"Unexpected error in interest analysis: {e}")
            return {"interests": [], "communication_style": "neutral"}

    def generate_personality_profile(self, user_email):
        """Generate comprehensive personality profile for user"""
        try:
            # Load user data
            memory = load_memory(user_email)
            summaries = load_summaries(user_email)
            
            # Analyze patterns
            traits = self.analyze_message_patterns(memory)
            interests_data = self.analyze_conversation_topics(memory, summaries)
            
            # Count user messages properly
            user_message_count = len([
                m for m in memory 
                if isinstance(m, dict) and (
                    m.get('role') == 'user' or 
                    ('role' not in m and 'message' in m)
                )
            ])
            
            # Create comprehensive profile
            profile = {
                "personality_traits": traits,
                "interests": interests_data.get("interests", []),
                "communication_style": interests_data.get("communication_style", "neutral"),
                "common_phrases": interests_data.get("common_phrases", []),
                "preferred_topics": interests_data.get("preferred_topics", []),
                "groq_personality_indicators": interests_data.get("personality_indicators", {}),
                "last_updated": datetime.now().isoformat(),
                "message_count": user_message_count,
                "conversation_count": len(summaries)
            }
            
            return profile
            
        except Exception as e:
            print(f"Error generating personality profile: {e}")
            return {
                "personality_traits": self.personality_traits.copy(),
                "interests": [],
                "communication_style": "neutral",
                "last_updated": datetime.now().isoformat(),
                "message_count": 0,
                "conversation_count": 0
            }

    def save_personality_profile(self, profile, user_email):
        """Save personality profile to user's data file"""
        try:
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
                
        except Exception as e:
            print(f"Error saving personality profile: {e}")

    def get_personality_profile(self, user_email):
        """Get personality profile for user"""
        try:
            _, _, _, pref_file = get_user_files(user_email)
            with open(pref_file, 'r') as f:
                data = json.load(f)
            return data.get("personality_profile", {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        except Exception as e:
            print(f"Error loading personality profile: {e}")
            return {}

    def should_update_profile(self, user_email):
        """Check if personality profile should be updated - more aggressive updating"""
        profile = self.get_personality_profile(user_email)
        
        if not profile:
            print(f"DEBUG: No profile found for {user_email}, needs update")
            return True
        
        # Update if last update was more than 3 days ago (reduced from 7)
        last_update = profile.get("last_updated")
        if last_update:
            try:
                last_update_date = datetime.fromisoformat(last_update)
                days_since_update = (datetime.now() - last_update_date).days
                print(f"DEBUG: Days since last update: {days_since_update}")
                if days_since_update > 3:
                    return True
            except ValueError:
                print("DEBUG: Invalid date format, forcing update")
                return True
        
        # Update if significant new conversation activity (reduced threshold)
        try:
            current_memory = load_memory(user_email)
            current_message_count = len([
                m for m in current_memory 
                if isinstance(m, dict) and (
                    m.get('role') == 'user' or 
                    ('role' not in m and 'message' in m)
                )
            ])
            profile_message_count = profile.get("message_count", 0)
            
            print(f"DEBUG: Current messages: {current_message_count}, Profile messages: {profile_message_count}")
            
            if current_message_count > profile_message_count + 5:  # 5 new messages (reduced from 10)
                print("DEBUG: Significant new activity detected")
                return True
        except Exception as e:
            print(f"ERROR: Error checking message count: {e}")
            return True  # Force update on error
        
        # Force update if profile has default values
        traits = profile.get("personality_traits", {})
        if all(abs(v - 0.5) < 0.01 for v in traits.values()):
            print("DEBUG: Profile has default values, forcing update")
            return True
        
        print("DEBUG: No update needed")
        return False

    def generate_personality_prompt(self, user_email):
        """Generate a personality-based system prompt for the AI - more dynamic"""
        profile = self.get_personality_profile(user_email)
        
        if not profile or not profile.get("personality_traits"):
            return "You are Cereal, a helpful AI assistant. Keep responses conversational and engaging."
        
        traits = profile.get("personality_traits", {})
        interests = profile.get("interests", [])
        
        # Build personality-based prompt with more nuanced adaptations
        prompt_parts = ["You are Cereal, adapting to this user's communication style:"]
        
        # Formality
        formality = traits.get("formality", 0.5)
        if formality > 0.65:
            prompt_parts.append("- Use respectful, well-structured language")
        elif formality < 0.35:
            prompt_parts.append("- Keep it casual and relaxed, use contractions freely")
        
        # Verbosity
        verbosity = traits.get("verbosity", 0.5)
        if verbosity > 0.65:
            prompt_parts.append("- Provide thorough explanations and details")
        elif verbosity < 0.35:
            prompt_parts.append("- Keep responses concise and direct")
        
        # Emotiveness
        emotiveness = traits.get("emotiveness", 0.5)
        if emotiveness > 0.6:
            prompt_parts.append("- Match their emotional energy and enthusiasm")
        elif emotiveness < 0.4:
            prompt_parts.append("- Stay factual and analytical in your responses")
        
        # Humor
        humor = traits.get("humor", 0.5)
        if humor > 0.6:
            prompt_parts.append("- Feel free to include humor and playful banter")
        elif humor < 0.3:
            prompt_parts.append("- Keep responses serious and professional")
        
        # Curiosity
        curiosity = traits.get("curiosity", 0.5)
        if curiosity > 0.6:
            prompt_parts.append("- Engage their curiosity with follow-up questions")
        
        # Directness
        directness = traits.get("directness", 0.5)
        if directness > 0.6:
            prompt_parts.append("- Be direct and straight to the point")
        elif directness < 0.4:
            prompt_parts.append("- Use gentle, indirect communication")
        
        # Interests
        if interests:
            prompt_parts.append(f"- They're interested in: {', '.join(interests[:5])}")
        
        # Add personality stats for context
        message_count = profile.get("message_count", 0)
        if message_count > 0:
            prompt_parts.append(f"- Based on {message_count} previous interactions")
        
        return "\n".join(prompt_parts)


# Helper functions to integrate with existing system

def update_user_personality(user_email):
    """Update personality profile for user if needed - with better debugging"""
    print(f"DEBUG: Checking personality update for {user_email}")
    profiler = PersonalityProfiler()
    
    if profiler.should_update_profile(user_email):
        print(f"DEBUG: Updating personality profile for {user_email}")
        try:
            profile = profiler.generate_personality_profile(user_email)
            profiler.save_personality_profile(profile, user_email)
            print(f"DEBUG: Successfully updated personality profile")
            return True
        except Exception as e:
            print(f"ERROR: Failed to update personality profile: {e}")
            return False
    else:
        print(f"DEBUG: No personality update needed for {user_email}")
        return False

def get_personality_system_prompt(user_email):
    """Get personality-based system prompt for user"""
    profiler = PersonalityProfiler()
    return profiler.generate_personality_prompt(user_email)

def get_user_personality_stats(user_email):
    """Get personality statistics for user"""
    profiler = PersonalityProfiler()
    return profiler.get_personality_profile(user_email)