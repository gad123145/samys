// Custom JavaScript for CRM System

// Initialize Bootstrap components
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize all popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Handle Search Form
const handleSearchForm = () => {
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const fromDate = document.getElementById('fromDate');
            const toDate = document.getElementById('toDate');
            
            if (fromDate && toDate && fromDate.value && toDate.value) {
                if (new Date(fromDate.value) > new Date(toDate.value)) {
                    e.preventDefault();
                    alert('تاريخ البداية يجب أن يكون قبل تاريخ النهاية');
                }
            }
        });
    }
};

// Initialize Date Inputs
const initializeDateInputs = () => {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (!input.value) {
            input.valueAsDate = new Date();
        }
    });
};

// Handle Quick Updates
const handleQuickUpdates = () => {
    const quickUpdateButtons = document.querySelectorAll('.quick-update');
    quickUpdateButtons.forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            const customerId = this.dataset.customerId;
            const action = this.dataset.action;
            
            try {
                const response = await fetch('/quick_update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        customer_id: customerId,
                        action: action
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    // Update UI elements
                    const statusBadge = document.querySelector(`#status-${customerId}`);
                    if (statusBadge) {
                        statusBadge.textContent = data.new_status;
                        statusBadge.className = `badge bg-${data.status_color}`;
                    }
                    
                    // Show success message
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-success alert-dismissible fade show';
                    alert.innerHTML = `
                        ${data.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    `;
                    document.querySelector('.main-content').insertBefore(alert, document.querySelector('.main-content').firstChild);
                }
            } catch (error) {
                console.error('Error:', error);
                // Show error message
                const alert = document.createElement('div');
                alert.className = 'alert alert-danger alert-dismissible fade show';
                alert.innerHTML = `
                    حدث خطأ أثناء تحديث حالة العميل
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                document.querySelector('.main-content').insertBefore(alert, document.querySelector('.main-content').firstChild);
            }
        });
    });
};

// Handle Export Modal
const handleExport = () => {
    const exportForm = document.getElementById('exportForm');
    if (exportForm) {
        exportForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const format = document.getElementById('exportFormat').value;
            const fromDate = document.getElementById('exportFromDate').value;
            const toDate = document.getElementById('exportToDate').value;
            
            window.location.href = `/export?format=${format}&from_date=${fromDate}&to_date=${toDate}`;
        });
    }
};

// Initialize all custom functionality
document.addEventListener('DOMContentLoaded', function() {
    handleSearchForm();
    initializeDateInputs();
    handleQuickUpdates();
    handleExport();
});
