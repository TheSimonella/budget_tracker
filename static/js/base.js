// Format currency
function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
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

  toastElement.on('hidden.bs.toast', function () {
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
