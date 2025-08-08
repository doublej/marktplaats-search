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
        const localToken = localStorage.getItem(CONFIG.STORAGE_KEYS.API_TOKEN);
        const cookieToken = CONFIG.FEATURE_FLAGS.FALLBACK_TO_COOKIE ?
            apiService.getCookie(CONFIG.COOKIE_KEYS.API_TOKEN) : null;

        const token = localToken || cookieToken;
        if (token) {
            // Ensure both storage methods have the token
            if (localToken && !cookieToken && CONFIG.FEATURE_FLAGS.COOKIE_AUTH) {
                apiService.setCookie(CONFIG.COOKIE_KEYS.API_TOKEN, localToken);
            } else if (!localToken && cookieToken) {
                localStorage.setItem(CONFIG.STORAGE_KEYS.API_TOKEN, cookieToken);
            }
            this.validateStoredToken();
        }
    }

    async validateStoredToken() {
        try {
            const user = await apiService.validateToken();
            this.setAuthenticatedState(true, user);
        } catch (error) {
            console.warn('Stored token is invalid:', error.message);
            // Clear both localStorage and cookies
            apiService.setToken('');
            this.setAuthenticatedState(false);
        }
    }

    async authenticate(token) {
        try {
            apiService.setToken(token); // This now handles both localStorage and cookie
            const user = await apiService.validateToken();

            // Attempt to set server-side cookie for persistence
            if (CONFIG.FEATURE_FLAGS.COOKIE_AUTH) {
                try {
                    await apiService.post('/api/auth/set-cookie');
                } catch (cookieError) {
                    console.warn('Failed to set server cookie:', cookieError);
                    // Continue anyway - client-side cookie should still work
                }
            }

            this.setAuthenticatedState(true, user);
            return true;
        } catch (error) {
            apiService.setToken(''); // This now clears both localStorage and cookie
            this.setAuthenticatedState(false);
            throw error;
        }
    }

    async logout() {
        await apiService.logout(); // This handles server-side logout and clears tokens
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

    syncTokenStorage() {
        const localToken = localStorage.getItem(CONFIG.STORAGE_KEYS.API_TOKEN);
        const cookieToken = apiService.getCookie(CONFIG.COOKIE_KEYS.API_TOKEN);

        if (localToken && !cookieToken && CONFIG.FEATURE_FLAGS.COOKIE_AUTH) {
            apiService.setCookie(CONFIG.COOKIE_KEYS.API_TOKEN, localToken);
        } else if (!localToken && cookieToken && CONFIG.FEATURE_FLAGS.FALLBACK_TO_COOKIE) {
            localStorage.setItem(CONFIG.STORAGE_KEYS.API_TOKEN, cookieToken);
            apiService.setToken(cookieToken); // Update apiService instance
        }
    }
}

// Create global auth service instance
window.authService = new AuthService();
