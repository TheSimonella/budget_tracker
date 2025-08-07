    let categories = [];
    let currentMonth = localStorage.getItem('selectedMonth') || new Date().toISOString().slice(0, 7);
    localStorage.setItem('selectedMonth', currentMonth);
    let editingTransactionId = null;

    $(document).ready(function() {
        $('#monthSelector').val(currentMonth);
        $('#monthSelector').change(function(){
            currentMonth = $(this).val();
            localStorage.setItem('selectedMonth', currentMonth);
            loadTransactions();
        });
        loadCategories();
        loadTransactions();
        $('input[name="date"]').val(new Date().toISOString().split('T')[0]);

        $('select[name="transaction_type"]').change(function() {
            updateCategoryDropdown($(this).val());
        });

        $('#editTransactionForm select[name="transaction_type"]').change(function() {
            updateCategoryDropdownEdit($(this).val());
        });

        $('#csvFileInput').change(handleCsvImport);
    });

    function handleCsvImport() {
        const input = document.getElementById('csvFileInput');
        if (!input.files.length) return;
        const formData = new FormData();
        formData.append('file', input.files[0]);

        $.ajax({
            url: '/api/import-csv',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(res) {
                showToast(res.message || 'Imported transactions successfully');
                loadTransactions();
            },
            error: function(xhr) {
                const msg = xhr.responseJSON && xhr.responseJSON.error ? xhr.responseJSON.error : 'Failed to import CSV';
                showToast(msg);
            },
            complete: function() {
                input.value = '';
            }
        });
    }
    
    function changeMonth(direction) {
        const dateInput = document.getElementById('monthSelector');
        const currentValue = dateInput.value;
        const [year, month] = currentValue.split('-').map(Number);
        
        const newDate = new Date(year, month - 1 + direction, 1);
        const newYear = newDate.getFullYear();
        const newMonth = String(newDate.getMonth() + 1).padStart(2, '0');
        
        const newValue = `${newYear}-${newMonth}`;
        dateInput.value = newValue;
        currentMonth = newValue;
        localStorage.setItem('selectedMonth', currentMonth);

        loadTransactions();
    }
    
    function loadCategories() {
        $.get('/api/categories', function(data) {
            categories = data;
            
            const categoryFilter = $('#categoryFilter');
            categoryFilter.empty().append('<option value="">All Categories</option>');
            
            // Group by parent category
            const grouped = {};
            categories.forEach(cat => {
                const parent = cat.parent_category || 'Other';
                if (!grouped[parent]) grouped[parent] = [];
                grouped[parent].push(cat);
            });
            
            Object.keys(grouped).sort().forEach(parent => {
                const optgroup = $(`<optgroup label="${parent}">`);
                grouped[parent].forEach(cat => {
                    optgroup.append(`<option value="${cat.id}">${cat.name}</option>`);
                });
                categoryFilter.append(optgroup);
            });
        });
    }
    
    function updateCategoryDropdown(transactionType) {
        const select = $('select[name="category_id"]');
        select.empty().append('<option value="">Select Category</option>');
        
        if (transactionType === 'income') {
            const incomeCategories = categories.filter(c => c.type === 'income' && !c.name.toLowerCase().includes('deduction'));
            const deductionCategories = categories.filter(c => c.type === 'income' && c.name.toLowerCase().includes('deduction'));
            
            if (incomeCategories.length > 0) {
                select.append('<optgroup label="Income Sources">');
                incomeCategories.forEach(cat => {
                    select.append(`<option value="${cat.id}">${cat.name}</option>`);
                });
                select.append('</optgroup>');
            }
            
            if (deductionCategories.length > 0) {
                select.append('<optgroup label="Deductions">');
                deductionCategories.forEach(cat => {
                    select.append(`<option value="${cat.id}">${cat.name}</option>`);
                });
                select.append('</optgroup>');
            }
        } else if (transactionType === 'expense') {
            const grouped = {};
            categories.filter(c => c.type === 'expense' || c.type === 'fund').forEach(cat => {
                const parent = cat.parent_category || 'Other';
                if (!grouped[parent]) grouped[parent] = [];
                grouped[parent].push(cat);
            });
            
            Object.keys(grouped).sort().forEach(parent => {
                select.append(`<optgroup label="${parent}">`);
                grouped[parent].forEach(cat => {
                    select.append(`<option value="${cat.id}">${cat.name}</option>`);
                });
                select.append('</optgroup>');
            });
        } else if (transactionType === 'fund_withdrawal') {
            const fundCategories = categories.filter(c => c.parent_category === 'Savings');
            fundCategories.forEach(cat => {
                select.append(`<option value="${cat.id}">${cat.name}</option>`);
            });
        }
    }
    
    function updateCategoryDropdownEdit(transactionType) {
        const select = $('#editTransactionForm select[name="category_id"]');
        select.empty().append('<option value="">Select Category</option>');
        
        // Same logic as updateCategoryDropdown but for edit form
        updateCategoryDropdown.call(this, transactionType);
    }
    
    function loadTransactions() {
        const scrollPosition = window.scrollY;
        const params = {
            month: $('#monthSelector').val(),
            type: $('#typeFilter').val(),
            category: $('#categoryFilter').val(),
            search: $('#searchFilter').val()
        };

        const tbody = $('#transactionTableBody');
        const emptyState = $('#emptyState');
        tbody.empty();
        emptyState.show().html('<div class="spinner-border text-secondary mb-3" role="status"></div><h5>Loading...</h5>');

        $.get('/api/transactions', params, function(transactions) {
            if (transactions.length === 0) {
                emptyState.html('<i class="fas fa-receipt"></i><h5>No transactions found</h5><p class="mb-0">Try adjusting your filters or add a new transaction.</p>');
                window.scrollTo(0, scrollPosition);
                return;
            }

            emptyState.hide();
            let html = '';

            transactions.forEach(trans => {
                const isDeduction = trans.type === 'income' && trans.category.toLowerCase().includes('deduction');
                const typeClass = isDeduction ? 'category-deduction'
                                   : trans.type === 'income' ? 'category-income'
                                   : trans.type === 'expense' ? 'category-expense'
                                   : 'category-fund';
                let amountClass = 'amount-positive';
                let amountSign = '+';
                if (trans.type === 'expense' || trans.type === 'fund_withdrawal') {
                    amountClass = 'amount-negative';
                    amountSign = '-';
                } else if (isDeduction) {
                    amountClass = 'amount-deduction';
                    amountSign = '-';
                }

                html += `
                    <tr class="transaction-row">
                        <td>${new Date(trans.date).toLocaleDateString()}</td>
                        <td>
                            <div class="fw-medium">${trans.description}</div>
                            ${trans.notes ? `<small class="text-muted">${trans.notes}</small>` : ''}
                        </td>
                        <td><span class="category-pill ${typeClass}">${trans.category}</span></td>
                        <td>${trans.merchant || '-'}</td>
                        <td class="${amountClass} text-end">${amountSign}${formatCurrency(Math.abs(trans.amount))}</td>
                        <td>
                            <div class="action-buttons text-end">
                                <button class="btn btn-sm btn-link text-primary p-1" onclick="editTransaction(${trans.id})">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-sm btn-link text-danger p-1" onclick="deleteTransaction(${trans.id})">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });

            tbody.html(html);
            window.scrollTo(0, scrollPosition);
        });
    }
    
    function saveTransaction() {
        const button = $('#addTransactionModal .btn-modern-primary');
        const formData = $('#addTransactionForm').serializeArray();
        const data = {};
        formData.forEach(field => {
            data[field.name] = field.value;
        });
        
        setButtonLoading(button, true);
        
        $.ajax({
            url: '/api/transactions',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function() {
                $('#addTransactionModal').modal('hide');
                $('#addTransactionForm')[0].reset();
                showToast('Transaction added successfully!');
                loadTransactions();
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Unknown error';
                showToast('Error: ' + error, 'error');
            },
            complete: function() {
                setButtonLoading(button, false);
            }
        });
    }
    
    function editTransaction(id) {
        editingTransactionId = id;
        
        $.get(`/api/transactions/${id}`, function(data) {
            $('#editTransactionForm input[name="id"]').val(data.id);
            $('#editTransactionForm select[name="transaction_type"]').val(data.transaction_type);
            
            updateCategoryDropdownEdit(data.transaction_type);
            
            setTimeout(() => {
                $('#editTransactionForm select[name="category_id"]').val(data.category_id);
            }, 100);
            
            $('#editTransactionForm input[name="amount"]').val(data.amount);
            $('#editTransactionForm input[name="description"]').val(data.description);
            $('#editTransactionForm input[name="merchant"]').val(data.merchant || '');
            $('#editTransactionForm input[name="date"]').val(data.date);
            $('#editTransactionForm input[name="notes"]').val(data.notes || '');
            
            $('#editTransactionModal').modal('show');
        }).fail(function() {
            showToast('Error loading transaction data', 'error');
        });
    }
    
    function updateTransaction() {
        const button = $('#editTransactionModal .btn-modern-primary');
        const formData = $('#editTransactionForm').serializeArray();
        const data = {};
        formData.forEach(field => {
            data[field.name] = field.value;
        });
        
        setButtonLoading(button, true);
        
        $.ajax({
            url: `/api/transactions/${editingTransactionId}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function() {
                $('#editTransactionModal').modal('hide');
                showToast('Transaction updated successfully!');
                loadTransactions();
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Unknown error';
                showToast('Error: ' + error, 'error');
            },
            complete: function() {
                setButtonLoading(button, false);
            }
        });
    }
    
    function deleteTransaction(id) {
        if (confirm('Are you sure you want to delete this transaction?')) {
            $.ajax({
                url: `/api/transactions/${id}`,
                method: 'DELETE',
                success: function() {
                    showToast('Transaction deleted successfully!');
                    loadTransactions();
                },
                error: function(xhr) {
                    const error = xhr.responseJSON?.error || 'Unknown error';
                    showToast('Error: ' + error, 'error');
                }
            });
        }
    }
