    let currentPeriod = 'monthly';
    let categories = [];
    let currentMonth = localStorage.getItem('selectedMonth') || new Date().toISOString().slice(0, 7);
    localStorage.setItem('selectedMonth', currentMonth);
    let currentYear = parseInt(currentMonth.split('-')[0]);
    
    // Load dashboard data on page load
    $(document).ready(function() {
        // Set current selectors
        $('#monthSelector').val(currentMonth);
        $('#yearSelector').val(currentYear);

        loadDashboardData();
        loadCategories();
        loadSankeyData('monthly');
        
        // Set today's date as default
        $('input[name="date"]').val(new Date().toISOString().split('T')[0]);
        
        // Update categories when transaction type changes
        $('select[name="transaction_type"]').change(function() {
            updateCategoryDropdown($(this).val());
        });
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

        loadDashboardForMonth();
    }
    
    function loadDashboardForMonth() {
        currentMonth = $('#monthSelector').val();
        localStorage.setItem('selectedMonth', currentMonth);
        loadDashboardData();
        loadSankeyData(currentPeriod);
    }
    
    function loadDashboardData() {
        $.get(`/api/dashboard-data/${currentMonth}`, function(data) {
            // Update summary values
            $('#netIncome').text(formatCurrency(data.net_income));
            $('#totalExpenses').text(formatCurrency(data.total_expenses));
            
            const leftToBudget = data.net_income - data.total_expenses - data.total_savings;
            $('#leftToBudget').text(formatCurrency(leftToBudget));
            
            const savingsRate = data.net_income > 0 ? ((data.total_savings / data.net_income) * 100).toFixed(0) : 0;
            $('#savingsRate').text(savingsRate + '%');
            
            // Load other components
            loadFundsProgress(data.funds);
            loadRecentTransactions(data.recent_transactions);
            loadBudgetStatus();
        });
    }

    function changeYear(direction) {
        currentYear += direction;
        $('#yearSelector').val(currentYear);
        loadDashboardForYear();
    }

    function loadDashboardForYear() {
        currentYear = parseInt($('#yearSelector').val());
        loadSankeyData('annual');
    }

    function loadDashboardDataYear() {
        $.get(`/api/dashboard-data/annual/${currentYear}`, function(data) {
            $('#netIncome').text(formatCurrency(data.net_income));
            $('#totalExpenses').text(formatCurrency(data.total_expenses));

            const leftToBudget = data.net_income - data.total_expenses - data.total_savings;
            $('#leftToBudget').text(formatCurrency(leftToBudget));

            const savingsRate = data.net_income > 0 ? ((data.total_savings / data.net_income) * 100).toFixed(0) : 0;
            $('#savingsRate').text(savingsRate + '%');

            loadFundsProgress(data.funds);
            loadRecentTransactions(data.recent_transactions);
            loadBudgetStatus();
        });
    }
    
    function loadCategories() {
        $.get('/api/categories', function(data) {
            categories = data;
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
            // Group expenses by parent category
            const expensesByParent = {};
            categories.filter(c => c.type === 'expense').forEach(cat => {
                const parent = cat.parent_category || 'Other';
                if (!expensesByParent[parent]) expensesByParent[parent] = [];
                expensesByParent[parent].push(cat);
            });
            
            Object.keys(expensesByParent).sort().forEach(parent => {
                select.append(`<optgroup label="${parent}">`);
                expensesByParent[parent].forEach(cat => {
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
    
    function loadFundsProgress(funds) {
        if (funds.length === 0) {
            $('#fundsProgress').html('<div class="p-3 text-center text-muted">No savings goals yet</div>');
            return;
        }
        
        let html = '';
        funds.forEach((fund, index) => {
            if (index < 3) { // Show only first 3 funds
                const progress = Math.min(fund.progress, 100);
                let progressClass = 'progress-positive-0';
                
                if (progress >= 100) progressClass = 'progress-positive-100';
                else if (progress >= 75) progressClass = 'progress-positive-75';
                else if (progress >= 50) progressClass = 'progress-positive-50';
                else if (progress >= 25) progressClass = 'progress-positive-25';
                
                html += `
                    <div class="fund-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="fund-name">${fund.name}</div>
                            <div class="fund-amount">${formatCurrency(fund.balance)}</div>
                        </div>
                        <div class="progress" style="height: 16px;">
                            <div class="progress-bar ${progressClass}" style="width: ${progress}%">
                                ${fund.progress.toFixed(0)}%
                            </div>
                        </div>
                    </div>
                `;
            }
        });
        
        if (funds.length > 3) {
            html += `<div class="text-center p-2"><small class="text-muted">+${funds.length - 3} more goals</small></div>`;
        }
        
        $('#fundsProgress').html(html);
    }
    
    function loadRecentTransactions(transactions) {
        if (transactions.length === 0) {
            $('#recentTransactions').html('<div class="p-3 text-center text-muted">No recent transactions</div>');
            return;
        }
        
        let html = '<div class="p-2">';
        transactions.slice(0, 5).forEach(trans => {
            const amountClass = trans.type === 'expense' || trans.type === 'fund_withdrawal' ? 'text-danger' : 'text-success';
            const sign = trans.type === 'expense' || trans.type === 'fund_withdrawal' ? '-' : '+';
            
            html += `
                <div class="transaction-item">
                    <div class="transaction-details">
                        <div style="font-weight: 500;">${trans.description}</div>
                        <div style="font-size: 0.75rem; color: #6c757d;">
                            ${trans.category} • ${new Date(trans.date).toLocaleDateString()}
                        </div>
                    </div>
                    <div class="transaction-amount ${amountClass}">
                        ${sign}${formatCurrency(Math.abs(trans.amount))}
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        $('#recentTransactions').html(html);
    }
    
    function loadBudgetStatus() {
        $.get(`/api/budget-comparison/${currentMonth}`, function(data) {
            const overBudget = data.filter(item => item.type === 'expense' && item.status === 'over');
            const underBudget = data.filter(item => item.type === 'expense' && item.status === 'under');
            
            let html = '<div style="font-size: 0.813rem;">';
            
            if (overBudget.length > 0) {
                html += '<div class="mb-2"><strong class="text-danger">Over Budget:</strong></div>';
                overBudget.slice(0, 3).forEach(item => {
                    const overAmount = item.actual - item.budgeted;
                    html += `<div class="ms-2 mb-1">${item.category}: <span class="text-danger">+${formatCurrency(overAmount)}</span></div>`;
                });
            }
            
            html += `<div class="mt-2 text-center"><strong>${underBudget.length}</strong> categories within budget</div>`;
            html += '</div>';
            
            $('#budgetStatus').html(html);
        });
    }
    
    function saveTransaction() {
        const formData = $('#addTransactionForm').serializeArray();
        const data = {};
        formData.forEach(field => {
            data[field.name] = field.value;
        });
        
        $.ajax({
            url: '/api/transactions',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function() {
                $('#addTransactionModal').modal('hide');
                $('#addTransactionForm')[0].reset();
                showToast('Transaction added successfully!');
                loadSankeyData(currentPeriod);
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Unknown error';
                showToast('Error: ' + error, 'error');
            }
        });
    }
    
    function loadSankeyData(period) {
        currentPeriod = period;

        // Update button states
        $('#periodToggle button').removeClass('active');
        if (period === 'monthly') {
            $('#periodToggle button:first').addClass('active');
            $('#monthNav').removeClass('d-none');
            $('#yearNav').addClass('d-none');
            loadDashboardData();
        } else {
            $('#periodToggle button:last').addClass('active');
            $('#yearNav').removeClass('d-none');
            $('#monthNav').addClass('d-none');
            loadDashboardDataYear();
        }

        const url = period === 'monthly'
            ? `/api/sankey-data/${period}/${currentMonth}`
            : `/api/sankey-data/${period}/${currentYear}-01`;

        $.get(url, function(data) {
            drawSankey(data);
        });
    }
    
    function drawSankey(data) {
        // Clear previous diagram
        d3.select("#sankeyDiagram").selectAll("*").remove();
        
        if (!data.nodes || data.nodes.length === 0 || !data.links || data.links.length === 0) {
            d3.select("#sankeyDiagram")
                .append("div")
                .attr("class", "text-center text-muted")
                .style("padding", "80px 20px")
                .html('<i class="fas fa-chart-line fa-3x mb-3"></i><br>No transaction data available.<br>Add income and expense transactions to see your cash flow.');
            return;
        }
        
        const margin = {top: 10, right: 10, bottom: 10, left: 10};
        const width = $("#sankeyDiagram").width() - margin.left - margin.right;
        const height = 330 - margin.top - margin.bottom;
        
        const svg = d3.select("#sankeyDiagram")
            .append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);
        
        const sankey = d3.sankey()
            .nodeWidth(15)
            .nodePadding(10)
            .extent([[0, 0], [width, height]]);
        
        const {nodes, links} = sankey(data);

        // Determine node type for coloring
        function getNodeType(node) {
            if (node.type) return node.type;
            const name = node.name || node;
            if (name === 'Income') return 'income';
            if (name === 'Deductions') return 'deduction';
            if (name === 'Expenses') return 'expense';
            if (name === 'Savings') return 'fund';
            if (name === 'Budget') return 'budget';
            return 'other';
        }
        
        // Add links
        svg.append("g")
            .selectAll("path")
            .data(links)
            .join("path")
            .attr("d", d3.sankeyLinkHorizontal())
            .attr("stroke", d => {
                const targetType = getNodeType(d.target);
                if (targetType === "deduction") return "#f77f00";
                if (targetType === "expense") return "#dc3545";
                if (targetType === "fund") return "#2a9d8f";
                return "#4361ee";
            })
            .attr("stroke-width", d => Math.max(1, d.width))
            .attr("fill", "none")
            .attr("opacity", 0.5);
        
        // Add nodes
        const node = svg.append("g")
            .selectAll("g")
            .data(nodes)
            .join("g");
        
        node.append("rect")
            .attr("x", d => d.x0)
            .attr("y", d => d.y0)
            .attr("height", d => d.y1 - d.y0)
            .attr("width", d => d.x1 - d.x0)
            .attr("fill", d => {
                const type = getNodeType(d);
                if (type === "income") return "#4361ee";
                if (type === "deduction") return "#f77f00";
                if (type === "expense") return "#dc3545";
                if (type === "fund") return "#2a9d8f";
                if (type === "budget") return "#6c757d";
                return "#999";
            });
        
        node.append("text")
            .attr("x", d => d.x0 - 6)
            .attr("y", d => (d.y1 + d.y0) / 2)
            .attr("dy", "0.35em")
            .attr("text-anchor", "end")
            .text(d => d.name)
            .style("font-size", "12px")
            .filter(d => d.x0 < width / 2)
            .attr("x", d => d.x1 + 6)
            .attr("text-anchor", "start");
    }
