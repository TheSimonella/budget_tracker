    let currentMonth = localStorage.getItem('selectedMonth') || new Date().toISOString().slice(0, 7);
    localStorage.setItem('selectedMonth', currentMonth);
    let allCategories = [];
    let comparisonData = {};

    let categoryGroups = [];
    let editingCategory = null;
    let editingGroupId = null;
    let incomeCongratsShown = false;
    $(document).ready(function() {
        $('#monthSelector').val(currentMonth);
        $('#monthSelector').change(function(){
            currentMonth = $(this).val();
            localStorage.setItem('selectedMonth', currentMonth);
            loadBudgetForMonth();
        });
        loadBudgetForMonth();
    });
    
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

        loadBudgetForMonth();
    }
    
    function loadBudgetForMonth() {
        currentMonth = $('#monthSelector').val();
        localStorage.setItem('selectedMonth', currentMonth);
        const [year, month] = currentMonth.split('-');
        $('#comparisonMonth').text(`${getMonthName(parseInt(month))} ${year}`);
        
        loadBudgetComparison(function(){
            loadCategories();
        });
    }
    
    function getMonthName(month) {
        const months = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
        return months[month - 1];
    }
    
    function loadCategories() {
        $.get('/api/category-groups', function(groups) {
            categoryGroups = groups;
            $.get(`/api/budget/${currentMonth}`, function(data) {
                allCategories = data;

                const incomeCategories = data.filter(c => c.type === 'income' && !c.name.toLowerCase().includes('deduction'));
                const deductionCategories = data.filter(c => c.type === 'income' && c.name.toLowerCase().includes('deduction'));
                const expenseCategories = data.filter(c => c.type === 'expense');
                const fundCategories = data.filter(c => c.type === 'fund');

                const incomeGroups = getGroups('income').filter(g => !g.name.toLowerCase().includes('deduct'));
                const deductGroups = getGroups('income').filter(g => g.name.toLowerCase().includes('deduct'));
                displayCategories(incomeCategories, 'incomeCategories', incomeGroups);
                displayCategories(deductionCategories, 'deductionCategories', deductGroups);
                displayCategories(expenseCategories, 'expenseCategories', getGroups('expense'));
                displayCategories(fundCategories, 'fundCategories', getGroups('fund'));
                updateSummary();
            });
        });
    }

    function getGroups(type) {
        return categoryGroups.filter(g => g.type === type);
    }
    
    function loadBudgetComparison(callback) {
        $.get(`/api/budget-comparison/${currentMonth}`, function(data) {
            comparisonData = {};
            data.forEach(item => comparisonData[item.category] = item);
            if (callback) callback();
        });
    }
    
    function displayCategories(categories, containerId, groupObjs = []) {
        const container = $('#' + containerId);

        if (categories.length === 0 && groupObjs.length === 0) {
            container.html('<p class="text-muted">No categories added yet. Click "Add" to create your first category.</p>');
            return;
        }

        const groups = {};
        groupObjs.forEach(g => groups[g.name] = { id: g.id, cats: [] });
        categories.forEach(cat => {
            const group = cat.parent_category || 'Other';
            if (!groups[group]) groups[group] = { id: null, cats: [] };
            groups[group].cats.push(cat);
        });

        let html = "";
        // Maintain the order provided by the API so new groups appear first
        Object.keys(groups).forEach(g => {
            const gData = groups[g];
            const safeId = g.replace(/\s+/g, "-");
            const totals = gData.cats.reduce((acc, c) => {
                const comp = comparisonData[c.name] || {actual:0};
                acc.budget += c.monthly_budget || 0;
                acc.actual += comp.actual;
                const isIncome = c.type === 'income' && !c.name.toLowerCase().includes('deduction');
                acc.remaining += isIncome
                    ? comp.actual - (c.monthly_budget || 0)
                    : (c.monthly_budget || 0) - comp.actual;
                return acc;
            }, {budget:0, actual:0, remaining:0});
            const groupNameEsc = g.replace(/'/g, "\\'");
            const groupRemainClass = totals.remaining > 0 ? 'text-success bg-success-subtle' : totals.remaining < 0 ? 'text-danger bg-danger-subtle' : 'text-secondary bg-secondary-subtle';
            html += `<div class="mb-3 category-group" data-group-id="${gData.id || ''}">
                        <div class="category-item group-header category-grid">
                            <div class="category-toggle"><span class="text-secondary group-toggle" data-bs-toggle="collapse" data-bs-target="#grp-${containerId}-${safeId}"><i class="fas fa-caret-down"></i></span></div>
                            <div class="category-name ${gData.id ? 'editable' : ''}" ${gData.id ? `onclick=\"editGroup(${gData.id}, '${groupNameEsc}')\"` : ''}>${g}</div>
                            <div class="category-budget text-end pe-2">${formatCurrency(totals.budget)}</div>
                            <div class="category-actual text-end pe-2">${formatCurrency(totals.actual)}</div>
                            <div class="category-remaining text-end pe-2"><span class="badge fs-6 ${groupRemainClass}">${formatCurrency(totals.remaining)}</span></div>
                            <div class="category-actions"></div>
                        </div>
                        <div id="grp-${containerId}-${safeId}" class="mt-2 collapse show group-categories" data-group="${g}">`;

            gData.cats.sort((a,b)=>a.sort_order-b.sort_order).forEach(cat => {
                const comp = comparisonData[cat.name] || {actual:0};
                const isIncome = cat.type === 'income' && !cat.name.toLowerCase().includes('deduction');
                const remaining = isIncome ? comp.actual - cat.monthly_budget : cat.monthly_budget - comp.actual;
                const pct = cat.monthly_budget ? (comp.actual / cat.monthly_budget) * 100 : (comp.actual > 0 ? 100 : 0);
                const progPct = Math.min(pct, 100);
                const barClass = isIncome ?
                    (comp.actual >= cat.monthly_budget ? 'bg-success' : 'bg-danger') :
                    (comp.actual <= cat.monthly_budget ? 'bg-success' : 'bg-danger');
                const remainClass = remaining > 0 ? 'text-success bg-success-subtle' : remaining < 0 ? 'text-danger bg-danger-subtle' : 'text-secondary bg-secondary-subtle';
                html += `
                    <div class="category-item category-grid" data-id="${cat.id}">
                        <div class="category-toggle"></div>
                        <div class="category-name editable" onclick='editCategory(${JSON.stringify(cat)})'>${cat.name}</div>
                        <div class="category-budget"><input type="number" step="0.01" class="form-control form-control-sm text-end editable-budget" data-id="${cat.id}" data-name="${cat.name.replace(/'/g, "\\'")}" data-amount="${cat.monthly_budget}" value="${cat.monthly_budget.toFixed(2)}"></div>
                        <div class="category-actual text-end pe-2">${formatCurrency(comp.actual)}</div>
                        <div class="category-remaining text-end pe-2"><span class="badge fs-6 ${remainClass}">${formatCurrency(remaining)}</span></div>
                        <div class="category-actions"></div>
                        <div class="progress category-progress">
                            <div class="progress-bar ${barClass}" style="width:${progPct}%"></div>
                        </div>
                    </div>`;
            });

            html += '</div></div>';
        });

        container.html(html);

        container.find('.group-categories').sortable({
            connectWith: '#' + containerId + ' .group-categories',
            update: function(event, ui) {
                saveOrder(containerId);
            },
            receive: function(event, ui) {
                const group = $(this).data('group');
                const catId = ui.item.data('id');
                updateCategoryGroup(catId, group);
            }
        });
    }

    function saveOrder(containerId) {
        const order = [];
        $('#' + containerId + ' .category-item').each(function(i, el) {
            const id = $(el).data('id');
            if (id !== undefined) {
                order.push({id: id, sort_order: order.length});
            }
        });
        $.ajax({
            url: '/api/categories/reorder',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({order: order}),
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Unknown error';
                showToast('Error saving order: ' + error, 'error');
            }
        });
    }

    function editCategory(cat) {
        editingCategory = cat;
        $('#editCategoryName').val(cat.name);
        $('#editCategoryBudget').val(cat.default_budget !== undefined ? cat.default_budget : cat.monthly_budget);
        const groupSelect = $('#editCategoryGroup');
        groupSelect.empty();
        groupSelect.append('<option value="">Other</option>');
        getGroups(cat.type).forEach(g => {
            groupSelect.append(`<option value="${g.name}" ${cat.parent_category === g.name ? 'selected' : ''}>${g.name}</option>`);
        });
        const modal = new bootstrap.Modal(document.getElementById('editCategoryModal'));
        modal.show();
        $('#deleteCategoryBtn').off('click').on('click', function() {
            modal.hide();
            deleteCategory(editingCategory.id);
        });
    }

    function saveCategoryEdits() {
        const name = $('#editCategoryName').val().trim();
        const defaultBudget = parseFloat($('#editCategoryBudget').val());
        const parent = $('#editCategoryGroup').val() || null;
        $.ajax({
            url: `/api/categories/${editingCategory.id}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({name: name, default_budget: defaultBudget, parent_category: parent}),
            success: function(){ showToast('Category updated'); loadBudgetForMonth(); },
            error: function(xhr){ const error = xhr.responseJSON?.error || 'Unknown error'; showToast('Error: '+error,'error'); }
        });
        bootstrap.Modal.getInstance(document.getElementById('editCategoryModal')).hide();
    }
    
    function updateAllDefaults() {
        if (confirm('This will save all current month budgets as the default for future months. Past months will not be affected. Continue?')) {
            // Gather all current month's budgets
            const updates = allCategories.map(cat => ({
                category_id: cat.id,
                amount: cat.monthly_budget
            }));
            
            // Send batch update
            $.ajax({
                url: '/api/categories/update-all-defaults',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ updates: updates }),
                success: function() {
                    showToast('Default budget saved successfully! This will apply to all future months.', 'success');
                },
                error: function(xhr) {
                    const error = xhr.responseJSON?.error || 'Unknown error';
                    showToast('Error saving default budget: ' + error, 'error');
                }
            });
        }
    }
    
    function editBudgetForMonth(categoryId, categoryName, currentAmount) {
        const newAmount = prompt(`Edit budget for ${categoryName} for ${currentMonth}:`, currentAmount);
        if (newAmount === null || newAmount === '' || isNaN(newAmount)) return;
        
        $.ajax({
            url: `/api/budget/${currentMonth}/update`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                category_id: categoryId,
                amount: parseFloat(newAmount)
            }),
            success: function() {
                showToast('Budget updated for this month!');
                loadBudgetForMonth();
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Unknown error';
                showToast('Error updating budget: ' + error, 'error');
            }
        });
    }
    
    function deleteCategory(id) {
        if (confirm('Are you sure you want to delete this category? This will delete the category and all associated transactions.')) {
            $.ajax({
                url: `/api/categories/${id}`,
                method: 'DELETE',
                success: function() {
                    showToast('Category deleted successfully!');
                    loadBudgetForMonth();
                },
                error: function(xhr) {
                    const error = xhr.responseJSON?.error || 'Unknown error';
                    showToast('Error deleting category: ' + error, 'error');
                }
            });
        }
    }
    
    function toggleAddCategoryForm(type) {
        const formType = type === 'deduction' ? 'Deduction' : type.charAt(0).toUpperCase() + type.slice(1);
        const el = document.getElementById('add' + formType + 'Form');
        const collapse = bootstrap.Collapse.getOrCreateInstance(el);
        const isHidden = !el.classList.contains('show');
        collapse.toggle();
        if (isHidden) {
            const input = el.querySelector('input[name="name"]');
            if (input) {
                input.focus();
            }
        }
    }

    function showAddCategoryForm(type) {
        const formType = type === 'deduction' ? 'Deduction' : type.charAt(0).toUpperCase() + type.slice(1);
        const el = document.getElementById('add' + formType + 'Form');
        const collapse = bootstrap.Collapse.getOrCreateInstance(el);
        collapse.show();
        const input = el.querySelector('input[name="name"]');
        if (input) {
            input.focus();
        }
    }

    function hideAddCategoryForm(type) {
        const formType = type === 'deduction' ? 'Deduction' : type.charAt(0).toUpperCase() + type.slice(1);
        const el = document.getElementById('add' + formType + 'Form');
        const collapse = bootstrap.Collapse.getOrCreateInstance(el);
        collapse.hide();
        el.querySelector('form').reset();
    }
    
    function addCategory(event, type) {
        event.preventDefault();
        
        const form = event.target;
        let categoryName = form.name.value;
        let categoryType = type;
        
        // For deductions, we store them as income type but with "Deduction" in the name
        if (type === 'deduction') {
            categoryType = 'income';
            if (!categoryName.toLowerCase().includes('deduction')) {
                categoryName = categoryName + ' Deduction';
            }
        }
        const monthlyBudget = parseFloat(form.monthly_budget.value);

        $.ajax({
            url: `/api/categories`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: categoryName,
                type: categoryType,
                monthly_budget: monthlyBudget,
                is_custom: true
            }),
            success: function () {
                showToast('Category added successfully!');
                loadBudgetForMonth();
                hideAddCategoryForm(type);
            },
            error: function (xhr) {
                const error = xhr.responseJSON?.error || 'Unknown error';
                showToast('Error adding category: ' + error, 'error');
            }
        });
    }

    function addGroup(type) {
        const name = prompt('Group Name');
        if (!name) return;
        $.ajax({
            url: '/api/category-groups',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ name: name, type: type }),
            success: function() {
                showToast('Group added successfully!');
                loadBudgetForMonth();
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Unknown error';
                showToast('Error adding group: ' + error, 'error');
            }
        });
    }

    function editGroup(id, currentName) {
        editingGroupId = id;
        $('#editGroupName').val(currentName);
        const modal = new bootstrap.Modal(document.getElementById('editGroupModal'));
        modal.show();
        $('#deleteGroupBtn').off('click').on('click', function() {
            modal.hide();
            deleteGroup(editingGroupId);
        });
    }

    function saveGroupEdits() {
        const name = $('#editGroupName').val().trim();
        $.ajax({
            url: `/api/category-groups/${editingGroupId}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({ name: name }),
            success: function(){ showToast('Group updated'); loadBudgetForMonth(); },
            error: function(xhr){ const error = xhr.responseJSON?.error || 'Unknown error'; showToast('Error updating group: ' + error, 'error'); }
        });
        bootstrap.Modal.getInstance(document.getElementById('editGroupModal')).hide();
    }

    function deleteGroup(id) {
        if (!confirm('Delete this group? Categories will move to "Other".')) return;
        $.ajax({
            url: `/api/category-groups/${id}`,
            method: 'DELETE',
            success: function(){ showToast('Group deleted'); loadBudgetForMonth(); },
            error: function(xhr){ const error = xhr.responseJSON?.error || 'Unknown error'; showToast('Error deleting group: ' + error, 'error'); }
        });
    }

    function updateCategoryGroup(catId, groupName) {
        const parent = groupName === 'Other' ? null : groupName;
        $.ajax({
            url: `/api/categories/${catId}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({ parent_category: parent }),
            success: function(){ loadCategories(); },
            error: function(xhr){ const error = xhr.responseJSON?.error || 'Unknown error'; showToast('Error moving category: ' + error, 'error'); loadBudgetForMonth(); }
        });
    }
    function updateSummary() {
        let incB=0, incA=0, dedB=0, dedA=0, expB=0, expA=0, fundB=0, fundA=0;
        Object.values(comparisonData).forEach(item => {
            if(item.type==='income') {
                if(item.category.toLowerCase().includes("deduction")) { dedB+=item.budgeted; dedA+=item.actual; }
                else { incB+=item.budgeted; incA+=item.actual; }
            } else if(item.type==='expense') { expB+=item.budgeted; expA+=item.actual; }
            else if(item.type==='fund') { fundB+=item.budgeted; fundA+=item.actual; }
        });
        const totalBudgetExp = expB + fundB + dedB;
        const totalActualExp = expA + fundA + dedA;
        const moneyToBudget = incA - totalActualExp;

        const moneyClass = moneyToBudget > 0 ? 'text-success bg-success-subtle' : moneyToBudget < 0 ? 'text-danger bg-danger-subtle' : 'text-secondary bg-secondary-subtle';
        $('#moneyToBudgetAmount').attr('class', `fs-2 fw-bold px-2 py-1 rounded ${moneyClass}`).text(formatCurrency(moneyToBudget));

        const groupTotals = { income:{}, deduction:{}, expense:{}, fund:{} };
        allCategories.forEach(cat => {
            const comp = comparisonData[cat.name] || {actual:0};
            const group = cat.parent_category || 'Other';
            let bucket;
            if(cat.type === 'income') {
                bucket = cat.name.toLowerCase().includes('deduction') ? 'deduction' : 'income';
            } else if(cat.type === 'fund') { bucket = 'fund'; }
            else { bucket = 'expense'; }
            if(!groupTotals[bucket][group]) groupTotals[bucket][group] = {budget:0, actual:0};
            groupTotals[bucket][group].budget += cat.monthly_budget || 0;
            groupTotals[bucket][group].actual += comp.actual;
        });

        function renderGroups(totals, isIncome) {
            let html = '';
            Object.entries(totals).forEach(([name, tot]) => {
                const remaining = isIncome ? tot.actual - tot.budget : tot.budget - tot.actual;
                const pct = tot.budget ? (tot.actual/tot.budget)*100 : (tot.actual>0?100:0);
                const barClass = isIncome ? (tot.actual >= tot.budget ? 'bg-success' : 'bg-danger') : (tot.actual <= tot.budget ? 'bg-success' : 'bg-danger');
                const remClass = remaining > 0 ? 'text-success bg-success-subtle' : remaining < 0 ? 'text-danger bg-danger-subtle' : 'text-secondary bg-secondary-subtle';
                html += `
                    <div class="mb-2">
                        <div class="d-flex justify-content-between"><span>${name}</span><span>${formatCurrency(tot.budget)}</span></div>
                        <div class="progress"><div class="progress-bar ${barClass}" style="width:${Math.min(pct,100)}%"></div></div>
                        <div class="d-flex justify-content-between mt-1">
                            <span class="fw-bold">${formatCurrency(tot.actual)}</span>
                            <span class="badge fs-6 ${remClass}">${formatCurrency(remaining)}</span>
                        </div>
                    </div>`;
            });
            return html;
        }

        let summaryHtml = '';
        if(Object.keys(groupTotals.income).length) {
            summaryHtml += '<h6>Income</h6>' + renderGroups(groupTotals.income, true);
        }
        if(Object.keys(groupTotals.deduction).length) {
            summaryHtml += '<h6 class="mt-3">Deductions</h6>' + renderGroups(groupTotals.deduction, false);
        }
        const expGroups = { ...groupTotals.expense, ...groupTotals.fund };
        if(Object.keys(expGroups).length) {
            summaryHtml += '<h6 class="mt-3">Expenses</h6>' + renderGroups(expGroups, false);
        }
        $('#summaryContent').html(summaryHtml);

        $('#incomeSummaryContent').html(renderGroups(groupTotals.income, true));
        $('#expenseSummaryContent').html(renderGroups(expGroups, false));

        if (incA > incB) {
            if (!incomeCongratsShown) {
                showToast('Fantastic! You earned more than you budgeted. Consider saving or investing the extra income.', 'success');
                incomeCongratsShown = true;
            }
        } else {
            incomeCongratsShown = false;
        }
    }

    function saveBudget(input) {
        const current = parseFloat(input.data('amount')) || 0;
        const newVal = parseFloat(input.val());
        if (isNaN(newVal)) {
            input.val(current.toFixed(2));
            return;
        }
        if (newVal === current) return;
        $.ajax({
            url: `/api/budget/${currentMonth}/update`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ category_id: input.data('id'), amount: newVal }),
            success: function(){ showToast('Budget updated'); loadBudgetForMonth(); },
            error: function(xhr){ const error = xhr.responseJSON?.error || 'Unknown error'; showToast('Error updating budget: '+error,'error'); loadBudgetForMonth(); }
        });
    }

    $(document).on('keydown', '.editable-budget', function(e){
        if(e.key === 'Enter') { e.preventDefault(); $(this).blur(); }
    });

    $(document).on('blur', '.editable-budget', function(){
        saveBudget($(this));
    });
