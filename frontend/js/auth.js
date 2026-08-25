document.addEventListener('DOMContentLoaded', () => {
    const authForm = document.getElementById('auth-form');
    const alertBox = document.getElementById('alert-message');
    const toggleBtn = document.getElementById('toggle-btn');
    const togglePrompt = document.getElementById('toggle-prompt');
    const formTitle = document.getElementById('form-title');
    const formSubtitle = document.getElementById('form-subtitle');
    const btnText = document.getElementById('btn-text');
    const formIcon = document.getElementById('form-icon');
    
    let isLogin = true;

    // Toggle between Login and Registration without replacing DOM elements
    toggleBtn.addEventListener('click', () => {
        isLogin = !isLogin;

        if (isLogin) {
            formTitle.textContent = 'Welcome Back';
            formSubtitle.textContent = 'Sign in to access document ingestion & quality workflows';
            btnText.textContent = 'Sign In';
            togglePrompt.textContent = "Don't have an account?";
            toggleBtn.textContent = 'Register';
            formIcon.textContent = '🔐';
        } else {
            formTitle.textContent = 'Create Account';
            formSubtitle.textContent = 'Register a new user to store and manage OCR document history';
            btnText.textContent = 'Register Account';
            togglePrompt.textContent = 'Already have an account?';
            toggleBtn.textContent = 'Sign In';
            formIcon.textContent = '📝';
        }

        showAlert('', 'hidden');
        authForm.reset();
    });

    // Handle standard submission
    authForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        showAlert('', 'hidden');
        btnText.textContent = isLogin ? 'Signing In...' : 'Registering...';

        const endpoint = isLogin ? '/auth/login' : '/auth/register';
        const payload = {
            username: authForm.username.value.trim(),
            password: authForm.password.value
        };

        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Authentication failed');
            }

            if (isLogin) {
                showAlert('Login successful! Redirecting...', 'success');
                localStorage.setItem('user', JSON.stringify(data));
                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 1000);
            } else {
                showAlert('Account created successfully! Switching to login...', 'success');
                setTimeout(() => {
                    toggleBtn.click(); // Trigger toggle back to login state smoothly
                }, 1500);
            }
        } catch (err) {
            showAlert(err.message, 'error');
        } finally {
            btnText.textContent = isLogin ? 'Sign In' : 'Register Account';
        }
    });

    function showAlert(message, type) {
        if (type === 'hidden') {
            alertBox.className = 'alert hidden';
            return;
        }
        alertBox.textContent = message;
        alertBox.className = `alert ${type}`;
    }
});