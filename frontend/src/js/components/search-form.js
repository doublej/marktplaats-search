/**
 * Search Form Component
 * Handles the search creation/editing modal
 */
class SearchForm {
    constructor(app) {
        this.app = app;
        this.editingSearch = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Form submission
        document.getElementById('search-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.save();
        });

        // Cancel and close buttons
        document.getElementById('cancel-search').addEventListener('click', () => {
            this.close();
        });

        document.getElementById('search-modal-close').addEventListener('click', () => {
            this.close();
        });

        // Close modal on background click
        document.getElementById('search-modal').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                this.close();
            }
        });
    }

    open(search = null) {
        this.editingSearch = search;
        const modal = document.getElementById('search-modal');
        const title = document.getElementById('search-modal-title');
        const saveBtn = document.getElementById('save-search-text');
        const form = document.getElementById('search-form');

        if (search) {
            title.textContent = 'Edit Search';
            saveBtn.textContent = 'Update Search';
            this.populateForm(search);
        } else {
            title.textContent = 'Create New Search';
            saveBtn.textContent = 'Create Search';
            form.reset();
            document.getElementById('search-limit').value = '25';
            document.getElementById('search-interval').value = '60';
        }

        modal.classList.add('open');
    }

    close() {
        document.getElementById('search-modal').classList.remove('open');
        this.editingSearch = null;
        document.getElementById('search-form-error').textContent = '';
    }

    populateForm(search) {
        document.getElementById('search-query').value = search.query || '';
        document.getElementById('search-zip-code').value = search.zip_code || '';
        document.getElementById('search-distance').value = search.distance || '';
        document.getElementById('search-price-from').value = search.price_from || '';
        document.getElementById('search-price-to').value = search.price_to || '';
        document.getElementById('search-limit').value = search.limit || 25;
        document.getElementById('search-interval').value = Math.round((search.interval || 3600) / 60);
        document.getElementById('search-sort-by').value = search.sort_by || '';
        document.getElementById('search-sort-order').value = search.sort_order || '';
    }

    async save() {
        const saveBtn = document.getElementById('save-search');
        const loading = document.getElementById('search-save-loading');
        const errorEl = document.getElementById('search-form-error');

        saveBtn.disabled = true;
        loading.style.display = 'inline-block';
        errorEl.textContent = '';

        try {
            const formData = this.getFormData();

            if (this.editingSearch) {
                await apiService.updateSearch(this.editingSearch.search_id, formData);
            } else {
                await apiService.createSearch(formData);
            }

            this.close();
            this.app.loadSearches();
        } catch (error) {
            errorEl.textContent = error.message || error.toString() || 'Unknown error';
        } finally {
            saveBtn.disabled = false;
            loading.style.display = 'none';
        }
    }

    getFormData() {
        const data = {
            query: document.getElementById('search-query').value,
            interval: parseInt(document.getElementById('search-interval').value) * 60,
            limit: parseInt(document.getElementById('search-limit').value) || 25
        };

        // Optional fields
        const zipCode = document.getElementById('search-zip-code').value;
        if (zipCode) data.zip_code = zipCode;

        const distance = parseInt(document.getElementById('search-distance').value);
        if (distance) data.distance = distance * 1000; // Convert km to meters

        const priceFrom = parseInt(document.getElementById('search-price-from').value);
        if (priceFrom) data.price_from = priceFrom;

        const priceTo = parseInt(document.getElementById('search-price-to').value);
        if (priceTo) data.price_to = priceTo;

        const sortBy = document.getElementById('search-sort-by').value;
        if (sortBy) data.sort_by = sortBy;

        const sortOrder = document.getElementById('search-sort-order').value;
        if (sortOrder) data.sort_order = sortOrder;

        return data;
    }

    async edit(searchId) {
        try {
            const search = await apiService.getSearch(searchId);
            this.open(search);
        } catch (error) {
            const errorMessage = error.message || error.toString() || 'Unknown error';
            alert(`Failed to load search details: ${errorMessage}`);
        }
    }
}
