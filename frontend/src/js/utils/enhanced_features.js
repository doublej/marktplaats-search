/**
 * Enhanced features for MarktplaatsSearch Dashboard
 * Adds support for marktplaats library data fields and cross-search analysis
 */

// Global state for enhanced features
window.enhancedFeatures = {
    currentView: 'standard',
    crossSearchData: null,
    healthData: null
};

/**
 * Global API request function for enhanced features
 * Uses the main app's apiRequest method if available, otherwise implements its own
 */
async function apiRequest(endpoint, options = {}) {
    // Try to use the main app's apiRequest method if available
    if (window.app && typeof window.app.apiRequest === 'function') {
        return await window.app.apiRequest(endpoint, options);
    }

    // Fallback implementation
    const baseUrl = window.location.origin;
    const apiToken = localStorage.getItem('mp_api_token') || '';

    const url = `${baseUrl}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Authorization': `Bearer ${apiToken}`,
            'Content-Type': 'application/json'
        }
    };

    const response = await fetch(url, {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    });

    if (!response.ok) {
        if (response.status === 401) {
            throw new Error('Authentication expired');
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    if (response.status === 204 || response.headers.get('content-length') === '0') {
        return null;
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
        return response.json();
    }

    return null;
}

/**
 * Initialize enhanced features
 */
function initializeEnhancedFeatures() {
    addEnhancedUI();
    loadHealthCheck();
    setupPeriodicHealthCheck();
}

/**
 * Add enhanced UI elements to the dashboard
 */
function addEnhancedUI() {
    const headerActions = document.querySelector('.header-actions');
    if (!headerActions) return;

    // Add view toggle buttons
    const viewToggle = document.createElement('div');
    viewToggle.className = 'view-toggle';
    viewToggle.innerHTML = `
        <button id="standard-view-btn" class="btn btn-secondary active" onclick="switchView('standard')">
            Standard View
        </button>
        <button id="enhanced-view-btn" class="btn btn-secondary" onclick="switchView('enhanced')">
            Enhanced View
        </button>
        <button id="analysis-view-btn" class="btn btn-secondary" onclick="switchView('analysis')">
            Cross-Search Analysis
        </button>
    `;

    headerActions.insertBefore(viewToggle, headerActions.firstChild);

    // Add health status indicator
    const healthIndicator = document.createElement('div');
    healthIndicator.id = 'health-indicator';
    healthIndicator.className = 'health-indicator';
    healthIndicator.innerHTML = `
        <div class="health-status loading">
            <span class="health-dot"></span>
            <span class="health-text">Checking...</span>
        </div>
    `;

    headerActions.appendChild(healthIndicator);

    // Add enhanced CSS
    addEnhancedCSS();
}

/**
 * Add CSS for enhanced features
 */
function addEnhancedCSS() {
    const style = document.createElement('style');
    style.textContent = `
        .view-toggle {
            display: flex;
            gap: 0.25rem;
            background: var(--surface);
            border-radius: 0.5rem;
            padding: 0.25rem;
        }

        .view-toggle .btn {
            padding: 0.5rem 1rem;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            border-radius: 0.25rem;
            transition: all 0.2s ease;
            font-size: 0.875rem;
        }

        .view-toggle .btn.active {
            background: var(--primary-color);
            color: white;
        }

        .health-indicator {
            display: flex;
            align-items: center;
        }

        .health-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 0.75rem;
            border-radius: 0.5rem;
            font-size: 0.875rem;
            border: 1px solid var(--border);
        }

        .health-status.healthy {
            background: rgba(5, 150, 105, 0.1);
            border-color: var(--success-color);
            color: var(--success-color);
        }

        .health-status.degraded {
            background: rgba(217, 119, 6, 0.1);
            border-color: var(--warning-color);
            color: var(--warning-color);
        }

        .health-status.error {
            background: rgba(220, 38, 38, 0.1);
            border-color: var(--error-color);
            color: var(--error-color);
        }

        .health-status.loading {
            background: rgba(100, 116, 139, 0.1);
            border-color: var(--secondary-color);
            color: var(--secondary-color);
        }

        .health-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .enhanced-listing {
            border-left: 3px solid var(--primary-color);
        }

        .listing-metadata {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 0.75rem;
            margin-top: 0.75rem;
            padding: 0.75rem;
            background: var(--surface);
            border-radius: 0.5rem;
            font-size: 0.875rem;
        }

        .metadata-item {
            display: flex;
            flex-direction: column;
        }

        .metadata-label {
            color: var(--text-secondary);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.025em;
            margin-bottom: 0.25rem;
        }

        .metadata-value {
            color: var(--text-primary);
            font-weight: 500;
        }

        .verified-seller {
            color: var(--success-color);
        }

        .cross-search-analysis {
            padding: 2rem 0;
        }

        .analysis-controls {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            align-items: center;
        }

        .duplicate-item {
            background: var(--surface-elevated);
            border: 1px solid var(--border);
            border-radius: 0.75rem;
            padding: 1.5rem;
            margin-bottom: 1rem;
            transition: all 0.2s ease;
        }

        .duplicate-item:hover {
            border-color: var(--border-hover);
            box-shadow: var(--shadow);
        }

        .duplicate-header {
            display: flex;
            justify-content: between;
            align-items: start;
            margin-bottom: 1rem;
        }

        .duplicate-title {
            flex: 1;
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
        }

        .duplicate-stats {
            display: flex;
            gap: 1rem;
            flex-shrink: 0;
        }

        .stat-badge {
            background: var(--primary-color);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .search-queries {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.75rem;
        }

        .query-tag {
            background: var(--surface);
            color: var(--text-secondary);
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            border: 1px solid var(--border);
        }

        .hidden {
            display: none !important;
        }

        .loading-spinner {
            display: inline-block;
            width: 1rem;
            height: 1rem;
            border: 2px solid var(--border);
            border-top-color: var(--primary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}

/**
 * Switch between different views
 */
async function switchView(viewName) {
    // Update button states
    document.querySelectorAll('.view-toggle .btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`${viewName}-view-btn`).classList.add('active');

    // Hide all views
    const mainContent = document.querySelector('.main-content');
    if (!mainContent) return;

    window.enhancedFeatures.currentView = viewName;

    switch (viewName) {
        case 'standard':
            await showStandardView();
            break;
        case 'enhanced':
            await showEnhancedView();
            break;
        case 'analysis':
            await showAnalysisView();
            break;
    }
}

/**
 * Show standard view (existing functionality)
 */
async function showStandardView() {
    const mainContent = document.querySelector('.main-content');
    mainContent.innerHTML = `
        <div class="searches-section">
            <h2>Your Searches</h2>
            <div id="searches-container">
                <div class="loading-spinner"></div>
                <span style="margin-left: 0.5rem;">Loading searches...</span>
            </div>
        </div>
    `;

    // Load searches using main app function
    if (window.app && typeof window.app.loadSearches === 'function') {
        await window.app.loadSearches();
    }
}

/**
 * Show enhanced view with marktplaats library data
 */
async function showEnhancedView() {
    const mainContent = document.querySelector('.main-content');
    mainContent.innerHTML = `
        <div class="enhanced-section">
            <h2>Enhanced Search Results</h2>
            <p class="section-description">
                Enhanced view showing rich data from the Marktplaats API including seller information,
                categories, location details, and verified seller status.
            </p>
            <div id="enhanced-searches-container">
                <div class="loading-spinner"></div>
                <span style="margin-left: 0.5rem;">Loading enhanced data...</span>
            </div>
        </div>
    `;

    await loadEnhancedSearches();
}

/**
 * Show cross-search analysis view
 */
async function showAnalysisView() {
    const mainContent = document.querySelector('.main-content');
    mainContent.innerHTML = `
        <div class="cross-search-analysis">
            <h2>Cross-Search Analysis</h2>
            <p class="section-description">
                Find listings that appear across multiple searches. This helps identify popular items
                and optimize your search strategies.
            </p>
            <div class="analysis-controls">
                <label>
                    Minimum searches:
                    <select id="min-searches-filter" onchange="loadCrossSearchAnalysis()">
                        <option value="2">2</option>
                        <option value="3" selected>3</option>
                        <option value="4">4</option>
                        <option value="5">5+</option>
                    </select>
                </label>
                <button class="btn btn-primary" onclick="loadCrossSearchAnalysis()">
                    Refresh Analysis
                </button>
            </div>
            <div id="cross-search-results">
                <div class="loading-spinner"></div>
                <span style="margin-left: 0.5rem;">Analyzing cross-search duplicates...</span>
            </div>
        </div>
    `;

    await loadCrossSearchAnalysis();
}

/**
 * Load enhanced search data
 */
async function loadEnhancedSearches() {
    try {
        const searches = await apiRequest('/api/searches');
        const container = document.getElementById('enhanced-searches-container');

        if (!searches || searches.length === 0) {
            container.innerHTML = '<p class="no-data">No searches found. Create your first search to get started!</p>';
            return;
        }

        let html = '';
        for (const search of searches) {
            html += await renderEnhancedSearch(search);
        }

        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading enhanced searches:', error);
        document.getElementById('enhanced-searches-container').innerHTML =
            '<p class="error">Error loading enhanced searches. Please try again.</p>';
    }
}

/**
 * Render enhanced search with rich listing data
 */
async function renderEnhancedSearch(search) {
    try {
        // Validate search ID before making API call
        if (!search || !search.id) {
            console.warn('Invalid search object or missing ID:', search);
            return `<div class="search-card error">Invalid search data</div>`;
        }

        const listings = await apiRequest(`/api/searches/${search.id}/results?limit=10`);

        let listingsHtml = '';
        if (listings && listings.length > 0) {
            listingsHtml = listings.map(listing => renderEnhancedListing(listing)).join('');
        } else {
            listingsHtml = '<p class="no-listings">No listings found yet. The search will run automatically.</p>';
        }

        return `
            <div class="search-card enhanced-listing">
                <div class="search-header">
                    <h3>${escapeHtml(search.query)}</h3>
                    <div class="search-status ${search.status.toLowerCase()}">
                        ${search.status}
                    </div>
                </div>
                <div class="search-details">
                    <div class="search-metadata">
                        ${search.zip_code ? `<span>📍 ${search.zip_code} (${search.distance || 25}km)</span>` : ''}
                        ${search.price_from || search.price_to ?
                            `<span>💰 €${search.price_from || 0} - €${search.price_to || '∞'}</span>` : ''}
                        <span>⏱️ Every ${formatInterval(search.interval)}</span>
                        ${search.last_run_at ? `<span>🕐 Last run: ${formatDate(search.last_run_at)}</span>` : ''}
                    </div>
                </div>
                <div class="listings-section">
                    <h4>Recent Listings</h4>
                    <div class="listings-grid">
                        ${listingsHtml}
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error rendering enhanced search:', error);
        return `<div class="search-card error">Error loading search data</div>`;
    }
}

/**
 * Render enhanced listing with marktplaats library data
 */
function renderEnhancedListing(listing) {
    const hasEnhancedData = listing.marktplaats_id || listing.seller_name || listing.category_id;

    return `
        <div class="listing-item ${hasEnhancedData ? 'enhanced-listing' : ''}">
            ${listing.image_large || listing.image_url ?
                `<img src="${listing.image_large || listing.image_url}" alt="${escapeHtml(listing.title)}" class="listing-image">` : ''}
            <div class="listing-content">
                <h5 class="listing-title">
                    <a href="${listing.url}" target="_blank">${escapeHtml(listing.title)}</a>
                    ${listing.is_new ? '<span class="new-badge">NEW</span>' : ''}
                </h5>
                <p class="listing-price">
                    ${listing.price ? `€${listing.price}` : (listing.price_numeric ? `€${(listing.price_numeric / 100).toFixed(2)}` : 'Price on request')}
                    ${listing.price_type && listing.price_type !== 'FIXED' ? ` (${listing.price_type})` : ''}
                </p>
                ${listing.description || listing.description_snippet ?
                    `<p class="listing-description">${escapeHtml((listing.description || listing.description_snippet).substring(0, 100))}...</p>` : ''}

                ${hasEnhancedData ? renderListingMetadata(listing) : ''}
            </div>
        </div>
    `;
}

/**
 * Render listing metadata from marktplaats library
 */
function renderListingMetadata(listing) {
    const metadata = [];

    if (listing.seller_name) {
        metadata.push({
            label: 'Seller',
            value: `${listing.seller_name} ${listing.seller_is_verified ? '✅' : ''}`,
            className: listing.seller_is_verified ? 'verified-seller' : ''
        });
    }

    if (listing.location_city) {
        metadata.push({
            label: 'Location',
            value: `${listing.location_city}${listing.location_distance ? ` (${Math.round(listing.location_distance/1000)}km)` : ''}`
        });
    }

    if (listing.category_id) {
        metadata.push({
            label: 'Category',
            value: `ID: ${listing.category_id}`
        });
    }

    if (listing.date_posted) {
        metadata.push({
            label: 'Posted',
            value: formatDate(listing.date_posted)
        });
    }

    if (metadata.length === 0) return '';

    return `
        <div class="listing-metadata">
            ${metadata.map(item => `
                <div class="metadata-item">
                    <div class="metadata-label">${item.label}</div>
                    <div class="metadata-value ${item.className || ''}">${item.value}</div>
                </div>
            `).join('')}
        </div>
    `;
}

/**
 * Load cross-search analysis
 */
async function loadCrossSearchAnalysis() {
    const container = document.getElementById('cross-search-results');
    const minSearches = document.getElementById('min-searches-filter')?.value || 3;

    container.innerHTML = `
        <div class="loading-spinner"></div>
        <span style="margin-left: 0.5rem;">Analyzing cross-search duplicates...</span>
    `;

    try {
        const analysis = await apiRequest(`/api/cross-search-analysis?min_searches=${minSearches}&limit=50`);

        if (!analysis || analysis.length === 0) {
            container.innerHTML = `
                <div class="no-data">
                    <h4>No Cross-Search Duplicates Found</h4>
                    <p>No listings appear in ${minSearches}+ searches. Try lowering the minimum search count or create more searches with overlapping results.</p>
                </div>
            `;
            return;
        }

        const html = analysis.map(renderDuplicateAnalysis).join('');
        container.innerHTML = html;

        window.enhancedFeatures.crossSearchData = analysis;

    } catch (error) {
        console.error('Error loading cross-search analysis:', error);
        container.innerHTML = '<p class="error">Error loading cross-search analysis. Please try again.</p>';
    }
}

/**
 * Render cross-search duplicate analysis
 */
function renderDuplicateAnalysis(duplicate) {
    return `
        <div class="duplicate-item">
            <div class="duplicate-header">
                <div>
                    <h4 class="duplicate-title">
                        <a href="${duplicate.url}" target="_blank">${escapeHtml(duplicate.title || 'Untitled')}</a>
                    </h4>
                    ${duplicate.marktplaats_id ? `<p class="listing-id">ID: ${duplicate.marktplaats_id}</p>` : ''}
                </div>
                <div class="duplicate-stats">
                    <span class="stat-badge">${duplicate.search_count} searches</span>
                    <span class="stat-badge">${duplicate.total_occurrences} occurrences</span>
                </div>
            </div>

            <div class="listing-metadata">
                ${duplicate.price ? `
                    <div class="metadata-item">
                        <div class="metadata-label">Price</div>
                        <div class="metadata-value">€${duplicate.price}${duplicate.price_type && duplicate.price_type !== 'FIXED' ? ` (${duplicate.price_type})` : ''}</div>
                    </div>
                ` : ''}
                ${duplicate.seller_name ? `
                    <div class="metadata-item">
                        <div class="metadata-label">Seller</div>
                        <div class="metadata-value ${duplicate.seller_is_verified ? 'verified-seller' : ''}">${duplicate.seller_name} ${duplicate.seller_is_verified ? '✅' : ''}</div>
                    </div>
                ` : ''}
                ${duplicate.location_city ? `
                    <div class="metadata-item">
                        <div class="metadata-label">Location</div>
                        <div class="metadata-value">${duplicate.location_city}</div>
                    </div>
                ` : ''}
                ${duplicate.category_id ? `
                    <div class="metadata-item">
                        <div class="metadata-label">Category</div>
                        <div class="metadata-value">ID: ${duplicate.category_id}</div>
                    </div>
                ` : ''}
                <div class="metadata-item">
                    <div class="metadata-label">Time Range</div>
                    <div class="metadata-value">${formatDate(duplicate.first_seen)} - ${formatDate(duplicate.last_seen)}</div>
                </div>
            </div>

            <div class="search-queries">
                <strong>Found in searches:</strong>
                ${duplicate.search_queries.map(query =>
                    `<span class="query-tag">${escapeHtml(query)}</span>`
                ).join('')}
            </div>
        </div>
    `;
}

/**
 * Load health check data
 */
async function loadHealthCheck() {
    try {
        const health = await apiRequest('/health');
        updateHealthIndicator(health);
        window.enhancedFeatures.healthData = health;
    } catch (error) {
        console.error('Health check failed:', error);
        updateHealthIndicator({ status: 'error', error: error.message });
    }
}

/**
 * Update health indicator UI
 */
function updateHealthIndicator(health) {
    const indicator = document.getElementById('health-indicator');
    if (!indicator) return;

    const statusClass = health.status || 'error';
    const statusText = getHealthStatusText(health);

    indicator.innerHTML = `
        <div class="health-status ${statusClass}" title="${getHealthTooltip(health)}">
            <span class="health-dot"></span>
            <span class="health-text">${statusText}</span>
        </div>
    `;
}

/**
 * Get health status text
 */
function getHealthStatusText(health) {
    if (!health.status) return 'Error';

    switch (health.status) {
        case 'healthy':
            return 'System Healthy';
        case 'degraded':
            return 'System Degraded';
        case 'error':
            return 'System Error';
        default:
            return health.status;
    }
}

/**
 * Get health tooltip
 */
function getHealthTooltip(health) {
    if (!health) return 'Health check failed';

    const details = [];
    if (health.database_status) details.push(`DB: ${health.database_status}`);
    if (health.scheduler_status) details.push(`Scheduler: ${health.scheduler_status}`);
    if (health.marktplaats_client_status) details.push(`Client: ${health.marktplaats_client_status}`);
    if (health.total_searches !== undefined) details.push(`${health.total_searches} searches`);
    if (health.total_listings !== undefined) details.push(`${health.total_listings} listings`);

    return details.join(' | ');
}

/**
 * Setup periodic health checks
 */
function setupPeriodicHealthCheck() {
    // Check health every 30 seconds
    setInterval(loadHealthCheck, 30000);
}

/**
 * Format interval for display
 */
function formatInterval(seconds) {
    if (!seconds || seconds < 60) return `${seconds || 0}s`;
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.round(minutes / 60);
    return `${hours}h`;
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString();
    } catch {
        return 'Invalid date';
    }
}

/**
 * Utility function to escape HTML
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Initialize enhanced features when DOM is loaded
 */
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeEnhancedFeatures);
} else {
    initializeEnhancedFeatures();
}
