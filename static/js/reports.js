    let annualChart = null;
    let categoryChart = null;

    function showReport(reportType) {
        $('#reportDisplay').show();
        $('#reportContent').html('<div class="text-center"><div class="spinner-border text-primary" role="status"></div><p>Loading report...</p></div>');
        
        // Scroll to report
        $('html, body').animate({
            scrollTop: $('#reportDisplay').offset().top - 100
        }, 500);
        
        if (reportType === 'monthly-summary') {
            const currentMonth = new Date().toISOString().slice(0, 7);
            const monthSelector = `
                <div class="mb-4">
                    <label>Select Month:</label>
                    <input type="month" class="form-control" style="width: 200px; display: inline-block; margin-left: 10px;" 
                           id="reportMonth" value="${currentMonth}" onchange="loadMonthlySummary()">
                </div>
            `;
            
            $('#reportContent').html(`
                <h3>Monthly Summary Report</h3>
                ${monthSelector}
                <div id="monthlySummaryContent"></div>
            `);
            
            loadMonthlySummary();
        } else if (reportType === 'annual-overview') {
            loadAnnualOverview();
        } else if (reportType === 'category-analysis') {
            loadCategoryAnalysis();
        } else if (reportType === 'spending-trends') {
            loadSpendingTrends();
        } else if (reportType === 'fund-progress') {
            loadFundProgress();
        }
    }
    
    function loadMonthlySummary() {
        const selectedMonth = $('#reportMonth').val();
        
        $.get(`/api/reports/monthly-summary/${selectedMonth}`, function(data) {
            let incomeHtml = '<h5>Income Breakdown</h5><table class="table table-sm"><tbody>';
            
            for (const [category, amount] of Object.entries(data.income_breakdown)) {
                incomeHtml += `<tr><td>${category}</td><td class="text-end">${formatCurrency(amount)}</td></tr>`;
            }
            incomeHtml += `<tr class="fw-bold"><td>Total Gross Income</td><td class="text-end">${formatCurrency(data.gross_income)}</td></tr>`;
            incomeHtml += `<tr class="text-danger"><td>Total Deductions</td><td class="text-end">-${formatCurrency(data.deductions)}</td></tr>`;
            incomeHtml += `<tr class="fw-bold table-primary"><td>Net Income</td><td class="text-end">${formatCurrency(data.net_income)}</td></tr>`;
            incomeHtml += '</tbody></table>';
            
            let expenseHtml = '<h5 class="mt-4">Expense Breakdown</h5><table class="table table-sm"><tbody>';
            for (const [category, amount] of Object.entries(data.expense_breakdown)) {
                expenseHtml += `<tr><td>${category}</td><td class="text-end">${formatCurrency(amount)}</td></tr>`;
            }
            expenseHtml += `<tr class="fw-bold table-danger"><td>Total Expenses</td><td class="text-end">${formatCurrency(data.total_expenses)}</td></tr>`;
            expenseHtml += '</tbody></table>';
            
            const summaryHtml = `
                <div class="row mt-4">
                    <div class="col-md-6">
                        ${incomeHtml}
                        ${expenseHtml}
                    </div>
                    <div class="col-md-6">
                        <h5>Summary</h5>
                        <div class="card">
                            <div class="card-body">
                                <div class="d-flex justify-content-between mb-2">
                                    <span>Net Income:</span>
                                    <strong class="text-primary">${formatCurrency(data.net_income)}</strong>
                                </div>
                                <div class="d-flex justify-content-between mb-2">
                                    <span>Total Expenses:</span>
                                    <strong class="text-danger">-${formatCurrency(data.total_expenses)}</strong>
                                </div>
                                <hr>
                                <div class="d-flex justify-content-between mb-2">
                                    <span>Monthly Savings:</span>
                                    <strong class="${data.savings >= 0 ? 'text-success' : 'text-danger'}">${formatCurrency(data.savings)}</strong>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <span>Savings Rate:</span>
                                    <strong class="${data.savings_rate >= 20 ? 'text-success' : data.savings_rate >= 10 ? 'text-warning' : 'text-danger'}">
                                        ${data.savings_rate.toFixed(1)}%
                                    </strong>
                                </div>
                            </div>
                        </div>
                        
                        <div class="alert ${data.savings_rate >= 20 ? 'alert-success' : data.savings_rate >= 10 ? 'alert-warning' : 'alert-danger'} mt-3">
                            <h6>Savings Analysis</h6>
                            ${data.savings_rate >= 20 ? 
                                `Great job! You're saving ${data.savings_rate.toFixed(1)}% of your income. Keep it up!` :
                                data.savings_rate >= 10 ?
                                `You're saving ${data.savings_rate.toFixed(1)}% of your income. Consider increasing this to 20% or more for better financial security.` :
                                `Your savings rate is only ${data.savings_rate.toFixed(1)}%. Try to reduce expenses or increase income to improve your financial health.`
                            }
                        </div>
                    </div>
                </div>
            `;
            
            $('#monthlySummaryContent').html(summaryHtml);
        }).fail(function() {
            $('#monthlySummaryContent').html('<div class="alert alert-warning">No data available for the selected month.</div>');
        });
    }
    
    function loadAnnualOverview() {
        const currentYear = new Date().getFullYear();
        $.get(`/api/reports/annual-overview/${currentYear}`, function(data) {
            let monthlyTrendHtml = '<h5>Monthly Trends</h5><canvas id="monthlyTrendChart" width="400" height="200"></canvas>';
            
            let summaryHtml = `
                <h3>Annual Overview - ${currentYear}</h3>
                <div class="row mt-4">
                    <div class="col-md-4">
                        <div class="card text-center">
                            <div class="card-body">
                                <h6>Total Income (YTD)</h6>
                                <h3 class="text-primary">${formatCurrency(data.total_income)}</h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card text-center">
                            <div class="card-body">
                                <h6>Total Expenses (YTD)</h6>
                                <h3 class="text-danger">${formatCurrency(data.total_expenses)}</h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card text-center">
                            <div class="card-body">
                                <h6>Total Saved (YTD)</h6>
                                <h3 class="text-success">${formatCurrency(data.total_saved)}</h3>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="mt-4">
                    ${monthlyTrendHtml}
                </div>
            `;
            
            $('#reportContent').html(summaryHtml);
            
            // Create the trend chart
            const ctx = document.getElementById('monthlyTrendChart').getContext('2d');
            if (annualChart) {
                annualChart.destroy();
            }
            annualChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.months,
                    datasets: [{
                        label: 'Income',
                        data: data.monthly_income,
                        borderColor: 'rgb(67, 97, 238)',
                        backgroundColor: 'rgba(67, 97, 238, 0.1)',
                        tension: 0.1
                    }, {
                        label: 'Expenses',
                        data: data.monthly_expenses,
                        borderColor: 'rgb(214, 40, 40)',
                        backgroundColor: 'rgba(214, 40, 40, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toLocaleString();
                                }
                            }
                        }
                    }
                }
            });
        }).fail(function() {
            $('#reportContent').html('<div class="alert alert-warning">No data available for the current year.</div>');
        });
    }
    
    function loadCategoryAnalysis() {
        const currentMonth = new Date().toISOString().slice(0, 7);
        $.get(`/api/reports/category-analysis/${currentMonth}`, function(data) {
            let chartHtml = `
                <h3>Category Analysis</h3>
                <div class="mb-4">
                    <label>Select Month:</label>
                    <input type="month" class="form-control" style="width: 200px; display: inline-block; margin-left: 10px;" 
                           id="categoryMonth" value="${currentMonth}" onchange="loadCategoryAnalysis()">
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <h5>Expense Distribution</h5>
                        <canvas id="categoryPieChart" width="300" height="300"></canvas>
                    </div>
                    <div class="col-md-6">
                        <h5>Top Categories</h5>
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Category</th>
                                    <th>Amount</th>
                                    <th>% of Total</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            data.categories.forEach(cat => {
                chartHtml += `
                    <tr>
                        <td>${cat.name}</td>
                        <td>${formatCurrency(cat.amount)}</td>
                        <td>${cat.percentage.toFixed(1)}%</td>
                    </tr>
                `;
            });
            
            chartHtml += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
            
            $('#reportContent').html(chartHtml);
            
            // Create pie chart
            const ctx = document.getElementById('categoryPieChart').getContext('2d');
            if (categoryChart) {
                categoryChart.destroy();
            }
            categoryChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: data.categories.map(c => c.name),
                    datasets: [{
                        data: data.categories.map(c => c.amount),
                        backgroundColor: [
                            '#4361ee', '#f77f00', '#2a9d8f', '#d62828',
                            '#e76f51', '#264653', '#e9c46a', '#457b9d'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.label + ': ' + formatCurrency(context.parsed);
                                }
                            }
                        }
                    }
                }
            });
        });
    }
    
    function loadSpendingTrends() {
        $.get('/api/reports/spending-trends', function(data) {
            let chartHtml = `
                <h3>Spending Trends - Last 6 Months</h3>
                <div class="mt-4">
                    <canvas id="spendingTrendChart" width="400" height="200"></canvas>
                </div>
                <div class="row mt-4">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h6>Average Monthly Spending</h6>
                                <h4>${formatCurrency(data.average_spending)}</h4>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h6>Highest Month</h6>
                                <h4>${data.highest_month}: ${formatCurrency(data.highest_amount)}</h4>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h6>Trend</h6>
                                <h4 class="${data.trend === 'increasing' ? 'text-danger' : 'text-success'}">
                                    ${data.trend === 'increasing' ? '↑' : '↓'} ${data.trend}
                                </h4>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            $('#reportContent').html(chartHtml);
            
            // Create trend chart
            const ctx = document.getElementById('spendingTrendChart').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.months,
                    datasets: [{
                        label: 'Total Expenses',
                        data: data.expenses,
                        backgroundColor: 'rgba(214, 40, 40, 0.6)',
                        borderColor: 'rgb(214, 40, 40)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toLocaleString();
                                }
                            }
                        }
                    }
                }
            });
        });
    }
    
    function loadFundProgress() {
        $.get('/api/reports/fund-progress', function(data) {
            let fundsHtml = `
                <h3>Fund Progress Report</h3>
                <div class="row mt-4">
            `;
            
            data.funds.forEach(fund => {
                const progressClass = fund.progress >= 100 ? 'bg-success' : 
                                    fund.progress >= 75 ? 'bg-info' : 
                                    fund.progress >= 50 ? 'bg-warning' : 'bg-danger';
                
                fundsHtml += `
                    <div class="col-md-6 mb-4">
                        <div class="card">
                            <div class="card-body">
                                <h5>${fund.name}</h5>
                                <div class="progress mb-3" style="height: 25px;">
                                    <div class="progress-bar ${progressClass}" style="width: ${Math.min(fund.progress, 100)}%">
                                        ${fund.progress.toFixed(1)}%
                                    </div>
                                </div>
                                <div class="row">
                                    <div class="col-6">
                                        <small class="text-muted">Current</small>
                                        <h6>${formatCurrency(fund.balance)}</h6>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Goal</small>
                                        <h6>${formatCurrency(fund.goal)}</h6>
                                    </div>
                                </div>
                                ${fund.goal_date ? `
                                    <p class="mb-0 mt-2">
                                        <small class="text-muted">Target Date: ${new Date(fund.goal_date).toLocaleDateString()}</small><br>
                                        <small>Recommended monthly: ${formatCurrency(fund.recommended_contribution)}</small>
                                    </p>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });
            
            fundsHtml += '</div>';
            $('#reportContent').html(fundsHtml);
        });
    }
    
    function showExportOptions() {
        $('#exportModal').modal('show');
    }
    
    function exportData(format) {
        $('#exportModal').modal('hide');
        
        if (format === 'csv') {
            window.location.href = '/api/export/csv';
            showToast('Downloading CSV file...', 'success');
        } else if (format === 'json') {
            window.location.href = '/api/export/json';
            showToast('Downloading JSON file...', 'success');
        }
    }
