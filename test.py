import os
profiler_path = os.path.join(os.path.dirname(__file__), 'groq_api', 'personality', 'personality_profiler.py')
print(f"Looking for personality_profiler.py at: {profiler_path}")
print(f"File exists: {os.path.exists(profiler_path)}")