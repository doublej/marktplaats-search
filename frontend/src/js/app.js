/**
 * Main Application Class
 * Coordinates all components and manages application state
 */
class MarktplaatsSearchApp {
    constructor() {
        this.searches = [];
        this.currentSearchId = null;
        this.selectedSearchId = null;
        this.currentResults = [];
        this.currentResultsPage = 0;
        this.resultsLimit = CONFIG.DEFAULTS.RESULTS_LIMIT;

        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.startHealthChecks();
        this.startProgressUpdates();

        // Initialize services
        await this.initializeServices();

        console.log('MarktplaatsSearch App initialized');
    }

    async initializeServices() {
        // Services are already initialized globally
        // Set up authentication change listener
        authService.onAuthChange((isAuthenticated) => {
            if (isAuthenticated) {
                this.loadSearches();
            } else {
                this.searches = [];
                this.renderSearches();
            }
        });

        // Initialize SearchForm component
        this.searchForm = new SearchForm(this);
    }

    setupEventListeners() {
        // Authentication form
        const authForm = $('#auth-form');
        if (authForm) {
            authForm.addEventListener('submit', this.handleAuth.bind(this));
        }

        // Create search button
        const createBtn = $('#create-search-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.openSearchModal());
        }

        // Refresh searches button
        const refreshBtn = $('#refresh-searches-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', this.refreshAllSearches.bind(this));
        }

        // Modal close handlers
        const modalClose = $('#search-modal-close');
        if (modalClose) {
            modalClose.addEventListener('click', () => this.closeSearchModal());
        }

