// chat-functionality.js - Fixed version with proper AI message display and dark mode support
class ChatSessionManager {
    constructor() {
        this.currentSessionId = null;
        this.sessions = [];
        this.isLoading = false;
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.chatArea = document.getElementById('chatArea');
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadChatSessions();
        this.createSessionSidebar();
        
        // Load the most recent session or create a new one
        if (this.sessions.length > 0) {
            await this.loadSession(this.sessions[0].session_id);
        } else {
            await this.createNewSession();
        }
        
        // Show welcome message for new sessions
        if (!this.sessions.length || this.chatArea.children.length === 0) {
            this.showWelcomeMessage();
        }
    }

    setupEventListeners() {
        // Send message on Enter key
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessageStreaming();
            }
        });

        // Send button click
        this.sendBtn.addEventListener('click', () => {
            this.sendMessageStreaming();
        });
    }

    createSessionSidebar() {
        // Check if sidebar already exists
        if (document.querySelector('.session-sidebar')) {
            this.updateSessionList();
            return;
        }

        const chatContainer = document.querySelector('.chat-container') || document.body;
        
        // Create sidebar HTML
        const sidebarHTML = `
            <div class="session-sidebar" style="width: 280px; background: #f8f9fa; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; height: 100vh; position: fixed; left: 0; top: 0; z-index: 1000;">
                <div class="sidebar-header" style="padding: 16px; border-bottom: 1px solid #e5e7eb;">
                    <button id="newChatBtn" style="width: 100%; background: #660000; color: white; padding: 8px 16px; border-radius: 8px; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: background-color 0.2s;" onmouseover="this.style.background='#550000'" onmouseout="this.style.background='#660000'">
                        <i class="ri-add-line"></i>
                        New Chat
                    </button>
                </div>
                <div class="session-list" style="flex: 1; overflow-y: auto; padding: 8px;">
                    <div id="sessionListContainer"></div>
                </div>
            </div>
        `;

        // Insert sidebar
        chatContainer.insertAdjacentHTML('afterbegin', sidebarHTML);
        
        // Adjust main content to account for sidebar
        const mainContent = chatContainer;
        mainContent.style.marginLeft = '280px';

        // Add event listener for new chat button
        document.getElementById('newChatBtn').addEventListener('click', () => {
            this.createNewSession();
        });

        this.updateSessionList();
    }

    updateSessionList() {
        const container = document.getElementById('sessionListContainer');
        if (!container) return;

        container.innerHTML = this.sessions.map(session => `
            <div class="session-item ${session.session_id === this.currentSessionId ? 'active' : ''}" 
                 data-session-id="${session.session_id}"
                 style="padding: 12px; margin: 4px 0; border-radius: 8px; cursor: pointer; transition: all 0.2s; ${session.session_id === this.currentSessionId ? 'background: #660000; color: white;' : 'background: white;'}"
                 onmouseover="if('${session.session_id}' !== '${this.currentSessionId}') this.style.background='#f3f4f6'"
                 onmouseout="if('${session.session_id}' !== '${this.currentSessionId}') this.style.background='white'">
                <div class="session-title" style="font-weight: 500; font-size: 14px; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    ${session.title || 'New Chat'}
                </div>
                <div class="session-date" style="font-size: 12px; opacity: 0.7;">
                    ${this.formatDate(session.created_at || session.updated_at)}
                </div>
                <div class="session-actions" style="margin-top: 8px; display: flex; gap: 8px;">
                    <button class="delete-session-btn" data-session-id="${session.session_id}" 
                            style="padding: 4px 8px; font-size: 11px; background: rgba(239, 68, 68, 0.1); color: #dc2626; border: none; border-radius: 4px; cursor: pointer;"
                            onclick="event.stopPropagation();">
                        <i class="ri-delete-bin-line"></i>
                    </button>
                </div>
            </div>
        `).join('');

        // Add click listeners
        container.querySelectorAll('.session-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.session-actions')) {
                    const sessionId = item.dataset.sessionId;
                    this.loadSession(sessionId);
                }
            });
        });

        // Add delete listeners
        container.querySelectorAll('.delete-session-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const sessionId = btn.dataset.sessionId;
                this.deleteSession(sessionId);
            });
        });
    }

    async loadChatSessions() {
        try {
            const response = await fetch('/api/chat-sessions');
            if (response.ok) {
                const data = await response.json();
                this.sessions = Array.isArray(data) ? data : (data.sessions || []);
                console.log('Loaded sessions:', this.sessions);
            } else if (response.status === 401) {
                window.location.href = '/login';
            } else {
                console.error('Failed to load sessions:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Error loading chat sessions:', error);
        }
    }

    async createNewSession() {
        try {
            const response = await fetch('/api/chat-sessions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: `Chat ${new Date().toLocaleString()}`
                })
            });

            if (response.ok) {
                const newSession = await response.json();
                this.sessions.unshift(newSession);
                this.currentSessionId = newSession.session_id;
                this.clearChatArea();
                this.updateSessionList();
                this.showWelcomeMessage();
                console.log('Created new session:', newSession);
            } else if (response.status === 401) {
                window.location.href = '/login';
            } else {
                console.error('Failed to create session:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Error creating new session:', error);
        }
    }

    async loadSession(sessionId) {
        if (this.currentSessionId === sessionId) return;

        try {
            this.currentSessionId = sessionId;
            this.updateSessionList();

            const response = await fetch(`/api/chat-sessions/${sessionId}/messages`);
            if (response.ok) {
                const data = await response.json();
                const messages = data.messages || [];
                this.displayMessages(messages);
                console.log('Loaded messages for session:', sessionId, messages);
            } else if (response.status === 401) {
                window.location.href = '/login';
            } else {
                console.error('Failed to load session messages:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Error loading session:', error);
        }
    }

    async deleteSession(sessionId) {
        if (!confirm('Are you sure you want to delete this chat?')) return;

        try {
            const response = await fetch(`/api/chat-sessions/${sessionId}`, {
                method: 'DELETE'
        });

            if (response.ok) {
                this.sessions = this.sessions.filter(s => s.session_id !== sessionId);
            
                if (this.currentSessionId === sessionId) {
                    if (this.sessions.length > 0) {
                        await this.loadSession(this.sessions[0].session_id);
                    } else {
                        await this.createNewSession();
                    }
                }
            
                this.updateSessionList();
                console.log('Deleted session:', sessionId);
            } else if (response.status === 401) {
                window.location.href = '/login';
            } else {
                console.error('Failed to delete session:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Error deleting session:', error);
        }
    }

    displayMessages(messages) {
        this.clearChatArea();
        
        messages.forEach(message => {
            this.addMessage(message.content, message.message_type === 'user');
        });

        this.scrollToBottom();
    }

    clearChatArea() {
        this.chatArea.innerHTML = '';
    }

    showWelcomeMessage() {
        setTimeout(() => {
            const welcomeMessage = "Hello! I'm your AI assistant. How can I help you today?";
            const messageBubble = this.addMessage("", false);
            this.updateMessageContent(messageBubble, welcomeMessage);
        }, 500);
    }

    // Markdown parsing function
    parseMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/__(.*?)__/g, '<strong>$1</strong>')
            .replace(/_(.*?)_/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code style="background: #f1f5f9; padding: 2px 4px; border-radius: 3px; font-family: monospace;">$1</code>')
            .replace(/^### (.*$)/gm, '<h3 style="font-size: 1.125rem; font-weight: 600; margin: 0.5rem 0;">$1</h3>')
            .replace(/^## (.*$)/gm, '<h2 style="font-size: 1.25rem; font-weight: 600; margin: 0.5rem 0;">$1</h2>')
            .replace(/^# (.*$)/gm, '<h1 style="font-size: 1.5rem; font-weight: 600; margin: 0.5rem 0;">$1</h1>')
            .replace(/^\* (.*$)/gm, '<li style="margin-left: 1rem;">$1</li>')
            .replace(/^- (.*$)/gm, '<li style="margin-left: 1rem;">$1</li>')
            .replace(/\n/g, '<br>');
    }

    addMessage(text, isUser) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `flex ${isUser ? "justify-end" : "justify-start"} mb-4`;

        const messageBubble = document.createElement("div");
        messageBubble.className = isUser
            ? "bg-primary text-white rounded-lg rounded-tr-none py-2 px-4 max-w-[75%] whitespace-pre-wrap"
            : "bg-gray-100 text-gray-900 rounded-lg rounded-tl-none py-2 px-4 max-w-[75%] message-bubble";

        messageDiv.appendChild(messageBubble);
        this.chatArea.appendChild(messageDiv);
        this.scrollToBottom();

        if (isUser) {
            messageBubble.textContent = text;
        } else if (text) {
            // If we have initial text, display it
            this.updateMessageContent(messageBubble, text);
        }

        return messageBubble;
    }

    updateMessageContent(messageBubble, content) {
        messageBubble.innerHTML = this.parseMarkdown(content);
    }

    createLoadingIndicator() {
        const loadingDiv = document.createElement("div");
        loadingDiv.className = "loading-indicator";
        loadingDiv.style.cssText = `
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px;
            color: #666;
            font-size: 14px;
        `;
        
        const icon = document.createElement("i");
        icon.className = "ri-loader-4-line animate-spin";
        
        const text = document.createElement("span");
        text.textContent = "Thinking...";
        
        loadingDiv.appendChild(icon);
        loadingDiv.appendChild(text);
        
        return loadingDiv;
    }

    removeLoadingIndicator(messageBubble) {
        const loading = messageBubble.querySelector('.loading-indicator');
        if (loading) {
            loading.remove();
        }
    }

    async sendMessageStreaming() {
        const text = this.messageInput.value.trim();
        if (!text || this.isLoading) return;

        // Ensure we have a current session
        if (!this.currentSessionId) {
            await this.createNewSession();
        }

        this.isLoading = true;
        this.addMessage(text, true);
        this.messageInput.value = "";

        // Update send button to show loading state
        const originalSendBtnContent = this.sendBtn.innerHTML;
        this.sendBtn.innerHTML = '<i class="ri-loader-4-line ri-lg animate-spin"></i>';
        this.sendBtn.disabled = true;

        try {
            const response = await fetch("/chat-stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: 'include',
                body: JSON.stringify({ 
                    message: text,
                    session_id: this.currentSessionId 
                }),
            });

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            if (!response.body) {
                this.addMessage("Error: Streaming not supported.", false);
                return;
            }

            // Create AI message bubble with loading indicator
            const messageBubble = this.addMessage("", false);
            const loadingIndicator = this.createLoadingIndicator();
            messageBubble.appendChild(loadingIndicator);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let aiMessage = "";
            let hasStartedDisplaying = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                aiMessage += chunk;

                // Remove loading indicator and start displaying content once we have some
                if (!hasStartedDisplaying && aiMessage.trim().length > 0) {
                    this.removeLoadingIndicator(messageBubble);
                    hasStartedDisplaying = true;
                }

                // Update the message content
                if (hasStartedDisplaying) {
                    this.updateMessageContent(messageBubble, aiMessage);
                }

                this.scrollToBottom();
            }

            // Final update to ensure all content is displayed
            if (aiMessage) {
                this.removeLoadingIndicator(messageBubble);
                this.updateMessageContent(messageBubble, aiMessage);
            }

            // Save messages to current session
            await this.saveMessagesToSession(text, aiMessage);

        } catch (error) {
            console.error("Error sending message:", error);
            this.addMessage("Error: Failed to get response from the server.", false);
        } finally {
            this.isLoading = false;
            this.sendBtn.innerHTML = originalSendBtnContent;
            this.sendBtn.disabled = false;
            this.scrollToBottom();
        }
    }

    async saveMessagesToSession(userMessage, aiResponse) {
        if (!this.currentSessionId) {
            console.error('No current session ID available for saving messages');
            return;
        }

        try {
            // Save user message
            const userResponse = await fetch(`/api/chat-sessions/${this.currentSessionId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message_type: 'user',
                    content: userMessage
                })
            });

            if (!userResponse.ok) {
                console.error('Failed to save user message:', userResponse.status, userResponse.statusText);
                return;
            }

            // Save AI response
            const aiResponseResult = await fetch(`/api/chat-sessions/${this.currentSessionId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message_type: 'assistant',
                    content: aiResponse
                })
            });

            if (!aiResponseResult.ok) {
                console.error('Failed to save AI response:', aiResponseResult.status, aiResponseResult.statusText);
                return;
            }

            console.log('Messages saved successfully to session:', this.currentSessionId);
            
        } catch (error) {
            console.error('Error saving messages to session:', error);
        }
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays === 1) {
            return 'Today';
        } else if (diffDays === 2) {
            return 'Yesterday';
        } else if (diffDays <= 7) {
            return `${diffDays - 1} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatArea.scrollTop = this.chatArea.scrollHeight;
        }, 100);
    }
}

// Initialize the chat session manager when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
    // Configure marked for better markdown parsing if available
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true
        });
    }

    // Initialize the enhanced chat manager
    window.chatManager = new ChatSessionManager();
});

// Add CSS styles for the session management with dark mode support
const additionalStyles = `
    <style>
        .session-sidebar {
            min-width: 280px;
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }
        
        .session-item {
            transition: all 0.2s ease;
        }
        
        .session-item.active {
            background: #660000 !important;
            color: white !important;
        }
        
        /* Dark mode styles for session sidebar */
        body.dark-mode .session-sidebar {
            background:rgb(29, 29, 29) !important;
            border-right-color:rgb(31, 31, 31) !important;
        }
        
        body.dark-mode .sidebar-header {
            border-bottom-color:rgb(34, 34, 34) !important;
        }
        
        body.dark-mode .session-item:not(.active) {
            background:rgb(38, 38, 38) !important;
            color: #f9fafb !important;
        }
        
        body.dark-mode .session-item:not(.active):hover {
            background:rgb(41, 41, 41) !important;
        }
        
        body.dark-mode .session-date {
            color: #d1d5db !important;
        }
        
        body.dark-mode .delete-session-btn {
            background: rgba(239, 68, 68, 0.2) !important;
            color: #f87171 !important;
        }
        
        body.dark-mode .delete-session-btn:hover {
            background: rgba(239, 68, 68, 0.3) !important;
        }
        
        /* Dark mode for message bubbles */
        body.dark-mode .message-bubble {
            background:rgb(39, 39, 39) !important;
            color: #f9fafb !important;
        }
        
        body.dark-mode .loading-indicator {
            color: #d1d5db !important;
        }
        
        .animate-spin {
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        .loading-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px;
            color: #666;
            font-size: 14px;
        }
        
        .chat-area {
            overflow-y: auto;
            padding: 16px;
        }
        
        .message {
            margin: 8px 0;
        }
        
        /* Custom scrollbar for session list */
        .session-list::-webkit-scrollbar {
            width: 6px;
        }
        
        .session-list::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        
        body.dark-mode .session-list::-webkit-scrollbar-track {
            background: #1f2937;
        }
        
        .session-list::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 3px;
        }
        
        body.dark-mode .session-list::-webkit-scrollbar-thumb {
            background: #6b7280;
        }
        
        .session-list::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }
        
        body.dark-mode .session-list::-webkit-scrollbar-thumb:hover {
            background: #9ca3af;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            .session-sidebar {
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }
            
            .session-sidebar.mobile-open {
                transform: translateX(0);
            }
            
            .chat-container {
                margin-left: 0 !important;
            }
        }
        
        /* Ensure proper layout for chat container */
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            transition: margin-left 0.3s ease;
        }
        
        /* Button styling fixes */
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        /* Additional dark mode improvements */
        body.dark-mode {
            background-color:rgb(2, 3, 4);
            color: #f9fafb;
        }
        
        body.dark-mode .chat-container {
            background-color:rgb(0, 0, 0);
        }
        
        body.dark-mode .session-title {
            color: inherit;
        }
    </style>
`;

// Add styles to document head
if (document.head) {
    document.head.insertAdjacentHTML('beforeend', additionalStyles);
}