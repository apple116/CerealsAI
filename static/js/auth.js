function togglePassword(inputId, toggleElement) {
  const passwordInput = document.getElementById(inputId);
  const icon = toggleElement.querySelector('i');
  
  if (passwordInput.type === 'password') {
    passwordInput.type = 'text';
    icon.classList.remove('ri-eye-line');
    icon.classList.add('ri-eye-off-line');
  } else {
    passwordInput.type = 'password';
    icon.classList.remove('ri-eye-off-line');
    icon.classList.add('ri-eye-line');
  }
}

// Form submission with loading state
function handleSubmit(button, loadingText) {
  const originalText = button.innerHTML;
  
  // Add loading state
  button.classList.add('loading');
  button.innerHTML = `<span class="loading-spinner"></span>${loadingText}`;
  
  // Simulate form processing
  setTimeout(() => {
    button.classList.remove('loading');
    button.innerHTML = originalText;
    
    // Here you would normally submit the form
    console.log('Form submitted successfully');
  }, 2000);
}

// Enhanced form validation
document.addEventListener('DOMContentLoaded', function() {
  const form = document.querySelector('.auth-form');
  const inputs = document.querySelectorAll('.auth-input');
  const submitButton = document.querySelector('.primary-btn');
  
  // Add validation to all inputs
  inputs.forEach(input => {
    input.addEventListener('blur', function() {
      validateInput(this);
    });
    
    input.addEventListener('input', function() {
      if (this.classList.contains('error')) {
        validateInput(this);
      }
      
      // Real-time password confirmation check
      if (this.id === 'confirm-password' || this.id === 'password') {
        validatePasswordMatch();
      }
    });
    
    // Add focus animations
    input.addEventListener('focus', function() {
      this.parentElement.classList.add('focused');
    });
    
    input.addEventListener('blur', function() {
      this.parentElement.classList.remove('focused');
    });
  });
  
  // Form submission handling
  if (form) {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      
      let isValid = true;
      
      // Validate all inputs
      inputs.forEach(input => {
        if (!validateInput(input)) {
          isValid = false;
        }
      });
      
      // Special validation for signup form
      if (document.getElementById('confirm-password')) {
        if (!validatePasswordMatch()) {
          isValid = false;
        }
        
        // Check terms checkbox
        const termsCheckbox = document.getElementById('terms');
        if (termsCheckbox && !termsCheckbox.checked) {
          showError(termsCheckbox.closest('.custom-checkbox').querySelector('.checkmark'), 'Please accept the terms and conditions');
          isValid = false;
        }
      }
      
      if (isValid) {
        // Add loading state to submit button
        const originalText = submitButton.innerHTML;
        const loadingText = submitButton.textContent.includes('Sign In') ? 'Signing in...' : 'Creating account...';
        
        submitButton.classList.add('loading');
        submitButton.innerHTML = `<span class="loading-spinner"></span>${loadingText}`;
        submitButton.disabled = true;
        
        // Simulate API call
        setTimeout(() => {
          // In a real application, you would submit the form here
          console.log('Form submitted successfully');
          
          // For demonstration, reset the button
          submitButton.classList.remove('loading');
          submitButton.innerHTML = originalText;
          submitButton.disabled = false;
          
          // Actually submit the form (uncomment in production)
          form.submit();
        }, 2000);
      } else {
        // Shake animation for invalid form
        form.classList.add('shake');
        setTimeout(() => {
          form.classList.remove('shake');
        }, 600);
      }
    });
  }
});

// Input validation functions
function validateInput(input) {
  const value = input.value.trim();
  const inputType = input.type;
  const inputId = input.id;
  
  // Remove existing error state
  clearError(input);
  
  // Check if field is empty
  if (!value) {
    showError(input, 'This field is required');
    return false;
  }
  
  // Email validation
  if (inputType === 'email') {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      showError(input, 'Please enter a valid email address');
      return false;
    }
  }
  
  // Password validation
  if (inputId === 'password') {
    if (value.length < 6) {
      showError(input, 'Password must be at least 8 characters long');
      return false;
    }
    
    // Check for at least one uppercase, one lowercase, and one number
    const hasUppercase = /[A-Z]/.test(value);
    const hasLowercase = /[a-z]/.test(value);
    const hasNumber = /\d/.test(value);
    
    if (!hasUppercase || !hasLowercase || !hasNumber) {
      showError(input, 'Password must contain uppercase, lowercase, and number');
      return false;
    }
  }
  
  // Full name validation
  if (inputId === 'fullname') {
    if (value.length < 2) {
      showError(input, 'Full name must be at least 2 characters long');
      return false;
    }
    
    const nameRegex = /^[a-zA-Z\s]+$/;
    if (!nameRegex.test(value)) {
      showError(input, 'Full name can only contain letters and spaces');
      return false;
    }
  }
  
  return true;
}

