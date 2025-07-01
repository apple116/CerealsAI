from fastapi import FastAPI, Request, HTTPException, Depends, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import Response
import os
import sys
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from pydantic import BaseModel
from typing import Optional, Dict, Any, Generator
import uvicorn

# Import modules with proper error handling
try:
    from AI.groq_api import get_groq_response_stream
except ImportError as e:
    print(f"ERROR: Could not import groq_api: {e}")
    sys.exit(1)

try:
    import database
except ImportError as e:
    print(f"ERROR: Could not import database: {e}")
    sys.exit(1)

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

class ChatSessionCreate(BaseModel):
    title: str = "New Chat"

class ChatSessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: Optional[str] = None

class MessageCreate(BaseModel):
    message_type: str  # 'user' or 'assistant'
    content: str

class MessageResponse(BaseModel):
    message_id: str
    session_id: str
    message_type: str
    content: str
    created_at: str
# Pydantic models for request/response validation
class ChatMessage(BaseModel):
    message: str

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str
    confirm_password: str

class UserResponse(BaseModel):
    email: str
    authenticated: bool
    personality_available: bool

class PersonalityInsight(BaseModel):
    type: str
    title: str
    description: str
    icon: str

def create_app() -> FastAPI:
    app = FastAPI(
        title="Cereal AI Chat",
        description="AI-powered chat application with personality profiling",
        version="2.0.0"
    )

    # Initialize Sentry first
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FastApiIntegration()],
            traces_sample_rate=1.0,
            send_default_pii=True
        )
    else:
        print("WARNING: SENTRY_DSN not set. Sentry monitoring is disabled.")

    # Session middleware
    secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not secret_key:
        print("CRITICAL WARNING: FLASK_SECRET_KEY environment variable not set. Session security compromised. Exiting.")
        sys.exit(1)

    app.add_middleware(SessionMiddleware, secret_key=secret_key)

    # Static files and templates
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")

    # Helper function for template context
    def get_template_context(request: Request, **kwargs):
        """Helper to create template context with url_for function"""
        def url_for(name, **params):
        # Handle static files
            if name == "static":
                filename = params.get('filename', '')
                return f"/static/{filename}"
        
        # Handle regular routes
            routes = {
                'home': '/',
                'login': '/login',
                'logout': '/logout',
                'signup': '/signup',
                'chat': '/chat',
                'pricing': '/pricing',
                'personality_dashboard': '/personality-dashboard'  # Add this line
            }
            return routes.get(name, f"/{name}")

        context = {
            "request": request,
            "url_for": url_for,
            "session": dict(request.session) if hasattr(request, 'session') else {},  # Better session handling
            **kwargs
        }
        return context

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        return response

    # Dependency to check if user is logged in
    def get_current_user(request: Request) -> Optional[str]:
        return request.session.get('user')

    def require_auth(request: Request) -> str:
        user = get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return user

    # Helper function to get memory module
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

    # Routes
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        user_logged_in = 'user' in request.session
        return templates.TemplateResponse("main/doc.html", 
            get_template_context(request, user_logged_in=user_logged_in)
        )

    @app.get("/login", response_class=HTMLResponse)
    async def login_get(request: Request):
        return templates.TemplateResponse("user/login.html", get_template_context(request))

    @app.post("/login")
    async def login_post(
        request: Request,
        email: str = Form(...),
        password: str = Form(...)
    ):
        try:
            user = database.get_user_by_email(email)
            
            if user and database.verify_password(user['password'], password):
                request.session['user'] = user['email']
                return RedirectResponse(url="/chat", status_code=303)
            else:
                return templates.TemplateResponse("user/login.html", 
                    get_template_context(request, error="Invalid email or password")
                )
        except Exception as e:
            print(f"ERROR in login: {e}")
            return templates.TemplateResponse("user/login.html", 
                get_template_context(request, error="Login failed. Please try again.")
            )

    @app.get("/pricing", response_class=HTMLResponse)
    async def pricing(request: Request):
        user_logged_in = 'user' in request.session
        return templates.TemplateResponse("main/pricing.html", 
            get_template_context(request, user_logged_in=user_logged_in)
        )

    @app.get("/chat", response_class=HTMLResponse)
    async def chat_get(request: Request):
        user_email = require_auth(request)
        return templates.TemplateResponse("main/chat.html", 
            get_template_context(request, user_logged_in=True, user_email=user_email)
        )

    @app.post("/chat")
    async def chat_post(request: Request, chat_message: ChatMessage):
        user_email = require_auth(request)
        
        if not chat_message.message:
            raise HTTPException(status_code=400, detail="No message provided")
        
        try:
            # Call streaming but collect full response before sending JSON
            full_response = ""
            for chunk in get_groq_response_stream(chat_message.message, user_email):
                full_response += chunk

            return {"response": full_response}
        except Exception as e:
            print(f"ERROR in chat_post: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate response")

    @app.post("/chat-stream")
    async def stream_chat(request: Request, chat_message: ChatMessage):
        user_email = require_auth(request)
        
        if not chat_message.message:
            raise HTTPException(status_code=400, detail="No message provided")

        def generate() -> Generator[str, None, None]:
            try:
                for token in get_groq_response_stream(chat_message.message, user_email):
                    yield token
            except Exception as e:
                print(f"ERROR in stream_chat: {e}")
                yield f"Error: {str(e)}"

        return StreamingResponse(generate(), media_type='text/plain')

    @app.get("/memory-stats")
    async def memory_stats(request: Request):
        """Endpoint to view user's memory statistics"""
        user_email = require_auth(request)
        memory_module = get_memory_module()
        
        if not memory_module:
            raise HTTPException(status_code=500, detail="Memory module not available")
        
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
            
            return stats
        except Exception as e:
            print(f"ERROR in memory_stats: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve memory stats")

    @app.post("/clear-memory")
    async def clear_memory(request: Request):
        """Endpoint to clear user's memory"""
        user_email = require_auth(request)
        memory_module = get_memory_module()
        
        if not memory_module:
            raise HTTPException(status_code=500, detail="Memory module not available")
        
        try:
            success = memory_module.clear_user_memory(user_email)
            
            if success:
                return {"message": "Memory cleared successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to clear memory")
        except Exception as e:
            print(f"ERROR in clear_memory: {e}")
            raise HTTPException(status_code=500, detail="Failed to clear memory")

    # PERSONALITY PROFILER ENDPOINTS
    
    @app.get("/personality-profile")
    async def personality_profile(request: Request):
        """Endpoint to view user's personality profile"""
        user_email = require_auth(request)
        
        if not PERSONALITY_AVAILABLE:
            raise HTTPException(status_code=503, detail="Personality profiling not available")
        
        try:
            personality_stats = get_user_personality_stats(user_email)
            
            if not personality_stats:
                return {
                    "message": "No personality profile available yet. Keep chatting to build your profile!",
                    "profile_exists": False
                }
            
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
            
            return profile_data
            
        except Exception as e:
            print(f"ERROR in personality_profile: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve personality profile")

    @app.post("/update-personality")
    async def update_personality_endpoint(request: Request):
        """Endpoint to manually trigger personality profile update"""
        user_email = require_auth(request)
        
        if not PERSONALITY_AVAILABLE:
            raise HTTPException(status_code=503, detail="Personality profiling not available")
        
        try:
            updated = update_user_personality(user_email)
            
            if updated:
                return {
                    "message": "Personality profile updated successfully!",
                    "updated": True
                }
            else:
                return {
                    "message": "Personality profile is already up to date.",
                    "updated": False
                }
                
        except Exception as e:
            print(f"ERROR in update_personality: {e}")
            raise HTTPException(status_code=500, detail="Failed to update personality profile")

    @app.get("/personality-insights")
    async def personality_insights(request: Request):
        """Endpoint to get personality insights and recommendations"""
        user_email = require_auth(request)
        
        if not PERSONALITY_AVAILABLE:
            raise HTTPException(status_code=503, detail="Personality profiling not available")
        
        try:
            personality_stats = get_user_personality_stats(user_email)
            
            if not personality_stats:
                return {
                    "message": "No personality data available for insights yet.",
                    "insights": []
                }
            
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
            
            return {
                "insights": insights,
                "total_insights": len(insights),
                "profile_strength": min(100, personality_stats.get("message_count", 0) * 2)
            }
            
        except Exception as e:
            print(f"ERROR in personality_insights: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate personality insights")

    @app.get("/personality-dashboard", response_class=HTMLResponse)
    async def personality_dashboard(request: Request):
        """Render personality dashboard page"""
        user_email = require_auth(request)
        
        return templates.TemplateResponse('main/personality.html', 
            get_template_context(request, 
                user_logged_in=True,
                user_email=user_email,
                personality_available=PERSONALITY_AVAILABLE
            )
        )
    
    @app.get("/api/chat-sessions")
    async def get_chat_sessions(request: Request):
        """Get all chat sessions for the current user"""
        user_email = require_auth(request)

        try:
            sessions = database.get_user_chat_sessions(user_email)
            for session_data in sessions:
                if 'session_id' in session_data:
                    session_data['session_id'] = str(session_data['session_id'])
            return sessions
        except Exception as e:
            print(f"Error retrieving chat sessions: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve chat sessions")
    @app.post("/api/chat-sessions")
    async def create_chat_session(request: Request):
        """Create a new chat session"""
        user_email = require_auth(request)
        data = await request.json()
        title = data.get('title', 'New Chat')
        try:
            session_data = database.create_chat_session(user_email, title)
            if session_data:
                return {
                    "session_id": str(session_data['session_id']),
                    "title": session_data['title'],
                    "created_at": session_data['created_at'],
                    "updated_at": session_data.get('updated_at', session_data['created_at'])
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to create session")
        except Exception as e:
            print(f"Error creating chat session: {e}")
            raise HTTPException(status_code=500, detail="Failed to create chat session")
    
    @app.delete("/api/chat-sessions/{session_id}")
    async def delete_chat_session(request: Request, session_id: str):
        """Delete a chat session"""
        user_email = require_auth(request)
        try:
            success = database.delete_chat_session(session_id, user_email)
            if success:
                return {"message": "Session deleted successfully"}
            else:
                raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        except Exception as e:
            print(f"Error deleting chat session: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete chat session")
    
    @app.get("/api/chat-sessions/{session_id}/messages")
    async def get_session_messages(request: Request, session_id: str):
        """Get all messages for a specific chat session"""
        user_email = require_auth(request)
    
        try:
        # First verify the session belongs to the user
            sessions = database.get_user_chat_sessions(user_email)
            session_exists = any(str(s['session_id']) == str(session_id) for s in sessions)
        
            if not session_exists:
                raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
            messages = database.get_chat_messages(session_id)
        # Convert UUID to string for JSON serialization
            for message in messages:
                if 'message_id' in message:
                     message['message_id'] = str(message['message_id'])
                if 'session_id' in message:
                     message['session_id'] = str(message['session_id'])
        
            return {"messages": messages}
        except Exception as e:
            print(f"Error retrieving session messages: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve messages")
    
    @app.post("/api/chat-sessions/{session_id}/messages")
    async def save_session_message(request: Request, session_id: str):
        """Save a message to a specific chat session"""
        user_email = require_auth(request)
        data = await request.json()
        message_type = data.get('message_type')  # 'user' or 'assistant'
        content = data.get('content')
    
        if not message_type or not content:
             raise HTTPException(status_code=400, detail="message_type and content are required")
    
        if message_type not in ['user', 'assistant']:
             raise HTTPException(status_code=400, detail="message_type must be 'user' or 'assistant'")
    
        try:
        # First verify the session belongs to the user
            sessions = database.get_user_chat_sessions(user_email)
            session_exists = any(str(s['session_id']) == str(session_id) for s in sessions)
        
            if not session_exists:
                raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
            message_data = database.save_chat_message(session_id, user_email, message_type, content)
            if message_data:
            # Convert UUID to string for JSON serialization
                 message_data['message_id'] = str(message_data['message_id'])
                 message_data['session_id'] = str(message_data['session_id'])
                 return {"message": "Message saved successfully", "data": message_data}
            else:
                raise HTTPException(status_code=500, detail="Failed to save message")
        except Exception as e:
            print(f"Error saving session message: {e}")
            raise HTTPException(status_code=500, detail="Failed to save message")

    @app.get("/api/user-info")
    async def get_user_info(request: Request) -> UserResponse:
        """API endpoint to get current user information"""
        user_email = require_auth(request)
        
        try:
            user = database.get_user_by_email(user_email)
            if user:
                return UserResponse(
                    email=user['email'],
                    authenticated=True,
                    personality_available=PERSONALITY_AVAILABLE
                )
            else:
                raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            print(f"ERROR in get_user_info: {e}")
            raise HTTPException(status_code=500, detail="Failed to get user info")

    @app.post("/logout")
    async def logout_post(request: Request):
        """Handle POST logout requests"""
        request.session.pop('user', None)
        return {"message": "Logged out successfully"}

    @app.get("/logout")
    async def logout_get(request: Request):
        """Handle GET logout requests"""
        request.session.pop('user', None)
        return RedirectResponse(url="/login", status_code=303)

    @app.get("/signup", response_class=HTMLResponse)
    async def signup_get(request: Request):
        return templates.TemplateResponse("user/signup.html", get_template_context(request))

    # Solution 1: Accept JSON data instead of form data
   # Solution: Use Form(...) parameters with correct field names
    @app.post("/signup")
    async def signup_post(
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
        confirm_password: str = Form(..., alias="confirm-password")  # Handle the hyphen in form field
    ):
        if not email or not password or not confirm_password:
            return templates.TemplateResponse("user/signup.html", 
                get_template_context(request, error="All fields are required")
            )
    
        if password != confirm_password:
            return templates.TemplateResponse("user/signup.html", 
                get_template_context(request, error="Passwords do not match")
            )
    
        if len(password) < 6:
            return templates.TemplateResponse("user/signup.html", 
                get_template_context(request, error="Password must be at least 6 characters long")
            )

        try:
            if database.add_user(email, password):
                request.session['user'] = email
            # Initialize user preferences when they sign up
                memory_module = get_memory_module()
                if memory_module:
                    try:
                        memory_module.set_user_preference("chat_style", "casual", email)
                        memory_module.set_user_preference("preferred_name", "there", email)
                    except Exception as e:
                        print(f"WARNING: Could not set initial preferences: {e}")
            
                return RedirectResponse(url="/chat", status_code=303)
            else:
                return templates.TemplateResponse("user/signup.html", 
                     get_template_context(request, error="Email already registered")
                )
        except Exception as e:
            print(f"ERROR in signup: {e}")
            return templates.TemplateResponse("user/signup.html", 
                get_template_context(request, error="Signup failed. Please try again.")
            )
    @app.middleware("http")
    async def block_malformed_requests(request: Request, call_next):
        """Block malformed requests"""
    # Check if the request has a valid HTTP protocol
        if not request.url.scheme in ['http', 'https']:
            raise HTTPException(status_code=400, detail="Malformed request")
    
        response = await call_next(request)
        return response    


    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG') == '1' 
    uvicorn.run(
        "app:app",
        host='0.0.0.0',
        port=8000,
        reload=debug_mode,
        log_level="info"
    )