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
        let cookieToken = null;
        
        // Safely get cookie token if apiService is available
        if (CONFIG.FEATURE_FLAGS.FALLBACK_TO_COOKIE && window.apiService) {
            cookieToken = window.apiService.getCookie(CONFIG.COOKIE_KEYS.API_TOKEN);
        }

        const token = localToken || cookieToken;
        if (token) {
            // Ensure both storage methods have the token
            if (localToken && !cookieToken && CONFIG.FEATURE_FLAGS.COOKIE_AUTH && window.apiService) {
                window.apiService.setCookie(CONFIG.COOKIE_KEYS.API_TOKEN, localToken);
            } else if (!localToken && cookieToken) {
                localStorage.setItem(CONFIG.STORAGE_KEYS.API_TOKEN, cookieToken);
            }
            
            // Validate token when apiService becomes available
            if (window.apiService) {
                this.validateStoredToken();
            } else {
                // Wait for apiService to be available
                this.waitForApiServiceAndValidate();
            }
        }
    }
    
    waitForApiServiceAndValidate() {
        // Poll for apiService availability
        const checkApiService = () => {
            if (window.apiService) {
                this.validateStoredToken();
            } else {
                setTimeout(checkApiService, 50); // Check every 50ms
            }
        };
        
        // Start checking, but with a timeout
        const startTime = Date.now();
        const timeoutMs = 5000; // 5 second timeout
        
        const checkWithTimeout = () => {
            if (window.apiService) {
                this.validateStoredToken();
            } else if (Date.now() - startTime < timeoutMs) {
                setTimeout(checkWithTimeout, 50);
            } else {
                console.warn('apiService not available after timeout, skipping token validation');
                this.setAuthenticatedState(false);
            }
        };
        
        checkWithTimeout();
    }

    async validateStoredToken() {
        // Check if apiService is available
        if (!window.apiService) {
            console.warn('apiService not available, skipping token validation');
            this.setAuthenticatedState(false);
            return;
        }
        
        try {
            const user = await window.apiService.validateToken();
            this.setAuthenticatedState(true, user);
        } catch (error) {
            console.warn('Stored token is invalid:', error.message);
            // Clear both localStorage and cookies
            if (window.apiService) {
                window.apiService.setToken('');
            }
            this.setAuthenticatedState(false);
        }
    }

    async authenticate(token) {
        try {
            window.apiService.setToken(token); // This now handles both localStorage and cookie
            const user = await window.apiService.validateToken();

            // Attempt to set server-side cookie for persistence
            if (CONFIG.FEATURE_FLAGS.COOKIE_AUTH) {
                try {
                    await window.apiService.post('/api/auth/set-cookie');
                } catch (cookieError) {
                    console.warn('Failed to set server cookie:', cookieError);
                    // Continue anyway - client-side cookie should still work
                }
            }

            this.setAuthenticatedState(true, user);
            return true;
        } catch (error) {
            window.apiService.setToken(''); // This now clears both localStorage and cookie
            this.setAuthenticatedState(false);
            throw error;
        }
    }

    async logout() {
        await window.apiService.logout(); // This handles server-side logout and clears tokens
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
        const cookieToken = window.apiService ? window.apiService.getCookie(CONFIG.COOKIE_KEYS.API_TOKEN) : null;

        if (localToken && !cookieToken && CONFIG.FEATURE_FLAGS.COOKIE_AUTH && window.apiService) {
            window.apiService.setCookie(CONFIG.COOKIE_KEYS.API_TOKEN, localToken);
        } else if (!localToken && cookieToken && CONFIG.FEATURE_FLAGS.FALLBACK_TO_COOKIE && window.apiService) {
            localStorage.setItem(CONFIG.STORAGE_KEYS.API_TOKEN, cookieToken);
            window.apiService.setToken(cookieToken); // Update apiService instance
        }
    }
}

// Create global auth service instance
window.authService = new AuthService();
