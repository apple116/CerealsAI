// user-profile.js - User profile functionality
document.addEventListener("DOMContentLoaded", function () {
  const userProfileBtn = document.getElementById("userProfileBtn");
  const userMenu = document.getElementById("userMenu");
  const themeToggle = document.getElementById("themeToggle");
  const signOutBtn = document.getElementById("signOutBtn");
  const userEmail = document.getElementById("userEmail");

  // Function to get user info from the server
  async function loadUserInfo() {
    try {
      const response = await fetch('/api/user-info', {
        method: 'GET',
        credentials: 'include' // Include cookies for session-based auth
      });
      
      if (response.ok) {
        const userData = await response.json();
        userEmail.textContent = userData.email;
      } else if (response.status === 401) {
        // User not authenticated, redirect to login
        window.location.href = '/login';
      } else {
        console.error('Failed to load user info');
        userEmail.textContent = 'Error loading user';
      }
    } catch (error) {
      console.error('Error loading user info:', error);
      userEmail.textContent = 'Error loading user';
    }
  }

  // Load user info on page load
  loadUserInfo();

  userProfileBtn.addEventListener("click", function (event) {
      event.stopPropagation();
      userMenu.classList.toggle("active");
  });

  document.addEventListener("click", function (event) {
    if (
      !userProfileBtn.contains(event.target) &&
      !userMenu.contains(event.target)
    ) {
      userMenu.classList.remove("active");
    }
  });

  themeToggle.addEventListener("click", function () {
    document.body.classList.toggle("dark-mode");
    if (document.body.classList.contains("dark-mode")) {
      localStorage.setItem("theme", "dark");
    } else {
      localStorage.setItem("theme", "light");
    }
  });

  // Sign out functionality
  signOutBtn.addEventListener("click", async function (event) {
    event.preventDefault();
    
    try {
      const response = await fetch('/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include' // Include cookies for session-based auth
      });
      
      if (response.ok) {
        // Redirect to login page
        window.location.href = '/login';
      } else {
        console.error('Sign out failed');
        // Still redirect for better UX
        window.location.href = '/login';
      }
    } catch (error) {
      console.error('Sign out error:', error);
      // Redirect anyway for better UX
      window.location.href = '/login';
    }
  });

  // Load saved theme
  if (localStorage.getItem("theme") === "dark") {
    document.body.classList.add("dark-mode");
  }
});