function validatePasswordMatch() {
  const password = document.getElementById('password');
  const confirmPassword = document.getElementById('confirm-password');
  
  if (!password || !confirmPassword) return true;
  
  clearError(confirmPassword);
  
  if (password.value !== confirmPassword.value) {
    showError(confirmPassword, 'Passwords do not match');
    return false;
  }
  
  return true;
}

function showError(input, message) {
  const inputGroup = input.closest('.input-group') || input.closest('.custom-checkbox');
  if (!inputGroup) return;
  
  // Add error class
  input.classList.add('error');
  inputGroup.classList.add('error');
  
  // Remove existing error message
  const existingError = inputGroup.querySelector('.error-message');
  if (existingError) {
    existingError.remove();
  }
  
  // Create and add error message
  const errorElement = document.createElement('div');
  errorElement.className = 'error-message';
  errorElement.textContent = message;
  inputGroup.appendChild(errorElement);
}

function clearError(input) {
  const inputGroup = input.closest('.input-group') || input.closest('.custom-checkbox');
  if (!inputGroup) return;
  
  // Remove error classes
  input.classList.remove('error');
  inputGroup.classList.remove('error');
  
  // Remove error message
  const errorMessage = inputGroup.querySelector('.error-message');
  if (errorMessage) {
    errorMessage.remove();
  }
}

// Social login handlers
document.addEventListener('DOMContentLoaded', function() {
  const socialButtons = document.querySelectorAll('.social-btn');
  
  socialButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      
      const provider = this.textContent.trim();
      const originalText = this.innerHTML;
      
      // Add loading state
      this.classList.add('loading');
      this.innerHTML = `<span class="loading-spinner"></span>Connecting...`;
      
      // Simulate social login
      setTimeout(() => {
        this.classList.remove('loading');
        this.innerHTML = originalText;
        
        console.log(`${provider} login initiated`);
        // Here you would redirect to the actual social login provider
      }, 1500);
    });
  });
});

// Keyboard navigation enhancement
document.addEventListener('keydown', function(e) {
  // Enter key on form inputs
  if (e.key === 'Enter' && e.target.classList.contains('auth-input')) {
    const inputs = Array.from(document.querySelectorAll('.auth-input'));
    const currentIndex = inputs.indexOf(e.target);
    
    if (currentIndex < inputs.length - 1) {
      // Focus next input
      inputs[currentIndex + 1].focus();
    } else {
      // Submit form
      const submitButton = document.querySelector('.primary-btn');
      if (submitButton) {
        submitButton.click();
      }
    }
  }
});

// Auto-focus first input on page load
window.addEventListener('load', function() {
  const firstInput = document.querySelector('.auth-input');
  if (firstInput) {
    firstInput.focus();
  }
});

// Remember me functionality
document.addEventListener('DOMContentLoaded', function() {
  const rememberCheckbox = document.getElementById('remember');
  const emailInput = document.getElementById('email');
  
  if (rememberCheckbox && emailInput) {
    // Load saved email if remember me was checked
    const savedEmail = localStorage.getItem('rememberedEmail');
    if (savedEmail) {
      emailInput.value = savedEmail;
      rememberCheckbox.checked = true;
    }
    
    // Save email when form is submitted
    const form = document.querySelector('.auth-form');
    if (form) {
      form.addEventListener('submit', function() {
        if (rememberCheckbox.checked) {
          localStorage.setItem('rememberedEmail', emailInput.value);
        } else {
          localStorage.removeItem('rememberedEmail');
        }
      });
    }
  }
});

// Utility function for smooth scrolling to error
function scrollToError() {
  const firstError = document.querySelector('.error');
  if (firstError) {
    firstError.scrollIntoView({ 
      behavior: 'smooth', 
      block: 'center' 
    });
  }
}