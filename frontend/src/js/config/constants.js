/**
 * Application Constants
 */
export const CONFIG = {
    API_BASE_URL: window.location.origin,
    STORAGE_KEYS: {
        API_TOKEN: 'mp_api_token',
        THEME: 'mp_theme',
        USER_PREFS: 'mp_user_preferences'
    },
    DEFAULTS: {
        RESULTS_LIMIT: 20,
        SEARCH_INTERVAL: 3600, // 1 hour
        HEALTH_CHECK_INTERVAL: 30000, // 30 seconds
        DEBOUNCE_DELAY: 300
    },
    THEMES: {
        LIGHT: 'light',
        DARK: 'dark'
    },
    STATUS: {
        ACTIVE: 'active',
        INACTIVE: 'inactive',
        ERROR: 'error'
    }
};
