/**
 * Theme Service
 * Handles light/dark theme switching
 */
class ThemeService {
    constructor() {
        this.currentTheme = localStorage.getItem(CONFIG.STORAGE_KEYS.THEME) || CONFIG.THEMES.LIGHT;
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.setupThemeToggle();
    }

    applyTheme(theme) {
        document.body.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        localStorage.setItem(CONFIG.STORAGE_KEYS.THEME, theme);
        this.updateThemeIcon();
    }

    toggleTheme() {
        const newTheme = this.currentTheme === CONFIG.THEMES.LIGHT
            ? CONFIG.THEMES.DARK
            : CONFIG.THEMES.LIGHT;
        this.applyTheme(newTheme);
    }

    updateThemeIcon() {
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) {
            themeIcon.textContent = this.currentTheme === CONFIG.THEMES.LIGHT ? '🌙' : '☀️';
        }
    }

    setupThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    getCurrentTheme() {
        return this.currentTheme;
    }
}

// Create global theme service instance
window.themeService = new ThemeService();
