/**
 * Authentication Service
 * Handles user authentication and token management
 */
class AuthService {
    constructor() {
        this.isAuthenticated = false;
        this.user = null;
        this.callbacks = {
            onAuthChange: []
        };

        // Initialize authentication state
        this.init();
    }

    init() {
        const token = localStorage.getItem(CONFIG.STORAGE_KEYS.API_TOKEN);
        if (token) {
            this.validateStoredToken();
        }
    }

    async validateStoredToken() {
        try {
            const user = await apiService.validateToken();
            this.setAuthenticatedState(true, user);
        } catch (error) {
            console.warn('Stored token is invalid:', error.message);
            this.setAuthenticatedState(false);
        }
    }

    async authenticate(token) {
        try {
            apiService.setToken(token);
            const user = await apiService.validateToken();
            this.setAuthenticatedState(true, user);
            return true;
        } catch (error) {
            apiService.setToken('');
            this.setAuthenticatedState(false);
            throw error;
        }
    }

    logout() {
        apiService.setToken('');
        this.setAuthenticatedState(false);
    }

    setAuthenticatedState(authenticated, user = null) {
        this.isAuthenticated = authenticated;
        this.user = user;

        // Update UI
        this.updateAuthUI();

        // Trigger callbacks
        this.callbacks.onAuthChange.forEach(callback => {
            callback(authenticated, user);
        });
    }

    updateAuthUI() {
        const indicator = document.getElementById('auth-indicator');
        const statusText = document.getElementById('auth-status-text');
        const authSection = document.getElementById('auth-section');
        const authenticatedElements = document.querySelectorAll('.authenticated');

        if (this.isAuthenticated) {
            indicator?.classList.add('authenticated');
            if (statusText) statusText.textContent = 'Authenticated';
            if (authSection) authSection.style.display = 'none';
            authenticatedElements.forEach(el => el.style.display = 'block');
        } else {
            indicator?.classList.remove('authenticated');
            if (statusText) statusText.textContent = 'Not authenticated';
            if (authSection) authSection.style.display = 'block';
            authenticatedElements.forEach(el => el.style.display = 'none');
        }
    }

    onAuthChange(callback) {
        this.callbacks.onAuthChange.push(callback);
    }

    getUser() {
        return this.user;
    }

    isUserAuthenticated() {
        return this.isAuthenticated;
    }
}

// Create global auth service instance
window.authService = new AuthService();
