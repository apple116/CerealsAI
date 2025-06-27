document.addEventListener('DOMContentLoaded', function () {
  const userProfileBtn = document.getElementById('userProfileBtn');
  const userMenu = document.getElementById('userMenu');
  const themeToggle = document.getElementById("themeToggle");

  if (userProfileBtn && userMenu) {
      userProfileBtn.addEventListener('click', function (event) {
          event.stopPropagation();
          userMenu.classList.toggle('active');
      });

      document.addEventListener('click', function (event) {
          if (!userProfileBtn.contains(event.target) && !userMenu.contains(event.target)) {
              userMenu.classList.remove('active');
          }
      });
  }

  themeToggle.addEventListener("click", function () {
    document.body.classList.toggle("dark-mode");
    // Optionally, save the theme preference to localStorage
    if (document.body.classList.contains("dark-mode")) {
      localStorage.setItem("theme", "dark");
    } else {
      localStorage.setItem("theme", "light");
    }
  });

  // Apply saved theme preference
  if (localStorage.getItem("theme") === "dark") {
    document.body.classList.add("dark-mode");
  }
});
