# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, abort
import os
import sys
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Import modules with proper error handling
try:
    from groq_api import get_groq_response_stream_enhanced, get_groq_response_stream
except ImportError as e:
    print(f"ERROR: Could not import groq_api: {e}")
    sys.exit(1)

try:
    import database
except ImportError as e:
    print(f"ERROR: Could not import database: {e}")
    sys.exit(1)

# Import personality profiler functions
groq_api_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'groq_api')
if groq_api_path not in sys.path:
    sys.path.insert(0, groq_api_path)

# Import personality profiler functions
try:
    from personality.personality_profiler import (
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
            traces_sample_rate=1.0,  # Adjust sampling rate as needed (0.0 to 1.0)
            send_default_pii=True    # To send user info like emails (optional)
        )
    else:
        print("WARNING: SENTRY_DSN not set. Sentry monitoring is disabled.")

    # Rest of your app config & routes here...
    app.secret_key = os.environ.get("FLASK_SECRET_KEY")
    
    if not app.secret_key:
        print("CRITICAL WARNING: FLASK_SECRET_KEY environment variable not set. Session security compromised. Exiting.")
        sys.exit(1)

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
                user = database.get_user_by_email(email)
                
                if user and database.verify_password(user['password'], password):
                    session['user'] = user['email']
                    return redirect(url_for('chat'))
                else:
                    return render_template('user/login.html', error="Invalid email or password")
            except Exception as e:
                print(f"ERROR in login: {e}")
                return render_template('user/login.html', error="Login failed. Please try again.")
                
        return render_template('user/login.html')

    @app.route('/pricing')
    def pricing():
        user_logged_in = 'user' in session
        return render_template('main/pricing.html', user_logged_in=user_logged_in)

    @app.route('/chat', methods=['GET'])
    def chat():
        if 'user' not in session:
            return redirect(url_for('login'))
        user_logged_in = 'user' in session
        user_email = session.get('user', 'Guest') # Get user email from session
        return render_template('main/chat.html', user_logged_in=user_logged_in, user_email=user_email) # Pass user_email
        

    @app.route('/chat', methods=['POST'])
    def chat_post():
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        user_message = request.json.get('message')
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Get user email from session
        user_email = session['user']
        
        try:
            # Call streaming but collect full response before sending JSON
            full_response = ""
            for chunk in get_groq_response_stream(user_message, user_email):
                full_response += chunk

            return jsonify({'response': full_response})
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

        # Get user email from session
        user_email = session['user']

        def generate():
            try:
                for token in get_groq_response_stream(user_message, user_email):
                    yield token
            except Exception as e:
                print(f"ERROR in stream_chat: {e}")
                yield f"Error: {str(e)}"

        return Response(generate(), mimetype='text/plain')

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
                "recent_messages": memory[-5:] if memory else []  # Last 5 messages
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

    # NEW PERSONALITY PROFILER ENDPOINTS
    
    @app.route('/personality-profile')
    def personality_profile():
        """Endpoint to view user's personality profile"""
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        if not PERSONALITY_AVAILABLE:
            return jsonify({"error": "Personality profiling not available"}), 503
        
        user_email = session['user']
        
        try:
            # Get personality stats
            personality_stats = get_user_personality_stats(user_email)
            
            if not personality_stats:
                return jsonify({
                    "message": "No personality profile available yet. Keep chatting to build your profile!",
                    "profile_exists": False
                })
            
            # Format the personality data for better presentation
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
                "interests": personality_stats.get("interests", [])[:10],  # Top 10 interests
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
            # Force update personality profile
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
            
            # Generate insights based on personality traits
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
            
            # Add interest-based insights
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
                "profile_strength": min(100, personality_stats.get("message_count", 0) * 2)  # Profile strength based on message count
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

    @app.route('/api/user-info')
    def get_user_info():
        """API endpoint to get current user information"""
        if 'user' not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        user_email = session['user']
        
        try:
            user = database.get_user_by_email(user_email)
            if user:
                return jsonify({
                    "email": user['email'],
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

    # Keep the existing GET logout route for direct navigation
    @app.route('/logout')
    def logout():
        session.pop('user', None)
        return redirect(url_for('login'))

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
                if database.add_user(email, password):
                    session['user'] = email
                    # Initialize user preferences when they sign up
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
            except Exception as e:
                print(f"ERROR in signup: {e}")
                return render_template('user/signup.html', error="Signup failed. Please try again.")
                
        return render_template('user/signup.html')

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
        # Flask's request.environ['SERVER_PROTOCOL'] should be HTTP/1.0 or HTTP/1.1 normally
        protocol = request.environ.get('SERVER_PROTOCOL', '')
        if not protocol.startswith('HTTP/'):
            # Likely a malformed request or binary junk; block it
            abort(400, description="Malformed request")

    return app
    
                  

# Create the app instance
app = create_app()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG') == '1' 
    app.run(debug=debug_mode, host='0.0.0.0')