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
    COOKIE_KEYS: {
        API_TOKEN: 'mp_auth_token'
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
    COOKIE_CONFIG: {
        SECURE: window.location.protocol === 'https:',
        SAME_SITE: 'Strict',
        PATH: '/',
        MAX_AGE_DAYS: 30
    },
    FEATURE_FLAGS: {
        COOKIE_AUTH: true,
        FALLBACK_TO_COOKIE: true
    },
    STATUS: {
        ACTIVE: 'active',
        INACTIVE: 'inactive',
        ERROR: 'error'
    }
};
