# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, abort
import os
import sys
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from datetime import datetime

# Import modules with proper error handling
try:
    from AI.groq_api import get_groq_response_stream
    GROQ_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Could not import groq_api: {e}")
    GROQ_AVAILABLE = False

try:
    import database
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Could not import database: {e}")
    DATABASE_AVAILABLE = False

# Import personality profiler functions
try:
    from AI.modules.personality.personality_profiler import (
        update_user_personality,
        get_personality_system_prompt,
        get_user_personality_stats
    )
    PERSONALITY_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Could not import personality_profiler: {e}")
    PERSONALITY_AVAILABLE = False

from werkzeug.security import generate_password_hash, check_password_hash

def create_app():
    app = Flask(__name__)
    
    # Initialize Sentry first
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=1.0,
            send_default_pii=True
        )
    else:
        print("WARNING: SENTRY_DSN not set. Sentry monitoring is disabled.")

    # App configuration
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    
    if app.secret_key == "dev-secret-key-change-in-production":
        print("WARNING: Using default secret key. Set FLASK_SECRET_KEY environment variable for production.")

    # Mock data for development when database is not available
    mock_sessions = []
    mock_users = {}

    def get_memory_module():
        """Safely import memory module"""
        try:
            memory_path = os.path.join(os.path.dirname(__file__), "memory")
            if memory_path not in sys.path:
                sys.path.append(memory_path)
            import memory
            return memory
        except ImportError as e:
            print(f"WARNING: Could not import memory module: {e}")
            return None

    @app.route('/')
    def home():
        user_logged_in = 'user' in session
        return render_template('main/doc.html', user_logged_in=user_logged_in)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            
            try:
                if DATABASE_AVAILABLE:
                    user = database.get_user_by_email(email)
                    if user and database.verify_password(user['password'], password):
                        session['user'] = user['email']
                        return redirect(url_for('chat'))
                    else:
                        return render_template('user/login.html', error="Invalid email or password")
                else:
                    # Mock authentication for development
                    if email in mock_users and check_password_hash(mock_users[email]['password'], password):
                        session['user'] = email
                        return redirect(url_for('chat'))
                    else:
                        return render_template('user/login.html', error="Invalid email or password (using mock auth)")
            except Exception as e:
                print(f"ERROR in login: {e}")
                return render_template('user/login.html', error="Login failed. Please try again.")
                
        return render_template('user/login.html')

    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form.get('confirm-password')

            if not email or not password or not confirm_password:
                return render_template('user/signup.html', error="All fields are required")
            
            if password != confirm_password:
                return render_template('user/signup.html', error="Passwords do not match")
            
            if len(password) < 6:
                return render_template('user/signup.html', error="Password must be at least 6 characters long")

            try:
                if DATABASE_AVAILABLE:
                    if database.add_user(email, password):
                        session['user'] = email
                        memory_module = get_memory_module()
                        if memory_module:
                            try:
                                memory_module.set_user_preference("chat_style", "casual", email)
                                memory_module.set_user_preference("preferred_name", "there", email)
                            except Exception as e:
                                print(f"WARNING: Could not set initial preferences: {e}")
                        return redirect(url_for('chat'))
                    else:
                        return render_template('user/signup.html', error="Email already registered")
                else:
                    # Mock user creation for development
                    if email in mock_users:
                        return render_template('user/signup.html', error="Email already registered (mock)")
                    
                    mock_users[email] = {
                        'email': email,
                        'password': generate_password_hash(password),
                        'created_at': datetime.now()
                    }
                    session['user'] = email
                    return redirect(url_for('chat'))
                    
            except Exception as e:
                print(f"ERROR in signup: {e}")
                return render_template('user/signup.html', error="Signup failed. Please try again.")
                
        return render_template('user/signup.html')

    @app.route('/pricing')
    def pricing():
        user_logged_in = 'user' in session
        return render_template('main/pricing.html', user_logged_in=user_logged_in)

    @app.route('/chat', methods=['GET'])
    def chat():
        if 'user' not in session:
            return redirect(url_for('login'))
        user_logged_in = 'user' in session
        user_email = session.get('user', 'Guest')
        return render_template('main/chat.html', user_logged_in=user_logged_in, user_email=user_email)

    @app.route('/chat', methods=['POST'])
    def chat_post():
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        user_message = request.json.get('message')
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        user_email = session['user']
        
        try:
            if GROQ_AVAILABLE:
                full_response = ""
                for chunk in get_groq_response_stream(user_message, user_email):
                    full_response += chunk
                return jsonify({'response': full_response})
            else:
                # Mock response when Groq is not available
                return jsonify({'response': f"Mock response to: {user_message} (Groq API not available)"})
        except Exception as e:
            print(f"ERROR in chat_post: {e}")
            return jsonify({'error': 'Failed to generate response'}), 500

    @app.route('/chat-stream', methods=['POST'])
    def stream_chat():
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401

        user_message = request.json.get("message", "")
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        user_email = session['user']

        def generate():
            try:
                if GROQ_AVAILABLE:
                    for token in get_groq_response_stream(user_message, user_email):
                        yield token
                else:
                    # Mock streaming response
                    mock_response = f"Mock streaming response to: {user_message}"
                    for char in mock_response:
                        yield char
            except Exception as e:
                print(f"ERROR in stream_chat: {e}")
                yield f"Error: {str(e)}"

        return Response(generate(), mimetype='text/plain')

    # Chat Sessions API Endpoints
    @app.route('/api/chat-sessions', methods=['GET'])
    def get_chat_sessions():
        """Get all chat sessions for the current user"""
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
    
        user_email = session['user']
    
        try:
            if DATABASE_AVAILABLE:
                sessions = database.get_user_chat_sessions(user_email)
            # Convert UUID to string for JSON serialization
                for session_data in sessions:
                    if 'session_id' in session_data:
                        session_data['session_id'] = str(session_data['session_id'])
            else:
            # Return mock sessions for development
                user_sessions = [s for s in mock_sessions if s.get('user_email') == user_email]
                sessions = user_sessions
        
        # Return sessions directly, not wrapped in another object
            return jsonify(sessions)  # Changed this line
        except Exception as e:
            print(f"Error retrieving chat sessions: {e}")
            return jsonify({"error": "Failed to retrieve chat sessions"}), 500

    @app.route('/api/chat-sessions', methods=['POST'])
    def create_chat_session():
        """Create a new chat session"""
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        user_email = session['user']
        data = request.get_json()
        title = data.get('title', 'New Chat')
        
        try:
            if DATABASE_AVAILABLE:
                session_data = database.create_chat_session(user_email, title)
                if session_data:
                    return jsonify({
                        "session_id": str(session_data['session_id']),
                        "title": session_data['title'],
                        "created_at": session_data['created_at'],
                        "updated_at": session_data.get('updated_at', session_data['created_at'])
                    })
                else:
                    return jsonify({"error": "Failed to create session"}), 500
            else:
                # Mock session creation
                session_id = len(mock_sessions) + 1
                new_session = {
                    'id': session_id,
                    'title': title,
                    'user_email': user_email,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'message_count': 0
                }
                mock_sessions.append(new_session)
                
                return jsonify({
                    "session_id": session_id,
                    "title": title,
                    "created_at": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Error creating chat session: {e}")
            return jsonify({"error": "Failed to create chat session"}), 500



    @app.route('/api/chat-sessions/<session_id>', methods=['DELETE'])
    def delete_chat_session(session_id):
        """Delete a chat session"""
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        user_email = session['user']
        
        try:
            if DATABASE_AVAILABLE:
                success = database.delete_chat_session(session_id, user_email)
            else:
                # Mock session deletion
                global mock_sessions
                original_length = len(mock_sessions)
                mock_sessions = [s for s in mock_sessions if not (str(s.get('id')) == str(session_id) and s['user_email'] == user_email)]
                success = len(mock_sessions) < original_length
            
            if success:
                return jsonify({"message": "Session deleted successfully"})
            else:
                return jsonify({"error": "Session not found or unauthorized"}), 404
        except Exception as e:
            print(f"Error deleting chat session: {e}")
            return jsonify({"error": "Failed to delete chat session"}), 500

    @app.route('/api/chat-sessions/<session_id>/messages', methods=['GET'])
    def get_session_messages(session_id):
        """Get all messages for a specific chat session"""
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        user_email = session['user']
        
        try:
            if DATABASE_AVAILABLE:
                # First verify the session belongs to the user
                sessions = database.get_user_chat_sessions(user_email)
                session_exists = any(str(s['session_id']) == str(session_id) for s in sessions)
                
                if not session_exists:
                    return jsonify({"error": "Session not found or unauthorized"}), 404
                
                messages = database.get_chat_messages(session_id)
                # Convert UUID to string for JSON serialization
                for message in messages:
                    if 'message_id' in message:
                        message['message_id'] = str(message['message_id'])
                    if 'session_id' in message:
                        message['session_id'] = str(message['session_id'])
                
                return jsonify({"messages": messages})
            else:
                # Mock messages for development
                return jsonify({"messages": []})
        except Exception as e:
            print(f"Error retrieving session messages: {e}")
            return jsonify({"error": "Failed to retrieve messages"}), 500

    @app.route('/api/chat-sessions/<session_id>/messages', methods=['POST'])
    def save_session_message(session_id):
        """Save a message to a specific chat session"""
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        user_email = session['user']
        data = request.get_json()
        message_type = data.get('message_type')  # 'user' or 'assistant'
        content = data.get('content')
        
        if not message_type or not content:
            return jsonify({"error": "message_type and content are required"}), 400
        
        if message_type not in ['user', 'assistant']:
            return jsonify({"error": "message_type must be 'user' or 'assistant'"}), 400
        
        try:
            if DATABASE_AVAILABLE:
                # First verify the session belongs to the user
                sessions = database.get_user_chat_sessions(user_email)
                session_exists = any(str(s['session_id']) == str(session_id) for s in sessions)
                
                if not session_exists:
                    return jsonify({"error": "Session not found or unauthorized"}), 404
                
                message_data = database.save_chat_message(session_id, user_email, message_type, content)
                if message_data:
                    # Convert UUID to string for JSON serialization
                    message_data['message_id'] = str(message_data['message_id'])
                    message_data['session_id'] = str(message_data['session_id'])
                    return jsonify({"message": "Message saved successfully", "data": message_data})
                else:
                    return jsonify({"error": "Failed to save message"}), 500
            else:
                # Mock message saving for development
                return jsonify({"message": "Message saved successfully (mock)"})
        except Exception as e:
            print(f"Error saving session message: {e}")
            return jsonify({"error": "Failed to save message"}), 500

    @app.route('/api/user-info')
    def get_user_info():
        """API endpoint to get current user information"""
        if 'user' not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        user_email = session['user']
        
        try:
            if DATABASE_AVAILABLE:
                user = database.get_user_by_email(user_email)
                if user:
                    return jsonify({
                        "email": user['email'],
                        "authenticated": True,
                        "personality_available": PERSONALITY_AVAILABLE
                    })
                else:
                    return jsonify({"error": "User not found"}), 404
            else:
                # Mock user info
                if user_email in mock_users:
                    return jsonify({
                        "email": user_email,
                        "authenticated": True,
                        "personality_available": PERSONALITY_AVAILABLE
                    })
                else:
                    return jsonify({"error": "User not found"}), 404
        except Exception as e:
            print(f"ERROR in get_user_info: {e}")
            return jsonify({"error": "Failed to get user info"}), 500

    @app.route('/logout', methods=['POST'])
    def logout_post():
        """Handle POST logout requests"""
        session.pop('user', None)
        return jsonify({"message": "Logged out successfully"})

    @app.route('/logout')
    def logout():
        session.pop('user', None)
        return redirect(url_for('login'))

    # Memory and Personality endpoints (existing code)
    @app.route('/memory-stats')
    def memory_stats():
        """Endpoint to view user's memory statistics"""
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        user_email = session['user']
        memory_module = get_memory_module()
        
        if not memory_module:
            return jsonify({"error": "Memory module not available"}), 500
        
        try:
            memory = memory_module.load_memory(user_email)
            summaries = memory_module.load_summaries(user_email)
            preferences = memory_module.get_all_user_preferences(user_email)
            
            stats = {
                "email": user_email,
                "active_memories": len(memory),
                "conversation_summaries": len(summaries),
                "preferences": preferences,
                "recent_messages": memory[-5:] if memory else []
            }
            
            return jsonify(stats)
        except Exception as e:
            print(f"ERROR in memory_stats: {e}")
            return jsonify({"error": "Failed to retrieve memory stats"}), 500

    @app.route('/clear-memory', methods=['POST'])
    def clear_memory():
        """Endpoint to clear user's memory"""
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        user_email = session['user']
        memory_module = get_memory_module()
        
        if not memory_module:
            return jsonify({"error": "Memory module not available"}), 500
        
        try:
            success = memory_module.clear_user_memory(user_email)
            
            if success:
                return jsonify({"message": "Memory cleared successfully"})
            else:
                return jsonify({"error": "Failed to clear memory"}), 500
        except Exception as e:
            print(f"ERROR in clear_memory: {e}")
            return jsonify({"error": "Failed to clear memory"}), 500

    @app.route('/personality-profile')
    def personality_profile():
        """Endpoint to view user's personality profile"""
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        if not PERSONALITY_AVAILABLE:
            return jsonify({"error": "Personality profiling not available"}), 503
        
        user_email = session['user']
        
        try:
            personality_stats = get_user_personality_stats(user_email)
            
            if not personality_stats:
                return jsonify({
                    "message": "No personality profile available yet. Keep chatting to build your profile!",
                    "profile_exists": False
                })
            
            traits = personality_stats.get("personality_traits", {})
            formatted_traits = {}
            
            trait_descriptions = {
                'formality': ('Very Casual 🤙', 'Casual', 'Balanced', 'Formal', 'Very Formal 🎩'),
                'verbosity': ('Brief & Concise', 'Somewhat Brief', 'Balanced', 'Detailed', 'Very Detailed 📝'),
                'emotiveness': ('Analytical 🔬', 'Somewhat Analytical', 'Balanced', 'Emotional', 'Very Emotional ❤️'),
                'humor': ('Serious 😐', 'Somewhat Serious', 'Balanced', 'Humorous', 'Very Humorous 😄'),
                'curiosity': ('Passive', 'Somewhat Passive', 'Balanced', 'Curious', 'Very Curious 🤔'),
                'directness': ('Indirect', 'Somewhat Indirect', 'Balanced', 'Direct', 'Very Direct 🎯'),
                'politeness': ('Blunt', 'Somewhat Blunt', 'Balanced', 'Polite', 'Very Polite 🙏'),
                'creativity': ('Practical', 'Somewhat Practical', 'Balanced', 'Creative', 'Very Creative 🎨')
            }
            
            for trait, value in traits.items():
                if trait in trait_descriptions:
                    index = min(4, int(value * 5))
                    description = trait_descriptions[trait][index]
                    formatted_traits[trait] = {
                        "value": round(value, 2),
                        "description": description,
                        "percentage": round(value * 100)
                    }
            
            profile_data = {
                "profile_exists": True,
                "email": user_email,
                "personality_traits": formatted_traits,
                "interests": personality_stats.get("interests", [])[:10],
                "communication_style": personality_stats.get("communication_style", "neutral"),
                "preferred_topics": personality_stats.get("preferred_topics", [])[:5],
                "common_phrases": personality_stats.get("common_phrases", [])[:5],
                "statistics": {
                    "message_count": personality_stats.get("message_count", 0),
                    "conversation_count": personality_stats.get("conversation_count", 0),
                    "last_updated": personality_stats.get("last_updated", "Never")
                }
            }
            
            return jsonify(profile_data)
            
        except Exception as e:
            print(f"ERROR in personality_profile: {e}")
            return jsonify({"error": "Failed to retrieve personality profile"}), 500

    @app.route('/update-personality', methods=['POST'])
    def update_personality():
        """Endpoint to manually trigger personality profile update"""
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        if not PERSONALITY_AVAILABLE:
            return jsonify({"error": "Personality profiling not available"}), 503
        
        user_email = session['user']
        
        try:
            updated = update_user_personality(user_email)
            
            if updated:
                return jsonify({
                    "message": "Personality profile updated successfully!",
                    "updated": True
                })
            else:
                return jsonify({
                    "message": "Personality profile is already up to date.",
                    "updated": False
                })
                
        except Exception as e:
            print(f"ERROR in update_personality: {e}")
            return jsonify({"error": "Failed to update personality profile"}), 500

    @app.route('/personality-insights')
    def personality_insights():
        """Endpoint to get personality insights and recommendations"""
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        if not PERSONALITY_AVAILABLE:
            return jsonify({"error": "Personality profiling not available"}), 503
        
        user_email = session['user']
        
        try:
            personality_stats = get_user_personality_stats(user_email)
            
            if not personality_stats:
                return jsonify({
                    "message": "No personality data available for insights yet.",
                    "insights": []
                })
            
            traits = personality_stats.get("personality_traits", {})
            insights = []
            
            if traits.get("formality", 0.5) > 0.7:
                insights.append({
                    "type": "communication",
                    "title": "Formal Communication Style",
                    "description": "You prefer formal, structured communication. Cereal will use polite language and proper grammar when chatting with you.",
                    "icon": "🎩"
                })
            elif traits.get("formality", 0.5) < 0.3:
                insights.append({
                    "type": "communication",
                    "title": "Casual Communication Style",
                    "description": "You enjoy casual, relaxed conversations. Cereal will use informal language and contractions to match your style.",
                    "icon": "🤙"
                })
            
            if traits.get("verbosity", 0.5) > 0.7:
                insights.append({
                    "type": "response_length",
                    "title": "Detailed Responses Preferred",
                    "description": "You appreciate comprehensive, detailed answers. Cereal will provide thorough explanations for your questions.",
                    "icon": "📝"
                })
            elif traits.get("verbosity", 0.5) < 0.3:
                insights.append({
                    "type": "response_length",
                    "title": "Concise Responses Preferred",
                    "description": "You prefer brief, to-the-point answers. Cereal will keep responses concise and focused.",
                    "icon": "⚡"
                })
            
            if traits.get("humor", 0.5) > 0.6:
                insights.append({
                    "type": "personality",
                    "title": "Humor Appreciated",
                    "description": "You enjoy humor in conversations. Cereal will include appropriate jokes and light-hearted comments.",
                    "icon": "😄"
                })
            
            if traits.get("curiosity", 0.5) > 0.6:
                insights.append({
                    "type": "learning",
                    "title": "High Curiosity Level",
                    "description": "You ask lots of questions and love learning new things. Cereal will provide extra context and related information.",
                    "icon": "🤔"
                })
            
            if traits.get("emotiveness", 0.5) > 0.6:
                insights.append({
                    "type": "emotional",
                    "title": "Emotional Expression",
                    "description": "You express emotions in your messages. Cereal will respond with empathy and emotional understanding.",
                    "icon": "❤️"
                })
            
            interests = personality_stats.get("interests", [])
            if interests:
                insights.append({
                    "type": "interests",
                    "title": "Key Interests Identified",
                    "description": f"Cereal has identified your main interests: {', '.join(interests[:3])}. Conversations will be tailored to these topics.",
                    "icon": "🎯"
                })
            
            return jsonify({
                "insights": insights,
                "total_insights": len(insights),
                "profile_strength": min(100, personality_stats.get("message_count", 0) * 2)
            })
            
        except Exception as e:
            print(f"ERROR in personality_insights: {e}")
            return jsonify({"error": "Failed to generate personality insights"}), 500

    @app.route('/personality-dashboard')
    def personality_dashboard():
        """Render personality dashboard page"""
        if 'user' not in session:
            return redirect(url_for('login'))
        
        user_logged_in = True
        user_email = session['user']
        personality_available = PERSONALITY_AVAILABLE
        
        return render_template('main/personality.html', 
                             user_logged_in=user_logged_in, 
                             user_email=user_email,
                             personality_available=personality_available)

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        return response

    @app.before_request
    def block_malformed_requests():
        protocol = request.environ.get('SERVER_PROTOCOL', '')
        if not protocol.startswith('HTTP/'):
            abort(400, description="Malformed request")

    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG') == '1' 
    app.run(debug=debug_mode, host='0.0.0.0')