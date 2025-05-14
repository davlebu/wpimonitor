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
    const customTerminInput = document.getElementById('customTerminInput');
    const columnFilters = document.querySelectorAll('.column-filter');
    const sortableHeaders = document.querySelectorAll('th.sortable');
    const rejectedFilesBtn = document.getElementById('rejectedFilesBtn');

    // Statistics selection elements
    const wpiRadio = document.getElementById('wpiRadio');
    const emisoRadio = document.getElementById('emisoRadio');

    // Get current statistics from the HTML class
    let currentStatistics = document.documentElement.className.replace('theme-', '');
    if (!currentStatistics || (currentStatistics !== 'wpi' && currentStatistics !== 'emiso')) {
        currentStatistics = 'wpi'; // Default to WPI if not set
    }

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

    // Initialize Advanced Settings
    const importCutDate = document.getElementById('importCutDate');
    const authFilePath = document.getElementById('authFilePath');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    const settingsSaveAlert = document.getElementById('settingsSaveAlert');

    // Save settings
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', function() {
            const settings = {
                statistics: currentStatistics,
                import_cut_date: importCutDate.value,
                auth_file_path: authFilePath.value
            };

            fetch('/api/settings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    settingsSaveAlert.className = 'alert alert-success mt-2';
                    settingsSaveAlert.textContent = 'Settings saved successfully!';
                } else {
                    settingsSaveAlert.className = 'alert alert-danger mt-2';
                    settingsSaveAlert.textContent = 'Error saving settings.';
                }
                settingsSaveAlert.style.display = 'block';

                setTimeout(() => {
                    settingsSaveAlert.style.display = 'none';
                }, 3000);
            })
            .catch(error => {
                settingsSaveAlert.className = 'alert alert-danger mt-2';
                settingsSaveAlert.textContent = 'Error: ' + error.message;
                settingsSaveAlert.style.display = 'block';
            });
        });
    }

    // Initialize data loading
    if (terminSelect.options.length > 0) {
        loadData();
    }

    // Event listeners
    terminSelect.addEventListener('change', function() {
        // Clear custom termin input when dropdown selection changes
        customTerminInput.value = '';
        currentPage = 1;
        filters = {};
        resetFiltersUI();
        loadData();
    });

    // Add event listener for custom termin input for validation feedback
    customTerminInput.addEventListener('input', function() {
        const value = this.value.trim();
        if (value === '') {
            this.classList.remove('is-invalid', 'is-valid');
        } else if (/^\d{6}$/.test(value)) {
            this.classList.remove('is-invalid');
            this.classList.add('is-valid');
        } else {
            this.classList.remove('is-valid');
            this.classList.add('is-invalid');
        }
    });

    // Statistics type selection
    if (wpiRadio && emisoRadio) {
        wpiRadio.addEventListener('change', function() {
            if (this.checked) {
                switchStatistics('wpi');
                updateStatisticsButtonsUI('wpi');
            }
        });

        emisoRadio.addEventListener('change', function() {
            if (this.checked) {
                switchStatistics('emiso');
                updateStatisticsButtonsUI('emiso');
            }
        });
    }

    // Update the statistics buttons UI based on selection
    function updateStatisticsButtonsUI(statistics) {
        const wpiBtn = document.querySelector('label[for="wpiRadio"]');
        const emisoBtn = document.querySelector('label[for="emisoRadio"]');

        if (statistics === 'wpi') {
            wpiBtn.classList.add('active');
            emisoBtn.classList.remove('active');
        } else {
            emisoBtn.classList.add('active');
            wpiBtn.classList.remove('active');
        }
    }

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

   missingFilesBtn.addEventListener('click', function() {
       // Clear other filters
       delete filters['rejected_files'];

       // Toggle missing files filter
       if (filters['missing_files']) {
           delete filters['missing_files'];
           missingFilesBtn.classList.add('inactive');
       } else {
           filters['missing_files'] = true;
           missingFilesBtn.classList.remove('inactive');
           rejectedFilesBtn.classList.add('inactive');
       }

       currentPage = 1;
       loadData();
   });

   // Reset filters
   resetFiltersBtn.addEventListener('click', function() {
       filters = {};
       resetFiltersUI();
       loadData();
   });

   // Rejected files filter
   rejectedFilesBtn.addEventListener('click', function() {
       // Clear other filters
       delete filters['missing_files'];

       // Toggle rejected files filter
       if (filters['rejected_files']) {
           delete filters['rejected_files'];
           rejectedFilesBtn.classList.add('inactive');
       } else {
           filters['rejected_files'] = true;
           rejectedFilesBtn.classList.remove('inactive');
           missingFilesBtn.classList.add('inactive');
       }

       currentPage = 1;
       loadData();
   });

    // Update data
    updateDataBtn.addEventListener('click', function() {
        // Get the custom termin if provided, otherwise use the selected termin
        const customTermin = customTerminInput.value.trim();
        const termin = customTermin || terminSelect.value;

        // Validate the termin format if custom termin is provided
        if (customTermin && !/^\d{6}$/.test(customTermin)) {
            alert('Please enter a valid termin in the format YYYYMM (e.g., 202405).');
            return;
        }

        if (confirm('Are you sure you want to update data for termin ' + termin + '?')) {
            loadingModal.show();
            fetch('/api/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    termin: termin,
                    statistics: currentStatistics
                })
            })
            .then(response => response.json())
            .then(data => {
                loadingModal.hide();
                if (data.success) {
                    alert('Data updated successfully!');
                    // If this was a new termin, refresh the termin list
                    if (customTermin) {
                        fetchTermins();
                    } else {
                        loadData();
                    }
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

            fetch(`/api/entry/${termin}/${id2}?statistics=${currentStatistics}`, {
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

    // Function to switch statistics type
    function switchStatistics(statistics) {
        if (currentStatistics === statistics) {
            return; // No change needed
        }

        currentStatistics = statistics;

        // Update theme
        document.documentElement.className = 'theme-' + statistics;

        // Update any statistics badges in the UI
        const statisticsBadges = document.querySelectorAll('.theme-badge');
        statisticsBadges.forEach(badge => {
            badge.textContent = statistics.toUpperCase();
        });

        // Update statistics buttons appearance
        updateStatisticsButtonsUI(statistics);

        // Save the setting to the server
        fetch('/api/switch_statistics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                statistics: statistics
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reset filters and pagination
                filters = {};
                currentPage = 1;
                resetFiltersUI();

                // Fetch termins for the new statistics type
                fetchTermins();
            } else {
                alert('Error switching statistics: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            alert('Error: ' + error);
        });
    }

    // Load data function
    function loadData() {
        const termin = terminSelect.value;
        if (!termin) return;

        // Build query parameters
        const params = new URLSearchParams({
            statistics: currentStatistics,
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
                totalRecords.textContent = data.total;

                // Also load statistics
                fetchStatistics(termin);
            })
            .catch(error => {
                console.error('Error loading data:', error);
                tableBody.innerHTML = `<tr><td colspan="6" class="text-center">Error loading data: ${error}</td></tr>`;
            });
    }

    // Function to fetch statistics
    function fetchStatistics(termin) {
        fetch(`/api/statistics/${termin}?statistics=${currentStatistics}`)
            .then(response => response.json())
            .then(data => {
                missingCount.textContent = data.missing_count;
                missingPercentage.textContent = data.missing_percentage + '%';
            })
            .catch(error => {
                console.error('Error loading statistics:', error);
            });
    }

    // Render table function
    function renderTable(data) {
        tableBody.innerHTML = '';

        data.forEach(item => {
            const row = document.createElement('tr');

            // Apply appropriate highlighting based on file status
            if (item.rejected_import_found) {
                row.classList.add('rejected-file');
            } else if (!item.import_found) {
                row.classList.add('missing-file');
            }

            // Add columns
            row.innerHTML = `
                <td>${escapeHtml(item.datei || '')}</td>
                <td>${escapeHtml(item.erstellt || '')}</td>
                <td>${escapeHtml(item.melder_id || '')}</td>
                <td>${escapeHtml(item.typ || '')}</td>
                <td>${getStatusIcon(item)}</td>
                <td>${item.ok ? '<i class="bi bi-check-circle-fill text-success"></i>' : '<i class="bi bi-x-circle-fill text-danger"></i>'}</td>
            `;

            // Open modal on row click
            row.addEventListener('click', function() {
                openEntryDetails(item.id2);
            });

            tableBody.appendChild(row);
        });
    }

    // Helper function to display appropriate status icon
    function getStatusIcon(item) {
        if (item.rejected_import_found) {
            return '<i class="bi bi-exclamation-triangle-fill text-purple"></i>';
        } else if (item.import_found) {
            return '<i class="bi bi-check-circle-fill text-success"></i>';
        } else {
            return '<i class="bi bi-x-circle-fill text-danger"></i>';
        }
    }

    // Render pagination function
    function renderPagination(total) {
        pagination.querySelector('ul').innerHTML = '';
        const totalPages = Math.ceil(total / pageSize);

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

    // Open entry details
    function openEntryDetails(id2) {
        const termin = terminSelect.value;

        fetch(`/api/entry/${termin}/${id2}?statistics=${currentStatistics}`)
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
        rejectedFilesBtn.classList.remove('btn-purple');
        rejectedFilesBtn.classList.add('btn-outline-purple');
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

    // Add function to fetch termins
    function fetchTermins() {
        fetch(`/api/termins?statistics=${currentStatistics}`)
            .then(response => response.json())
            .then(data => {
                // Update the select options
                terminSelect.innerHTML = '';
                data.forEach(termin => {
                    // Clean up the termin value - remove any potential prefix
                    let displayTermin = termin;
                    let valueTermin = termin;

                    // If this is already displaying EMISO termins, clean them up
                    if (termin.startsWith('_EMISO')) {
                        displayTermin = termin.substring(6); // Remove _EMISO prefix for display
                    }

                    const option = document.createElement('option');
                    option.value = valueTermin;
                    option.textContent = displayTermin;
                    terminSelect.appendChild(option);
                });
                // Clear the custom termin input
                customTerminInput.value = '';
                // Load data for the newly selected termin
                if (data.length > 0) {
                    loadData();
                } else {
                    // No data for this statistics type
                    tableBody.innerHTML = `<tr><td colspan="6" class="text-center">No data available for ${currentStatistics.toUpperCase()}. Use the Update Data button to import.</td></tr>`;
                    totalRecords.textContent = '0';
                    missingCount.textContent = '0';
                    missingPercentage.textContent = '0%';
                    pagination.querySelector('ul').innerHTML = '';
                }
            })
            .catch(error => {
                console.error('Error fetching termins:', error);
            });
    }
});