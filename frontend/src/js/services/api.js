/**
 * API Service
 * Handles all HTTP requests to the backend API
 */
class ApiService {
    constructor() {
        this.baseUrl = CONFIG.API_BASE_URL;
        this.token = localStorage.getItem(CONFIG.STORAGE_KEYS.API_TOKEN) || '';
    }

    setToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem(CONFIG.STORAGE_KEYS.API_TOKEN, token);
        } else {
            localStorage.removeItem(CONFIG.STORAGE_KEYS.API_TOKEN);
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
}

// Create global API service instance
window.apiService = new ApiService();
