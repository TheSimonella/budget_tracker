    let editingFundId = null;
    
    $(document).ready(function() {
        loadFunds();
    });
    
    function loadFunds() {
        $.get('/api/funds', function(funds) {
            const container = $('#fundsContainer');
            
            if (funds.length === 0) {
                container.html(`
                    <div class="col-12">
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle"></i> No funds created yet. Click "Create Fund" to start saving for your goals!
                        </div>
                    </div>
                `);
                return;
            }
            
            let html = '';
            funds.forEach(fund => {
                const progress = (fund.balance / fund.goal * 100).toFixed(1);
                const monthsRemaining = calculateMonthsRemaining(fund.goal_date);
                
                // Use positive color progression
                let progressClass = '';
                if (progress >= 100) progressClass = 'bg-success';
                else if (progress >= 75) progressClass = 'bg-primary';
                else if (progress >= 50) progressClass = 'bg-info';
                else if (progress >= 25) progressClass = 'bg-secondary';
                else progressClass = 'bg-light text-dark';
                
                // Create safe function parameters
                const fundId = fund.id;
                const fundNameEscaped = fund.name.replace(/'/g, "\\'");
                
                html += `
                    <div class="col-lg-6 mb-4">
                        <div class="card fund-card">
                            <div class="card-header">
                                <h5 class="mb-0">${fund.name}</h5>
                            </div>
                            <div class="card-body">
                                <div class="progress mb-3" style="height: 30px;">
                                    <div class="progress-bar ${progressClass}" style="width: ${Math.min(progress, 100)}%">
                                        ${progress}%
                                    </div>
                                </div>
                                
                                <div class="fund-stats">
                                    <div class="fund-stat">
                                        <div class="fund-stat-value">${formatCurrency(fund.balance)}</div>
                                        <div class="fund-stat-label">Current Balance</div>
                                    </div>
                                    <div class="fund-stat">
                                        <div class="fund-stat-value">${formatCurrency(fund.goal)}</div>
                                        <div class="fund-stat-label">Goal Amount</div>
                                    </div>
                                    <div class="fund-stat">
                                        <div class="fund-stat-value">${monthsRemaining}</div>
                                        <div class="fund-stat-label">Months Left</div>
                                    </div>
                                </div>
                                
                                ${fund.goal_date ? `
                                    <div class="recommendation-box">
                                        <h6><i class="fas fa-lightbulb"></i> Fund Details</h6>
                                        <p class="mb-1">Target Date: ${new Date(fund.goal_date).toLocaleDateString()}</p>
                                        <p class="mb-1">Recommended monthly: ${formatCurrency(fund.recommended_contribution)}</p>
                                        ${fund.monthly_contribution > 0 ? 
                                            `<p class="mb-0"><strong>Budget contribution: ${formatCurrency(fund.monthly_contribution)}/month</strong></p>` : 
                                            '<p class="mb-0 text-muted">No monthly contribution set in budget</p>'
                                        }
                                    </div>
                                ` : ''}
                                
                                <div class="mt-3">
                                    <button class="btn btn-sm btn-outline-primary" onclick="editFund(${fundId})">
                                        <i class="fas fa-edit"></i> Edit
                                    </button>
                                    <button class="btn btn-sm btn-outline-primary" onclick="withdrawFrom(${fundId}, '${fundNameEscaped}')">
                                        <i class="fas fa-minus"></i> Withdraw
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteFund(${fundId}, '${fundNameEscaped}')">
                                        <i class="fas fa-trash"></i> Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            container.html(html);
        });
    }
    
    function calculateMonthsRemaining(goalDate) {
        if (!goalDate) return 'N/A';
        
        const now = new Date();
        const goal = new Date(goalDate);
        const months = (goal.getFullYear() - now.getFullYear()) * 12 + (goal.getMonth() - now.getMonth());
        
        return months > 0 ? months : 0;
    }

    function toggleAddFundForm(show) {
        const el = document.getElementById('addFundModal');
        const collapse = bootstrap.Collapse.getOrCreateInstance(el);
        if (show === true) collapse.show();
        else if (show === false) collapse.hide();
        else collapse.toggle();
    }
    
    function saveFund() {
        const formData = $('#addFundForm').serializeArray();
        const data = {};
        formData.forEach(field => {
            data[field.name] = field.value;
        });
        
        $.ajax({
            url: '/api/funds',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function() {
                toggleAddFundForm(false);
                $('#addFundForm')[0].reset();
                showToast('Fund created successfully! Check your budget to see the monthly contribution.', 'success');
                loadFunds();
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Unknown error';
                showToast('Error creating fund: ' + error, 'error');
            }
        });
    }
    
    function editFund(fundId) {
        editingFundId = fundId;
        
        // Load fund data
        $.get(`/api/funds/${fundId}`, function(data) {
            $('#editFundForm input[name="id"]').val(data.id);
            $('#editFundForm input[name="name"]').val(data.name);
            $('#editFundForm input[name="goal_amount"]').val(data.goal);
            $('#editFundForm input[name="goal_date"]').val(data.goal_date);
            $('#editFundForm input[name="monthly_contribution"]').val(data.monthly_contribution);
            
            $('#editFundModal').modal('show');
        }).fail(function() {
            showToast('Error loading fund data', 'error');
        });
    }
    
    function updateFund() {
        const formData = $('#editFundForm').serializeArray();
        const data = {};
        formData.forEach(field => {
            data[field.name] = field.value;
        });
        
        $.ajax({
            url: `/api/funds/${editingFundId}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function() {
                $('#editFundModal').modal('hide');
                showToast('Fund updated successfully!', 'success');
                loadFunds();
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.error || 'Unknown error';
                showToast('Error updating fund: ' + error, 'error');
            }
        });
    }
    
    function deleteFund(fundId, fundName) {
        if (confirm(`Are you sure you want to delete "${fundName}"? This will also remove it from your budget and delete all related transactions.`)) {
            $.ajax({
                url: `/api/funds/${fundId}`,
                method: 'DELETE',
                success: function() {
                    showToast('Fund deleted successfully!', 'success');
                    loadFunds();
                },
                error: function(xhr) {
                    const error = xhr.responseJSON?.error || 'Unknown error';
                    showToast('Error deleting fund: ' + error, 'error');
                }
            });
        }
    }
    
    function withdrawFrom(fundId, fundName) {
        const amount = prompt(`How much would you like to withdraw from ${fundName}?`);
        if (amount && !isNaN(amount) && parseFloat(amount) > 0) {
            $.ajax({
                url: `/api/funds/${fundId}/withdraw`,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ amount: parseFloat(amount) }),
                success: function(response) {
                    showToast(`Successfully withdrew ${formatCurrency(parseFloat(amount))} from ${fundName}!`, 'success');
                    loadFunds();
                },
                error: function(xhr) {
                    const error = xhr.responseJSON?.error || 'Unknown error';
                    showToast('Error making withdrawal: ' + error, 'error');
                }
            });
        }
    }

    function refreshFunds() {
        $.post('/api/funds/refresh', function() {
            showToast('Funds refreshed successfully!', 'success');
            loadFunds();
        }).fail(function(xhr) {
            const error = xhr.responseJSON?.error || 'Unknown error';
            showToast('Error refreshing funds: ' + error, 'error');
        });
    }