        // Tab switching
        this.setupTabSwitching();
    }

    async handleAuth(e) {
        e.preventDefault();

        const tokenInput = $('#api-token');
        const errorDiv = $('#auth-error');
        const submitBtn = $('#auth-submit');
        const loadingSpinner = $('#auth-loading');

        if (!tokenInput) return;

        const token = tokenInput.value.trim();

        try {
            setLoading(submitBtn, true);
            if (loadingSpinner) loadingSpinner.style.display = 'inline-block';
            if (errorDiv) errorDiv.textContent = '';

            await authService.authenticate(token);
            tokenInput.value = '';
            showAlert('Authentication successful!', 'success');

        } catch (error) {
            console.error('Authentication failed:', error);
            if (errorDiv) errorDiv.textContent = error.message || 'Authentication failed';
            showAlert('Authentication failed: ' + error.message, 'error');
        } finally {
            setLoading(submitBtn, false);
            if (loadingSpinner) loadingSpinner.style.display = 'none';
        }
    }

    async loadSearches() {
        const loading = $('#searches-loading');
        const container = $('#searches-container');

        if (!container) return;

        try {
            if (loading) loading.style.display = 'flex';

            this.searches = await apiService.getSearches() || [];
            this.renderSearches();

        } catch (error) {
            console.error('Failed to load searches:', error);
            if (container) {
                container.innerHTML = `
                    <div class="alert alert-error">
                        Failed to load searches: ${error.message || 'Unknown error'}
                    </div>
                `;
            }
        } finally {
            if (loading) loading.style.display = 'none';
        }
    }

    renderSearches() {
        const container = $('#searches-container');
        if (!container) return;

        if (this.searches.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-title">No searches yet</div>
                    <p>Create your first search to get started!</p>
                </div>
            `;
            return;
        }

        const searchesHtml = this.searches.map(search =>
            this.renderSearchListItem(search)
        ).join('');

        container.innerHTML = searchesHtml;
    }

    renderSearchListItem(search) {
        const statusClass = search.status.toLowerCase();
        const searchId = search.id;
        const isActive = this.selectedSearchId === searchId;

        // Calculate progress for active searches
        let progressData = null;
        if (search.status === 'active' && search.last_run_at && search.interval) {
            const lastRun = new Date(search.last_run_at);
            const nextRun = new Date(lastRun.getTime() + (search.interval * 1000));
            const now = new Date();

            const totalDuration = search.interval * 1000; // in milliseconds
            const elapsed = now.getTime() - lastRun.getTime();
            const progress = Math.min(Math.max(elapsed / totalDuration * 100, 0), 100);

            progressData = {
                progress: progress,
                lastRun: lastRun,
                nextRun: nextRun,
                isOverdue: now > nextRun
            };
        }

        return `
            <div class="search-item ${isActive ? 'active' : ''}" onclick="app.selectSearch('${searchId}')">
                <div class="search-item-title">${escapeHtml(search.query)}</div>
                <div class="search-meta">
                    <span style="font-size: 0.65rem;">${search.zip_code || 'All locations'}</span>
                    <span class="status-badge status-${statusClass}">${search.status}</span>
                </div>
                ${progressData ? `
                    <div style="margin-top: 0.4rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.6rem; color: var(--text-secondary, #6b7280); margin-bottom: 0.2rem;">
                            <span>Last: ${this.formatTime(progressData.lastRun)}</span>
                            <span ${progressData.isOverdue ? 'style="color: var(--error-color, #ef4444); font-weight: 500;"' : ''}>
                                Next: ${this.formatTime(progressData.nextRun)}
                            </span>
                        </div>
                        <div style="width: 100%; height: 3px; background: var(--surface, #f1f5f9); border-radius: 1.5px; overflow: hidden;">
                            <div style="
                                height: 100%;
                                width: ${progressData.progress}%;
                                background: ${progressData.isOverdue ? 'var(--error-color, #ef4444)' : 'var(--primary-color, #3b82f6)'};
                                transition: width 0.3s ease;
                                border-radius: 1.5px;
                            "></div>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }

    formatTime(date) {
        const now = new Date();
        const diff = Math.abs(now - date);
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);

        if (minutes < 60) {
            return `${minutes}m`;
        } else if (hours < 24) {
            return `${hours}h ${minutes % 60}m`;
        } else {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
    }

    selectSearch(searchId) {
        this.selectedSearchId = searchId;
        this.currentSearchId = searchId;

        // Update active states
        $$('.search-item').forEach(item => {
            item.classList.remove('active');
        });
        $(`[onclick="app.selectSearch('${searchId}')"]`)?.classList.add('active');

        // Find search
        const search = this.searches.find(s => s.id === searchId);
        if (search) {
            // Load results and details
            this.loadResultsForSearch(searchId);
            this.renderSearchDetails(search);
        }
    }

    async loadResultsForSearch(searchId) {
        if (!searchId) {
            console.warn('loadResultsForSearch called with undefined searchId');
            const container = $('#results-content');
            if (container) {
                container.innerHTML = '<div class="empty-state">Please select a search to view results</div>';
            }
            return;
        }

        const container = $('#results-content');
        if (container) {
            container.innerHTML = '<div class="loading">Loading results...</div>';
        }

        try {
            const results = await apiService.getSearchResults(searchId);

            if (results.length === 0) {
                if (container) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-title">No results yet</div>
                            <p>This search will run automatically and results will appear here.</p>
                        </div>
                    `;
                }
                return;
            }

            this.renderResults(results);

        } catch (error) {
            console.error('Failed to load results:', error);
            if (container) {
                container.innerHTML = `
                    <div class="alert alert-error">
                        Failed to load results: ${error.message || 'Unknown error'}
                    </div>
                `;
            }
        }
    }

    renderResults(results) {
        const container = $('#results-content');
        if (!container) return;

        // Use requestAnimationFrame for smooth rendering
        requestAnimationFrame(() => {
            container.innerHTML = results.map(result => this.renderResultCard(result)).join('');
        });
    }

    renderResultCard(result) {
        const isNew = result.is_new;

        // Clean and extract data only once
        const title = escapeHtml(result.title || 'No title');
        const price = escapeHtml(result.price || 'Contact for price');
        const description = result.description ? escapeHtml(result.description) : '';
        const location = result.location ? escapeHtml(result.location) : '';
        const datePosted = result.date_posted;
        const dateDiscovered = result.discovered_at;

        return `
            <article class="result-card ${isNew ? 'new-item' : ''}" style="
                border: 1px solid ${isNew ? 'var(--success-color, #10b981)' : 'var(--border, #e5e7eb)'};
                border-radius: 6px;
                padding: 0.75rem;
                margin-bottom: 0.75rem;
                background: ${isNew ? 'rgba(16, 185, 129, 0.05)' : 'var(--surface-elevated, #ffffff)'};
                transition: all 0.2s;
            " onmouseover="this.style.boxShadow='0 2px 8px rgba(0,0,0,0.1)'" onmouseout="this.style.boxShadow=''">                <div style="display: grid; grid-template-columns: ${result.image_url ? 'auto 80px' : '1fr'}; gap: 0.75rem;">
                    <!-- Main content -->
                    <div style="min-width: 0;">
                        <!-- Title and badges -->
                        <header style="display: flex; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <h3 style="
                                margin: 0;
                                font-size: 0.95rem;
                                font-weight: 500;
                                line-height: 1.3;
                                flex: 1;
                                overflow: hidden;
                                text-overflow: ellipsis;
                                display: -webkit-box;
                                -webkit-line-clamp: 2;
                                -webkit-box-orient: vertical;
                            ">
                                ${title}
                            </h3>
                            ${isNew ? `
                                <span style="
                                    padding: 0.15rem 0.4rem;
                                    border-radius: 3px;
                                    background: var(--success-color, #10b981);
                                    color: white;
                                    font-size: 0.65rem;
                                    font-weight: 600;
                                    flex-shrink: 0;
                                ">NEW</span>
                            ` : ''}
                        </header>

                        <!-- Price and metadata -->
                        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; flex-wrap: wrap;">
                            <strong style="color: var(--primary-color, #3b82f6); font-size: 1.1rem;">
                                ${price}
                            </strong>
                            ${location ? `
                                <span style="color: var(--text-secondary, #6b7280); font-size: 0.75rem;">
                                    📍 ${location}
                                </span>
                            ` : ''}
                        </div>

                        <!-- Date information -->
                        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; flex-wrap: wrap; font-size: 0.7rem; color: var(--text-secondary, #6b7280);">
                            ${datePosted ? `
                                <time style="display: flex; align-items: center; gap: 0.25rem;">
                                    <span style="font-weight: 500;">Posted:</span>
                                    ${formatTimeAgo(datePosted)}
                                </time>
                            ` : ''}
                            ${dateDiscovered ? `
                                <time style="display: flex; align-items: center; gap: 0.25rem;">
                                    <span style="font-weight: 500;">Found:</span>
                                    ${formatTimeAgo(dateDiscovered)}
                                </time>
                            ` : ''}
                        </div>

                        <!-- Description -->
                        ${description ? `
                            <p style="
                                margin: 0 0 0.5rem 0;
                                font-size: 0.8rem;
                                color: var(--text-secondary, #6b7280);
                                line-height: 1.4;
                                overflow: hidden;
                                text-overflow: ellipsis;
                                display: -webkit-box;
                                -webkit-line-clamp: 2;
                                -webkit-box-orient: vertical;
                            ">
                                ${description}
                            </p>
                        ` : ''}

                        <!-- Footer with metadata and actions -->
                        <footer style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="display: flex; gap: 0.75rem; font-size: 0.7rem; color: var(--text-secondary, #6b7280);">
                                ${result.seller ? `<span>Seller: ${escapeHtml(result.seller)}</span>` : ''}
                                ${result.views ? `<span>Views: ${result.views}</span>` : ''}
                                ${result.condition ? `<span>Condition: ${escapeHtml(result.condition)}</span>` : ''}
                            </div>
                            <div style="display: flex; gap: 0.5rem;">
                                <a href="${result.url}"
                                   target="_blank"
                                   rel="noopener noreferrer"
                                   style="
                                       color: var(--primary-color, #3b82f6);
                                       font-size: 0.75rem;
                                       font-weight: 500;
                                       text-decoration: none;
                                       padding: 0.25rem 0.5rem;
                                       border: 1px solid var(--primary-color, #3b82f6);
                                       border-radius: 4px;
                                       transition: all 0.2s;
                                   "
                                   onmouseover="this.style.background='var(--primary-color, #3b82f6)'; this.style.color='white';"
                                   onmouseout="this.style.background='transparent'; this.style.color='var(--primary-color, #3b82f6)';"
                                   onclick="event.stopPropagation();">
                                    View on Marktplaats
                                </a>
                            </div>
                        </footer>
                    </div>

                    <!-- Image thumbnail -->
                    ${result.image_url ? `
                        <figure style="margin: 0;">
                            <img src="${result.image_url}"
                                 alt="${title}"
                                 loading="lazy"
                                 style="
                                     width: 80px;
                                     height: 60px;
                                     object-fit: cover;
                                     border-radius: 4px;
                                     background: var(--surface, #f9fafb);
                                 "
                                 onerror="this.style.display='none'">
                        </figure>
                    ` : ''}
                </div>
            </article>
        `;
    }


    renderSearchDetails(search) {
        const container = $('#search-details-content');
        if (!container) return;

        if (!search) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-title">Select a search</div>
                    <p>Choose a search from the list to view and edit its details.</p>
                </div>
            `;
            return;
        }

        const lastRun = search.last_run_at ?
            new Date(search.last_run_at).toLocaleString() : 'Never';

        container.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h3 style="margin: 0; font-size: 1.1rem;">${escapeHtml(search.query)}</h3>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    <button class="btn btn-primary btn-sm" onclick="app.switchTab('results')">View Results</button>
                    <a href="${this.buildMarktplaatsUrl(search)}"
                       target="_blank"
                       rel="noopener noreferrer"
                       class="btn btn-primary btn-sm"
                       title="Compare on Marktplaats.nl">
                        Compare on MP
                    </a>
                    ${search.status === 'active' ? `
                        <button class="btn btn-primary btn-sm" onclick="app.stopSearch('${search.id}')">Stop</button>
                    ` : `
                        <button class="btn btn-primary btn-sm" onclick="app.activateSearch('${search.id}')">Activate</button>
                    `}
                    <button class="btn btn-danger btn-sm" onclick="app.deleteSearch('${search.id}')">Delete</button>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; padding: 1rem; background: var(--surface, #f9fafb); border-radius: 6px; margin-bottom: 1.5rem;">
                <div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary, #6b7280); margin-bottom: 0.25rem;">Status</div>
                    <span class="status-badge status-${search.status.toLowerCase()}">${search.status}</span>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary, #6b7280); margin-bottom: 0.25rem;">Last Run</div>
                    <div style="font-size: 0.85rem;">${lastRun}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary, #6b7280); margin-bottom: 0.25rem;">Interval</div>
                    <div style="font-size: 0.85rem;">Every ${Math.round(search.interval / 60)} minutes</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary, #6b7280); margin-bottom: 0.25rem;">Location</div>
                    <div style="font-size: 0.85rem;">${search.zip_code || 'All locations'}${search.distance ? ` (${search.distance}km)` : ''}</div>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
                <div style="padding: 1rem; background: var(--surface, #f9fafb); border-radius: 6px;">
                    <h4 style="margin: 0 0 0.75rem 0; font-size: 0.9rem; color: var(--text-secondary, #6b7280);">Search Parameters</h4>
                    <div style="display: grid; gap: 0.5rem; font-size: 0.85rem;">
                        <div><strong>Query:</strong> ${escapeHtml(search.query)}</div>
                        <div><strong>Price Range:</strong> €${search.price_from || 0} - €${search.price_to || '∞'}</div>
                        <div><strong>Sort:</strong> ${search.sort_by || 'Relevance'} ${search.sort_order ? `(${search.sort_order})` : ''}</div>
                        <div><strong>Limit:</strong> ${search.limit || 25} results</div>
                    </div>
                </div>
                <div style="padding: 1rem; background: var(--surface, #f9fafb); border-radius: 6px;">
                    <h4 style="margin: 0 0 0.75rem 0; font-size: 0.9rem; color: var(--text-secondary, #6b7280);">Timestamps</h4>
                    <div style="display: grid; gap: 0.5rem; font-size: 0.85rem;">
                        <div><strong>Created:</strong> ${formatDateTime(search.created_at)}</div>
                        <div><strong>Last Updated:</strong> ${formatDateTime(search.updated_at)}</div>
                        <div><strong>Last Run:</strong> ${lastRun}</div>
                        ${search.last_error ? `<div style="color: var(--error-color, #ef4444);"><strong>Last Error:</strong> ${escapeHtml(search.last_error)}</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    buildMarktplaatsUrl(search) {
        const baseUrl = 'https://www.marktplaats.nl/q/';
        const params = new URLSearchParams();

        if (search.zip_code) params.set('postcode', search.zip_code);
        if (search.distance) params.set('distanceMeters', String(search.distance * 1000));
        if (search.price_from) params.set('PriceCentsFrom', String(search.price_from * 100));
        if (search.price_to) params.set('PriceCentsTo', String(search.price_to * 100));
        if (search.sort_by === 'price' && search.sort_order === 'asc') {
            params.set('sortBy', 'PRICE');
            params.set('sortOrder', 'INCREASING');
        } else if (search.sort_by === 'price' && search.sort_order === 'desc') {
            params.set('sortBy', 'PRICE');
            params.set('sortOrder', 'DECREASING');
        } else if (search.sort_by === 'date') {
            params.set('sortBy', 'DATE');
        }

        const queryString = params.toString();
        return `${baseUrl}${encodeURIComponent(search.query.toLowerCase())}/${queryString ? '?' + queryString : ''}`;
    }

    async stopSearch(searchId) {
        try {
            await apiService.updateSearch(searchId, { status: 'inactive' });
            await this.loadSearches();
            const search = this.searches.find(s => s.id === searchId);
            if (search) this.renderSearchDetails(search);
            showAlert('Search stopped successfully', 'success');
        } catch (error) {
            console.error('Failed to stop search:', error);
            showAlert('Failed to stop search: ' + error.message, 'error');
        }
    }

    async activateSearch(searchId) {
        try {
            await apiService.updateSearch(searchId, { status: 'active' });
            await this.loadSearches();
            const search = this.searches.find(s => s.id === searchId);
            if (search) this.renderSearchDetails(search);
            showAlert('Search activated successfully', 'success');
        } catch (error) {
            console.error('Failed to activate search:', error);
            showAlert('Failed to activate search: ' + error.message, 'error');
        }
    }

    setupTabSwitching() {
        const tabs = $$('.tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.target.textContent.toLowerCase().replace(' ', '');
                this.switchTab(tabName === 'results' ? 'results' : 'details');
            });
        });
    }

    switchTab(tabName) {
        // Update tab states
        $$('.tab').forEach(tab => tab.classList.remove('active'));
        $$('.tab-panel').forEach(panel => panel.classList.remove('active'));

        // Activate selected tab and panel
        const tab = $(`.tab[onclick*="${tabName}"]`) ||
                   Array.from($$('.tab')).find(t =>
                       t.textContent.toLowerCase().includes(tabName)
                   );
        if (tab) tab.classList.add('active');

        $(`#${tabName}-tab`)?.classList.add('active');
    }

    openSearchModal(search = null) {
        this.searchForm.open(search);
    }

    closeSearchModal() {
        this.searchForm.close();
    }


    async refreshAllSearches() {
        try {
            showAlert('Refreshing all searches...', 'info');
            await apiService.refreshAllSearches();
            await this.loadSearches();
            showAlert('All searches refreshed successfully!', 'success');
        } catch (error) {
            console.error('Failed to refresh searches:', error);
            showAlert('Failed to refresh searches: ' + error.message, 'error');
        }
    }

    async deleteSearch(searchId) {
        if (!confirm('Are you sure you want to delete this search? This action cannot be undone.')) {
            return;
        }

        try {
            await apiService.deleteSearch(searchId);
            await this.loadSearches();

            // Clear selection if deleted search was selected
            if (this.selectedSearchId === searchId) {
                this.selectedSearchId = null;
                this.currentSearchId = null;

                // Show empty state
                const resultsContainer = $('#results-content');
                const detailsContainer = $('#search-details-content');

                if (resultsContainer) {
                    resultsContainer.innerHTML = '<div class="empty-state"><div class="empty-state-title">Select a search to view results</div></div>';
                }
                if (detailsContainer) {
                    detailsContainer.innerHTML = '<div class="empty-state"><div class="empty-state-title">Select a search to view details</div></div>';
                }
            }

            showAlert('Search deleted successfully', 'success');

        } catch (error) {
            console.error('Failed to delete search:', error);
            showAlert('Failed to delete search: ' + error.message, 'error');
        }
    }

    startHealthChecks() {
        // Initial health check
        this.checkHealth();

        // Periodic health checks
        setInterval(() => {
            this.checkHealth();
        }, CONFIG.DEFAULTS.HEALTH_CHECK_INTERVAL);
    }

    startProgressUpdates() {
        // Update progress bars every 30 seconds
        this.progressUpdateInterval = setInterval(() => {
            this.updateProgressBars();
        }, 30000);
    }

    updateProgressBars() {
        if (!this.searches || this.searches.length === 0) return;

        // Re-render search list to update progress bars
        this.renderSearches(this.searches);
    }

    async checkHealth() {
        try {
            await apiService.healthCheck();
            // Health check passed - could update UI if needed
        } catch (error) {
            console.warn('Health check failed:', error);
            // Could show health status in UI
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MarktplaatsSearchApp();
});

// Also expose the class globally for console access
window.MarktplaatsSearchApp = MarktplaatsSearchApp;
