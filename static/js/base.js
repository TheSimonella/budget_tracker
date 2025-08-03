document.addEventListener('DOMContentLoaded', () => {
  const root = document.documentElement;
  const btn = document.getElementById('theme-toggle');

  function applyTheme(theme) {
    root.dataset.theme = theme;
    if (btn) {
      btn.innerHTML = theme === 'dark' ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    }
  }

  const stored = localStorage.getItem('theme');
  if (stored) {
    applyTheme(stored);
  } else {
    localStorage.setItem('theme', 'light');
    applyTheme('light');
  }

  if (btn) {
    btn.addEventListener('click', () => {
      const newTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('theme', newTheme);
      applyTheme(newTheme);
    });
  }
});
        // Format currency
        function formatCurrency(amount) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount);
        }
        
        // Show toast notification
        function showToast(message, type = 'success') {
            const toastHtml = `
                <div class="toast position-fixed bottom-0 end-0 m-3" role="alert">
                    <div class="toast-header bg-${type === 'success' ? 'success' : 'danger'} text-white">
                        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>
                        <strong class="me-auto">${type === 'success' ? 'Success' : 'Error'}</strong>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                    </div>
                    <div class="toast-body">
                        ${message}
                    </div>
                </div>
            `;
            
            const toastElement = $(toastHtml);
            $('body').append(toastElement);
            const toast = new bootstrap.Toast(toastElement[0]);
            toast.show();
            
            toastElement.on('hidden.bs.toast', function() {
                $(this).remove();
            });
        }
        
        // Add loading state to buttons
        function setButtonLoading(button, loading) {
            if (loading) {
                button.prop('disabled', true);
                button.data('original-text', button.html());
                button.html('<span class="spinner-border spinner-border-sm me-2" role="status"></span>Loading...');
            } else {
                button.prop('disabled', false);
                button.html(button.data('original-text'));
            }
        }
