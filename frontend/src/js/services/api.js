/**
 * API Service
 * Handles all HTTP requests to the backend API
 */
class ApiService {
    constructor() {
        this.baseUrl = CONFIG.API_BASE_URL;
        // Initialize with localStorage first, cookie fallback will be handled later
        this.token = localStorage.getItem(CONFIG.STORAGE_KEYS.API_TOKEN) || '';
        
        // If no localStorage token and cookie fallback is enabled, check cookies
        if (!this.token && CONFIG.FEATURE_FLAGS.FALLBACK_TO_COOKIE) {
            const cookieToken = this.getCookie(CONFIG.COOKIE_KEYS.API_TOKEN);
            if (cookieToken) {
                this.token = cookieToken;
                // Sync back to localStorage
                localStorage.setItem(CONFIG.STORAGE_KEYS.API_TOKEN, cookieToken);
            }
        }
    }

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    setCookie(name, value, days = CONFIG.COOKIE_CONFIG.MAX_AGE_DAYS) {
        let expires = "";
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = `; expires=${  date.toUTCString()}`;
        }
        const secure = CONFIG.COOKIE_CONFIG.SECURE ? "; secure" : "";
        const sameSite = `; samesite=${CONFIG.COOKIE_CONFIG.SAME_SITE}`;
        const path = `; path=${CONFIG.COOKIE_CONFIG.PATH}`;
        document.cookie = `${name}=${value || ""}${expires}${path}${secure}${sameSite}`;
    }

    deleteCookie(name) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${CONFIG.COOKIE_CONFIG.PATH};`;
    }

    setToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem(CONFIG.STORAGE_KEYS.API_TOKEN, token);
            if (CONFIG.FEATURE_FLAGS.COOKIE_AUTH) {
                this.setCookie(CONFIG.COOKIE_KEYS.API_TOKEN, token);
            }
        } else {
            localStorage.removeItem(CONFIG.STORAGE_KEYS.API_TOKEN);
            if (CONFIG.FEATURE_FLAGS.COOKIE_AUTH) {
                this.deleteCookie(CONFIG.COOKIE_KEYS.API_TOKEN);
            }
        }
    }

    getHeaders() {
        return {
            'Content-Type': 'application/json',
            ...(this.token ? { 'Authorization': `Bearer ${this.token}` } : {})
        };
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: this.getHeaders(),
            ...options
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                if (response.status === 401) {
                    this.setToken('');
                    throw new Error('Authentication expired');
                }

                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            // Handle empty responses
            if (response.status === 204 || response.headers.get('content-length') === '0') {
                return null;
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            }

            return response.text();
        } catch (error) {
            console.error('API Request failed:', { endpoint, error });
            throw error;
        }
    }

    // Convenience methods
    async get(endpoint) {
        return this.request(endpoint);
    }

    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }

    // Health check
    async healthCheck() {
        return this.get('/health');
    }

    // Authentication
    async validateToken() {
        return this.get('/api/auth/me');
    }

    async registerUser(userData) {
        return this.post('/api/auth/register', userData);
    }

    // Searches
    async getSearches() {
        return this.get('/api/searches');
    }

    async getSearch(searchId) {
        return this.get(`/api/searches/${searchId}`);
    }

    async createSearch(searchData) {
        return this.post('/api/searches', searchData);
    }

    async updateSearch(searchId, updateData) {
        return this.put(`/api/searches/${searchId}`, updateData);
    }

    async deleteSearch(searchId) {
        return this.delete(`/api/searches/${searchId}`);
    }

    async getSearchResults(searchId, options = {}) {
        const params = new URLSearchParams(options);
        return this.get(`/api/searches/${searchId}/results?${params}`);
    }

    // Listings
    async getListingDetails(listingId, markAsRead = true) {
        return this.get(`/api/results/${listingId}?mark_as_read=${markAsRead}`);
    }

    // Admin operations
    async refreshAllSearches() {
        return this.post('/api/admin/refresh-searches');
    }

    async cleanupOldListings(options = {}) {
        const params = new URLSearchParams(options);
        return this.post(`/api/admin/cleanup-listings?${params}`);
    }

    async logout() {
        try {
            await this.post('/api/auth/logout');
        } catch (error) {
            console.warn('Logout request failed:', error);
        } finally {
            this.setToken('');
        }
    }
}

// Create global API service instance
window.apiService = new ApiService();
