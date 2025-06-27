// chat-functionality.js - Chat interface functionality with timeout fix
document.addEventListener("DOMContentLoaded", function () {
  const chatArea = document.getElementById("chatArea");
  const messageInput = document.getElementById("messageInput");
  const sendBtn = document.getElementById("sendBtn");

  // Configure marked for better markdown parsing
  marked.setOptions({
    breaks: true,
    gfm: true
  });

  function parseMarkdown(text) {
    // Simple markdown parsing for common elements
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/__(.*?)__/g, '<strong>$1</strong>')
      .replace(/_(.*?)_/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/^### (.*$)/gm, '<h3>$1</h3>')
      .replace(/^## (.*$)/gm, '<h2>$1</h2>')
      .replace(/^# (.*$)/gm, '<h1>$1</h1>')
      .replace(/^\* (.*$)/gm, '<li>$1</li>')
      .replace(/^- (.*$)/gm, '<li>$1</li>')
      .replace(/\n/g, '<br>');
  }

  function addMessage(text, isUser) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `flex ${isUser ? "justify-end" : "justify-start"} mb-4`;

    const messageBubble = document.createElement("div");
    messageBubble.className = isUser
      ? "bg-primary text-white rounded-lg rounded-tr-none py-2 px-4 max-w-[75%] whitespace-pre-wrap"
      : "bg-gray-100 text-gray-900 rounded-lg rounded-tl-none py-2 px-4 max-w-[75%] message-bubble";

    messageDiv.appendChild(messageBubble);
    chatArea.appendChild(messageDiv);
    chatArea.scrollTop = chatArea.scrollHeight;

    if (isUser) {
      messageBubble.textContent = text;
    }

    return messageBubble;
  }

  function updateMessageContent(messageBubble, content) {
    // Use innerHTML to render HTML/markdown
    messageBubble.innerHTML = parseMarkdown(content);
  }

  function createSearchAnimation(type = 'searching') {
    const animationDiv = document.createElement("div");
    animationDiv.className = "search-animation";
    
    const icon = document.createElement("i");
    icon.className = type === 'searching' ? "ri-search-line search-icon" : "ri-brain-line search-icon";
    
    const text = document.createElement("span");
    text.textContent = type === 'searching' ? "Searching the web" : "Summarizing results";
    
    const dotsContainer = document.createElement("div");
    dotsContainer.className = "search-dots";
    
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement("div");
      dot.className = "search-dot";
      dotsContainer.appendChild(dot);
    }
    
    animationDiv.appendChild(icon);
    animationDiv.appendChild(text);
    animationDiv.appendChild(dotsContainer);
    
    return animationDiv;
  }

  function removeSearchAnimation(messageBubble) {
    const animation = messageBubble.querySelector('.search-animation');
    if (animation) {
      animation.classList.add('fade-out');
      setTimeout(() => {
        if (animation.parentNode) {
          animation.remove();
        }
      }, 300);
    }
  }

  async function sendMessageStreaming() {
    const text = messageInput.value.trim();
    if (!text) return;

    addMessage(text, true);
    messageInput.value = "";

    try {
      const response = await fetch("/chat-stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: 'include',
        body: JSON.stringify({ message: text }),
      });

      if (response.status === 401) {
        window.location.href = '/login';
        return;
      }

      if (!response.body) {
        addMessage("Error: Streaming not supported.", false);
        return;
      }

      const messageBubble = addMessage("", false);
      let currentAnimation = null;
      let animationTimeout = null;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiMessage = "";
      let isSearching = false;
      let hasShownResults = false;

      // Set a timeout to remove animation if it's been too long
      const setAnimationTimeout = () => {
        if (animationTimeout) clearTimeout(animationTimeout);
        animationTimeout = setTimeout(() => {
          if (currentAnimation) {
            removeSearchAnimation(messageBubble);
            currentAnimation = null;
            // Show whatever content we have so far
            if (aiMessage && !hasShownResults) {
              updateMessageContent(messageBubble, aiMessage);
              hasShownResults = true;
            }
          }
        }, 8000); // 8 second timeout
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        aiMessage += chunk;

        // Check if we're in a search operation
        if ((aiMessage.includes("Searching") || aiMessage.includes("search")) && !isSearching && !hasShownResults) {
          isSearching = true;
          currentAnimation = createSearchAnimation('searching');
          messageBubble.appendChild(currentAnimation);
          setAnimationTimeout();
        } 
        // Check if we're summarizing
        else if (aiMessage.toLowerCase().includes("summariz") && currentAnimation && !hasShownResults) {
          removeSearchAnimation(messageBubble);
          currentAnimation = createSearchAnimation('summarizing');
          messageBubble.appendChild(currentAnimation);
          setAnimationTimeout();
        }
        // Check for final results or if we have substantial content
        else if (
          (aiMessage.includes("Here's what I found:") || 
           aiMessage.includes("Search result:") ||
           (!isSearching && aiMessage.length > 20)) && 
          !hasShownResults
        ) {
          // Clear any existing animation and timeout
          if (animationTimeout) {
            clearTimeout(animationTimeout);
            animationTimeout = null;
          }
          
          if (currentAnimation) {
            removeSearchAnimation(messageBubble);
            currentAnimation = null;
          }
          
          // Show the content
          let contentToShow = aiMessage;
          
          // Clean up search-related prefixes if they exist
          if (contentToShow.includes("Here's what I found:")) {
            const finalIndex = contentToShow.indexOf("Here's what I found:");
            contentToShow = contentToShow.substring(finalIndex);
          } else if (contentToShow.includes("Search result:")) {
            // Remove "Search result:" prefix
            contentToShow = contentToShow.replace(/^.*Search result:\s*/, "");
          }
          
          updateMessageContent(messageBubble, contentToShow);
          hasShownResults = true;
          isSearching = false;
        }
        // If we're not searching and haven't shown results, show content normally
        else if (!isSearching && !hasShownResults) {
          updateMessageContent(messageBubble, aiMessage);
        }
        // If we've already shown results, continue updating
        else if (hasShownResults) {
          let contentToShow = aiMessage;
          
          // Clean up search-related prefixes if they exist
          if (contentToShow.includes("Here's what I found:")) {
            const finalIndex = contentToShow.indexOf("Here's what I found:");
            contentToShow = contentToShow.substring(finalIndex);
          } else if (contentToShow.includes("Search result:")) {
            contentToShow = contentToShow.replace(/^.*Search result:\s*/, "");
          }
          
          updateMessageContent(messageBubble, contentToShow);
        }

        chatArea.scrollTop = chatArea.scrollHeight;
      }

      // Final cleanup - ensure animation is removed and content is shown
      if (animationTimeout) {
        clearTimeout(animationTimeout);
      }
      
      if (currentAnimation) {
        removeSearchAnimation(messageBubble);
      }
      
      if (!hasShownResults && aiMessage) {
        let finalContent = aiMessage;
        
        // Clean up any search prefixes
        if (finalContent.includes("Search result:")) {
          finalContent = finalContent.replace(/^.*Search result:\s*/, "");
        }
        
        updateMessageContent(messageBubble, finalContent);
      }

    } catch (error) {
      console.error("Error sending message:", error);
      addMessage("Error: Network issue or server problem.", false);
    }
  }

  sendBtn.addEventListener("click", sendMessageStreaming);
  messageInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      sendMessageStreaming();
    }
  });

  // Demo message with formatting
  setTimeout(() => {
    const welcomeMessage = "Hello! I'm your AI assistant.";
    const messageBubble = addMessage("", false);
    updateMessageContent(messageBubble, welcomeMessage);
  }, 500);
});