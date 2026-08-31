document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const authForm = document.getElementById('auth-form');
    const alertBox = document.getElementById('alert-message');
    const toggleBtn = document.getElementById('toggle-btn');
    const togglePrompt = document.getElementById('toggle-prompt');
    const formTitle = document.getElementById('form-title');
    const formSubtitle = document.getElementById('form-subtitle');
    const btnText = document.getElementById('btn-text');
    const formIcon = document.getElementById('form-icon');
    
    const passwordInput = document.getElementById('password');
    const togglePasswordBtn = document.getElementById('toggle-password-btn');
    const guestBtn = document.getElementById('guest-btn');
    
    const viewAuth = document.getElementById('view-auth');
    const viewApp = document.getElementById('view-app');
    const headerControls = document.getElementById('header-user-controls');
    const userBadge = document.getElementById('user-badge');
    const logoutBtn = document.getElementById('logout-btn');

    let isLogin = true;

    // 1. PERSISTENT AUTH STATE GUARD
    function checkAuthState() {
        const storedUser = localStorage.getItem('user');
        const isGuest = localStorage.getItem('isGuest') === 'true';

        if (storedUser || isGuest) {
            const username = isGuest ? 'Guest User' : JSON.parse(storedUser).username;
            showAppView(username, isGuest);
        } else {
            showAuthView();
        }
    }

    // SPA View Switchers
    function showAppView(username, isGuest) {
        viewAuth.classList.remove('active');
        viewAuth.classList.add('hidden');
        
        viewApp.classList.remove('hidden');
        viewApp.classList.add('active');
        
        headerControls.classList.remove('hidden');
        userBadge.textContent = isGuest ? '👤 Guest Mode' : `👤 ${username}`;
        
        // Broadcast custom event so the dynamic upload screen component knows auth is ready
        window.dispatchEvent(new CustomEvent('app:authenticated', { detail: { username, isGuest } }));
    }

    function showAuthView() {
        viewApp.classList.remove('active');
        viewApp.classList.add('hidden');
        
        viewAuth.classList.remove('hidden');
        viewAuth.classList.add('active');
        
        headerControls.classList.add('hidden');
    }

    // 2. PASSWORD VISIBILITY TOGGLE
    togglePasswordBtn.addEventListener('click', () => {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);
        togglePasswordBtn.style.color = type === 'text' ? 'var(--accent)' : 'var(--text-muted)';
    });

    // 3. GUEST MODE ACTION
    guestBtn.addEventListener('click', () => {
        localStorage.removeItem('user');
        localStorage.setItem('isGuest', 'true');
        showAppView('Guest User', true);
    });

    // 4. LOGOUT ACTION
    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('user');
        localStorage.removeItem('isGuest');
        localStorage.removeItem('access_token');
        localStorage.removeItem('token');
        authForm.reset();
        showAlert('', 'hidden');
        showAuthView();
    });

    // 5. REGISTER / LOGIN TOGGLE
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

    // 6. FORM SUBMISSION (LOGIN / REGISTER)
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
                showAlert('Login successful! Accessing workspace...', 'success');
                localStorage.removeItem('isGuest');
                localStorage.setItem('user', JSON.stringify(data));

                // Save auth token if returned by backend
                if (data.access_token || data.token) {
                    localStorage.setItem('access_token', data.access_token || data.token);
                }

                setTimeout(() => {
                    showAppView(data.username, false);
                }, 800);
            } else {
                showAlert('Account created successfully! Switching to sign in...', 'success');
                setTimeout(() => {
                    toggleBtn.click();
                }, 1200);
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

    // Initialize Auth Check
    checkAuthState();
});