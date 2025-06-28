import json
import os
import requests
from datetime import datetime #

# Base directories for user-specific data
MEMORY_BASE_DIR = 'memory/users'
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_user_files(user_email):
    """Get file paths for a specific user"""
    user_dir = os.path.join(MEMORY_BASE_DIR, user_email.replace('@', '_at_').replace('.', '_dot_'))
    memory_file = os.path.join(user_dir, 'memory.json')
    summary_file = os.path.join(user_dir, 'summary.json')
    pref_file = os.path.join(user_dir, 'data.json')
    return user_dir, memory_file, summary_file, pref_file

def get_real_time_files(user_email): #
    """Get file paths for a specific user's real-time search memory""" #
    user_dir = os.path.join(MEMORY_BASE_DIR, user_email.replace('@', '_at_').replace('.', '_dot_')) #
    real_time_file = os.path.join(user_dir, 'real_time.json') #
    return user_dir, real_time_file #

def load_memory(user_email):
    """Load memory for a specific user"""
    _, memory_file, _, _ = get_user_files(user_email)
    if not os.path.exists(memory_file):
        return []
    try:
        with open(memory_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_memory(memory, user_email):
    """Save memory for a specific user"""
    user_dir, memory_file, _, _ = get_user_files(user_email)
    os.makedirs(user_dir, exist_ok=True)
    with open(memory_file, 'w') as f:
        json.dump(memory, f, indent=2)

def save_summary(summary, user_email):
    """Save conversation summary for a specific user"""
    user_dir, _, summary_file, _ = get_user_files(user_email)
    os.makedirs(user_dir, exist_ok=True)
    try:
        with open(summary_file, 'r') as f:
            summaries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        summaries = []
    
    summaries.append({
        **summary,
        "user_email": user_email,
        "timestamp": _get_timestamp()
    })
    
    with open(summary_file, 'w') as f:
        json.dump(summaries, f, indent=2)

def load_summaries(user_email):
    """Load conversation summaries for a specific user"""
    _, _, summary_file, _ = get_user_files(user_email)
    if not os.path.exists(summary_file):
        return []
    try:
        with open(summary_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def summarize_conversation_naive(messages):
    """Fallback summarization method"""
    summary = " | ".join(msg["message"] for msg in messages if "message" in msg)
    return {"message": f"Summary: {summary[:300]}..."}

def summarize_with_groq(messages, instruction=None): #
    """Summarize conversation using Groq API""" #
    base_prompt = "Summarize the following text concisely. " #
    conversation = "\n".join(f"- {m['message']}" for m in messages if "message" in m) #

    if instruction: #
        summary_prompt = f"{base_prompt}Instructions: {instruction}\n\n{conversation}" #
    else: #
        summary_prompt = base_prompt + conversation #

    headers = { #
        "Authorization": f"Bearer {GROQ_API_KEY}", #
        "Content-Type": "application/json" #
    } #

    data = { #
        "model": "compound-beta-mini", #
        "messages": [{"role": "user", "content": summary_prompt}], #
        "temperature": 0.3, #
        "stream": False #
    } #

    try: #
        response = requests.post(GROQ_API_URL, json=data, headers=headers) #
        response.raise_for_status() #
        content = response.json()["choices"][0]["message"]["content"] #
        
        # Attempt to extract key points if the instruction asked for them
        key_points = [] #
        if instruction and "key points" in instruction.lower(): #
            # A simple heuristic to extract bullet points or numbered lists
            key_points = [line.strip() for line in content.split('\n') if line.strip().startswith(('-', '*', '1.', '2.'))] #

        return {"message": content.strip(), "key_points": key_points} #
    except Exception as e: #
        print(f"Summarization error: {e}") #
        return summarize_conversation_naive(messages) #

def prune_memory(memory, user_email, instruction=None):
    """Prune memory for a specific user"""
    if len(memory) < 10:
        return memory

    # Summarize all but the last 4 messages
    to_summarize = memory[:-4] #
    summary = summarize_with_groq(to_summarize, instruction="Summarize the preceding conversation.") #
    save_summary(summary, user_email)
    
    # Keep the last 4 messages in active memory instead of clearing everything
    memory = memory[-4:] #
    save_memory(memory, user_email)
    return memory

def append_to_memory(user_input, ai_response, user_email):
    """Append conversation to user's memory"""
    memory = load_memory(user_email)
    memory.append({
        "message": user_input,
        "role": "user",
        "timestamp": _get_timestamp()
    })
    memory.append({
        "message": ai_response,
        "role": "assistant", 
        "timestamp": _get_timestamp()
    })
    memory = prune_memory(memory, user_email)
    save_memory(memory, user_email)

def load_real_time_memory(user_email): #
    """Load real-time search summaries for a specific user""" #
    _, real_time_file = get_real_time_files(user_email) #
    if not os.path.exists(real_time_file): #
        return [] #
    try: #
        with open(real_time_file, 'r') as f: #
            return json.load(f) #
    except json.JSONDecodeError: #
        return [] #

def save_real_time_memory(entry, user_email): #
    """Save a real-time search summary entry for a specific user""" #
    user_dir, real_time_file = get_real_time_files(user_email) #
    os.makedirs(user_dir, exist_ok=True) #
    real_time_memory = load_real_time_memory(user_email) #
    real_time_memory.append(entry) #
    # Optionally, you might want to prune this memory based on timestamp or number of entries
    with open(real_time_file, 'w') as f: #
        json.dump(real_time_memory, f, indent=2) #

def set_user_preference(key, value, user_email):
    """Set preference for a specific user"""
    user_dir, _, _, pref_file = get_user_files(user_email)
    os.makedirs(user_dir, exist_ok=True)
    
    try:
        with open(pref_file, 'r') as f:
            prefs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        prefs = {"email": user_email, "created_at": _get_timestamp()}
    
    prefs[key] = value
    prefs["last_updated"] = _get_timestamp()
    
    with open(pref_file, 'w') as f:
        json.dump(prefs, f, indent=2)

def get_user_preference(key, user_email):
    """Get preference for a specific user"""
    _, _, _, pref_file = get_user_files(user_email)
    try:
        with open(pref_file, 'r') as f:
            prefs = json.load(f)
        return prefs.get(key)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def get_all_user_preferences(user_email):
    """Get all preferences for a specific user"""
    _, _, _, pref_file = get_user_files(user_email)
    try:
        with open(pref_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"email": user_email, "created_at": _get_timestamp()}

def clear_user_memory(user_email):
    """Clear all memory for a specific user"""
    save_memory([], user_email)
    return True

def _get_timestamp():
    """Get current timestamp"""
    return datetime.now().isoformat()