    let currentMonth = localStorage.getItem('selectedMonth') || new Date().toISOString().slice(0, 7);
    localStorage.setItem('selectedMonth', currentMonth);
    let allCategories = [];
    let comparisonData = {};

    let categoryGroups = [];
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
            updateSummary();
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
        Object.keys(groups).sort().forEach(g => {
            const gData = groups[g];
            const safeId = g.replace(/\s+/g, "-");
            const total = gData.cats.reduce((sum, c) => sum + (c.monthly_budget || 0), 0);
            html += `<div class="mb-3 category-group" data-group-id="${gData.id || ''}">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">${g} <span class="badge bg-secondary group-total d-none" id="total-${containerId}-${safeId}">${formatCurrency(total)}</span></h6>
                            <div>
                                <button class="btn btn-sm btn-outline-secondary group-toggle" data-bs-toggle="collapse" data-bs-target="#grp-${containerId}-${safeId}">
                                    <i class="fas fa-caret-down"></i>
                                </button>
                                ${gData.id ? `<div class="dropdown d-inline ms-1">
                                    <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="dropdown"><i class="fas fa-ellipsis-v"></i></button>
                                    <ul class="dropdown-menu">
                                        <li><a class="dropdown-item" href="#" onclick="editGroup(${gData.id}, '${g.replace(/'/g, "\\'")}')">Edit Group</a></li>
                                        <li><hr class="dropdown-divider"></li>
                                        <li><a class="dropdown-item text-danger" href="#" onclick="deleteGroup(${gData.id})">Delete Group</a></li>
                                    </ul>
                                </div>` : ''}
                            </div>
                        </div>
                        <div id="grp-${containerId}-${safeId}" class="mt-2 collapse show group-categories" data-group="${g}">`;

            gData.cats.sort((a,b)=>a.sort_order-b.sort_order).forEach(cat => {
                const comp = comparisonData[cat.name] || {actual:0};
                const remaining = cat.monthly_budget - comp.actual;
                const pct = cat.monthly_budget ? (comp.actual / cat.monthly_budget) * 100 : (comp.actual > 0 ? 100 : 0);
                const progPct = Math.min(pct, 100);
                const barClass = comp.actual <= cat.monthly_budget ? 'bg-success' : 'bg-danger';
                html += `
                    <div class="category-item" data-id="${cat.id}">
                        <div class="category-info">
                            <h6 class="mb-1">${cat.name}</h6>
                            <div class="progress category-progress">
                                <div class="progress-bar ${barClass}" style="width:${progPct}%"></div>
                            </div>
                        </div>
                        <div class="category-budget"><input type="number" step="0.01" class="editable-budget" data-id="${cat.id}" data-name="${cat.name.replace(/'/g, "\\'")}" data-amount="${cat.monthly_budget}" value="${cat.monthly_budget.toFixed(2)}"></div>
                        <div class="category-actual">${formatCurrency(comp.actual)}</div>
                        <div class="category-remaining">${formatCurrency(remaining)}</div>
                        <div class="dropdown ms-2">
                            <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="dropdown"><i class="fas fa-ellipsis-v"></i></button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item" href="#" onclick='editCategory(${JSON.stringify(cat)})'>Edit Category</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item text-danger" href="#" onclick="deleteCategory(${cat.id})">Delete</a></li>
                            </ul>
                        </div>
                    </div>`;
            });

            html += '</div></div>';
        });

        container.html(html);

        Object.keys(groups).forEach(g => {
            const safeId = g.replace(/\s+/g, '-');
            const collapseId = `#grp-${containerId}-${safeId}`;
            $(collapseId).on('hide.bs.collapse', function(){
                $(`#total-${containerId}-${safeId}`).removeClass('d-none');
            });
            $(collapseId).on('show.bs.collapse', function(){
                $(`#total-${containerId}-${safeId}`).addClass('d-none');
            });
        });

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
            order.push({id: $(el).data('id'), sort_order: i});
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
        const newName = prompt('Category Name', cat.name);
        if (newName === null) return;
        const newBudget = prompt('Default Monthly Budget', cat.default_budget);
        if (newBudget === null || isNaN(newBudget)) return;
        const newGroup = prompt('Group', cat.parent_category || '');
        $.ajax({
            url: `/api/categories/${cat.id}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({name:newName, default_budget:parseFloat(newBudget), parent_category:newGroup}),
            success: function(){ showToast('Category updated'); loadBudgetForMonth(); },
            error: function(xhr){ const error = xhr.responseJSON?.error || 'Unknown error'; showToast('Error: '+error,'error'); }
        });
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
        collapse.toggle();
    }

    function showAddCategoryForm(type) {
        const formType = type === 'deduction' ? 'Deduction' : type.charAt(0).toUpperCase() + type.slice(1);
        const el = document.getElementById('add' + formType + 'Form');
        const collapse = bootstrap.Collapse.getOrCreateInstance(el);
        collapse.show();
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
        const newName = prompt('Group Name', currentName);
        if (!newName) return;
        $.ajax({
            url: `/api/category-groups/${id}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({ name: newName }),
            success: function(){ showToast('Group updated'); loadBudgetForMonth(); },
            error: function(xhr){ const error = xhr.responseJSON?.error || 'Unknown error'; showToast('Error updating group: ' + error, 'error'); }
        });
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
        $('#summaryContent').html(`<p class="fs-4 text-center">${formatCurrency(moneyToBudget)}</p>`);
        const incPercent = incB ? incA / incB * 100 : 0;
        const expPercent = totalBudgetExp ? totalActualExp / totalBudgetExp * 100 : 0;
        const expClass = expPercent <= 100 ? "bg-success" : "bg-danger";
        $('#incomeSummaryContent').html(`
            <p>Earned ${formatCurrency(incA)} of ${formatCurrency(incB)}</p>
            <div class="progress"><div class="progress-bar bg-success" style="width:${Math.min(incPercent,100)}%">${incPercent.toFixed(0)}%</div></div>
            ${incPercent>100?'<div class="mt-2 text-success">Great job exceeding your goal!</div>':''}
        `);
        $('#expenseSummaryContent').html(`
            <p>Spent ${formatCurrency(totalActualExp)} of ${formatCurrency(totalBudgetExp)}</p>
            <div class="progress"><div class="progress-bar ${expClass}" style="width:${Math.min(expPercent,100)}%">${expPercent.toFixed(0)}%</div></div>
        `);
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
