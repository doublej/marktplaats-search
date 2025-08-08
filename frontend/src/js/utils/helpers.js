/**
 * Utility Helper Functions
 */

// DOM utilities
function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}

// Escape HTML to prevent XSS - unified with backend sanitization
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Clean text similar to backend text_utils
function cleanText(text) {
    if (!text) return null;

    // Remove extra whitespace and normalize
    const cleaned = text.replace(/\s+/g, ' ').trim();

    return cleaned || null;
}

// Truncate text with suffix
function truncateText(text, maxLength, suffix = '...') {
    if (!text) return text;

    if (text.length <= maxLength) {
        return text;
    }

    const truncateAt = maxLength - suffix.length;
    if (truncateAt <= 0) {
        return suffix.substring(0, maxLength);
    }

    return text.substring(0, truncateAt) + suffix;
}

// Format date for display
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString();
    } catch {
        return 'Invalid date';
    }
}

// Format date and time
function formatDateTime(dateString) {
    if (!dateString) return 'Unknown';
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch {
        return 'Invalid date';
    }
}

// Format relative time (e.g., "2h ago", "3d ago")
function formatTimeAgo(dateString) {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);

        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)  }m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)  }h ago`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)  }d ago`;
        return date.toLocaleDateString();
    } catch {
        return '';
    }
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Show/hide loading state
function setLoading(element, loading = true) {
    if (!element) return;

    if (loading) {
        element.style.opacity = '0.6';
        element.style.pointerEvents = 'none';
    } else {
        element.style.opacity = '1';
        element.style.pointerEvents = 'auto';
    }
}

// Show alert message
function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = $('#alert-container') || createAlertContainer();

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;

    alertContainer.appendChild(alert);

    // Auto remove after duration
    setTimeout(() => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, duration);
}

function createAlertContainer() {
    const container = document.createElement('div');
    container.id = 'alert-container';
    container.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        max-width: 400px;
    `;
    document.body.appendChild(container);
    return container;
}
