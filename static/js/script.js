document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const terminSelect = document.getElementById('terminSelect');
    const dataTable = document.getElementById('dataTable');
    const tableBody = document.getElementById('tableBody');
    const pagination = document.getElementById('pagination');
    const totalRecords = document.getElementById('totalRecords');
    const missingCount = document.getElementById('missingCount');
    const missingPercentage = document.getElementById('missingPercentage');
    const missingFilesBtn = document.getElementById('missingFilesBtn');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    const updateDataBtn = document.getElementById('updateDataBtn');
    const columnFilters = document.querySelectorAll('.column-filter');
    const sortableHeaders = document.querySelectorAll('th.sortable');
    
    // Configuration elements
    const importCutDate = document.getElementById('importCutDate');
    const authFilePath = document.getElementById('authFilePath');
    const saveConfigBtn = document.getElementById('saveConfigBtn');
    
    // Bootstrap modals
    const entryModal = new bootstrap.Modal(document.getElementById('entryModal'));
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    
    // Modal elements
    const entryDetails = document.getElementById('entryDetails');
    const entryComment = document.getElementById('entryComment');
    const entryOk = document.getElementById('entryOk');
    const saveEntryBtn = document.getElementById('saveEntryBtn');
    
    // State variables
    let currentPage = 1;
    let pageSize = 20;
    let sortBy = 'datei';
    let sortOrder = 'asc';
    let filters = {};
    let currentEntry = null;
    
    // Initialize
    if (terminSelect.options.length > 0) {
        loadData();
        loadConfig();
    }
    
    // Event listeners
    terminSelect.addEventListener('change', function() {
        currentPage = 1;
        filters = {};
        resetFiltersUI();
        loadData();
    });
    
    // Sorting
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const field = this.getAttribute('data-field');
            if (sortBy === field) {
                sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                sortBy = field;
                sortOrder = 'asc';
            }
            
            // Update sort icons
            sortableHeaders.forEach(h => {
                h.classList.remove('active-sort');
                const icon = h.querySelector('.sort-icon');
                icon.className = 'bi sort-icon';
                icon.classList.add(h === this ? 
                    (sortOrder === 'asc' ? 'bi-sort-alpha-down' : 'bi-sort-alpha-up') : 
                    'bi-sort-alpha-down');
            });
            
            this.classList.add('active-sort');
            loadData();
        });
    });
    
    // Column filters
    columnFilters.forEach(filter => {
        filter.addEventListener('input', function() {
            const field = this.getAttribute('data-field');
            if (this.value) {
                filters[field] = this.value;
            } else {
                delete filters[field];
            }
            currentPage = 1;
            loadData();
        });
    });
    
    // Missing files filter
    missingFilesBtn.addEventListener('click', function() {
        filters['missing_files'] = true;
        currentPage = 1;
        loadData();
        missingFilesBtn.classList.add('btn-danger');
        missingFilesBtn.classList.remove('btn-outline-danger');
    });
    
    // Reset filters
    resetFiltersBtn.addEventListener('click', function() {
        filters = {};
        resetFiltersUI();
        loadData();
    });
    
    // Update data
    updateDataBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to update data for termin ' + terminSelect.value + '?')) {
            loadingModal.show();
            fetch('/api/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    termin: terminSelect.value
                })
            })
            .then(response => response.json())
            .then(data => {
                loadingModal.hide();
                if (data.success) {
                    alert('Data updated successfully!');
                    loadData();
                } else {
                    alert('Error updating data: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                loadingModal.hide();
                alert('Error: ' + error);
            });
        }
    });
    
    // Save entry changes
    saveEntryBtn.addEventListener('click', function() {
        if (currentEntry) {
            const termin = terminSelect.value;
            const id2 = currentEntry.id2;
            const comment = entryComment.value;
            const ok = entryOk.checked;
            
            fetch(`/api/entry/${termin}/${id2}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    comment: comment,
                    ok: ok
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    entryModal.hide();
                    loadData();
                } else {
                    alert('Error saving changes!');
                }
            })
            .catch(error => {
                alert('Error: ' + error);
            });
        }
    });
    
    // Save configuration
    saveConfigBtn.addEventListener('click', function() {
        const cutDateValue = importCutDate.value;
        const authFileValue = authFilePath.value;
        
        // Save Import Cut Date
        if (cutDateValue) {
            updateConfig('IMPORT_CUT_DATE', cutDateValue);
        }
        
        // Save Auth File Path
        if (authFileValue) {
            updateConfig('AUTH_FILE_PATH', authFileValue);
        }
    });
    
    // Function to load configuration
    function loadConfig() {
        fetch('/api/config')
            .then(response => response.json())
            .then(config => {
                if (config['IMPORT_CUT_DATE']) {
                    importCutDate.value = config['IMPORT_CUT_DATE'];
                }
                if (config['AUTH_FILE_PATH']) {
                    authFilePath.value = config['AUTH_FILE_PATH'];
                }
            })
            .catch(error => {
                console.error('Error loading configuration:', error);
            });
    }
    
    // Function to update configuration
    function updateConfig(key, value) {
        fetch(`/api/config/${key}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                value: value
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(`Configuration ${key} updated successfully!`);
            } else {
                alert(`Error updating configuration: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            alert(`Error: ${error}`);
        });
    }
    
    // Load data function
    function loadData() {
        const termin = terminSelect.value;
        if (!termin) return;
        
        // Build query parameters
        const params = new URLSearchParams({
            page: currentPage,
            page_size: pageSize,
            sort_by: sortBy,
            sort_order: sortOrder
        });
        
        // Add filters
        for (const [key, value] of Object.entries(filters)) {
            params.append(key, value);
        }
        
        // Fetch data
        fetch(`/api/data/${termin}?${params}`)
            .then(response => response.json())
            .then(data => {
                renderTable(data.data);
                renderPagination(data.total);
                // We don't update statistics from filtered data anymore
            })
            .catch(error => {
                console.error('Error fetching data:', error);
            });
            
        // Fetch statistics separately - not affected by filters
        fetch(`/api/statistics/${termin}`)
            .then(response => response.json())
            .then(stats => {
                updateStatistics(stats);
            })
            .catch(error => {
                console.error('Error fetching statistics:', error);
            });
    }
    
    // Render table function
    function renderTable(data) {
        tableBody.innerHTML = '';
        
        data.forEach(item => {
            const row = document.createElement('tr');
            
            // Highlight missing files
            if (!item.import_found) {
                row.classList.add('missing-file');
            }
            
            // Add columns
            row.innerHTML = `
                <td>${escapeHtml(item.datei || '')}</td>
                <td>${escapeHtml(item.erstellt || '')}</td>
                <td>${escapeHtml(item.melder_id || '')}</td>
                <td>${escapeHtml(item.typ || '')}</td>
                <td>${item.import_found ? '<i class="bi bi-check-circle-fill text-success"></i>' : '<i class="bi bi-x-circle-fill text-danger"></i>'}</td>
                <td>${item.ok ? '<i class="bi bi-check-circle-fill text-success"></i>' : '<i class="bi bi-x-circle-fill text-danger"></i>'}</td>
            `;
            
            // Open modal on row click
            row.addEventListener('click', function() {
                openEntryDetails(item.id2);
            });
            
            tableBody.appendChild(row);
        });
    }
    
    // Render pagination function
    function renderPagination(total) {
        const totalPages = Math.ceil(total / pageSize);
        pagination.querySelector('ul').innerHTML = '';
        
        // Update total records
        totalRecords.textContent = total;
        
        if (totalPages <= 1) return;
        
        // Previous button
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = '<a class="page-link" href="#">&laquo;</a>';
        prevLi.addEventListener('click', function(e) {
            e.preventDefault();
            if (currentPage > 1) {
                currentPage--;
                loadData();
            }
        });
        pagination.querySelector('ul').appendChild(prevLi);
        
        // Pages
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        
        if (endPage - startPage < 4 && startPage > 1) {
            startPage = Math.max(1, endPage - 4);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const pageLi = document.createElement('li');
            pageLi.className = `page-item ${i === currentPage ? 'active' : ''}`;
            pageLi.innerHTML = `<a class="page-link" href="#">${i}</a>`;
            pageLi.addEventListener('click', function(e) {
                e.preventDefault();
                currentPage = i;
                loadData();
            });
            pagination.querySelector('ul').appendChild(pageLi);
        }
        
        // Next button
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        nextLi.innerHTML = '<a class="page-link" href="#">&raquo;</a>';
        nextLi.addEventListener('click', function(e) {
            e.preventDefault();
            if (currentPage < totalPages) {
                currentPage++;
                loadData();
            }
        });
        pagination.querySelector('ul').appendChild(nextLi);
    }
    
    // Update statistics
    function updateStatistics(data) {
        missingCount.textContent = data.missing_count;
        missingPercentage.textContent = data.missing_percentage + '%';
    }
    
    // Open entry details
    function openEntryDetails(id2) {
        const termin = terminSelect.value;
        
        fetch(`/api/entry/${termin}/${id2}`)
            .then(response => response.json())
            .then(data => {
                if (data) {
                    currentEntry = data;
                    renderEntryDetails(data);
                    entryComment.value = data.comment || '';
                    entryOk.checked = data.ok || false;
                    entryModal.show();
                }
            })
            .catch(error => {
                console.error('Error fetching entry details:', error);
            });
    }
    
    // Render entry details
    function renderEntryDetails(entry) {
        let html = '';
        
        // Show all properties except a few specific ones
        const excludedProps = ['comment', 'ok', 'last_updated', 'id2'];
        
        // Sort properties alphabetically
        const sortedProps = Object.keys(entry).sort();
        
        sortedProps.forEach(key => {
            if (!excludedProps.includes(key)) {
                html += `
                    <div class="entry-property">
                        <div class="label">${key}</div>
                        <div class="value">${escapeHtml(entry[key] !== null ? entry[key].toString() : '')}</div>
                    </div>
                `;
            }
        });
        
        entryDetails.innerHTML = html;
    }
    
    // Reset filters UI
    function resetFiltersUI() {
        columnFilters.forEach(filter => {
            filter.value = '';
        });
        
        missingFilesBtn.classList.remove('btn-danger');
        missingFilesBtn.classList.add('btn-outline-danger');
    }
    
    // Helper function to escape HTML
    function escapeHtml(unsafe) {
        if (unsafe === null || unsafe === undefined) return '';
        return unsafe
            .toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}); 