/**
 * Cart functionality for Angel's Plants
 * Handles add to cart, update quantity, and cart interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Add to cart functionality
    document.addEventListener('click', function(e) {
        // Handle add to cart button clicks
        if (e.target.closest('.add-to-cart')) {
            e.preventDefault();
            const button = e.target.closest('.add-to-cart');
            addToCart(button);
        }
        
        // Handle quantity input changes
        if (e.target.closest('.quantity-input')) {
            const input = e.target.closest('.quantity-input');
            updateQuantity(input);
        }
    });
    
    // Initialize cart count on page load
    updateCartCount();
});

/**
 * Add a product to the cart
 * @param {HTMLElement} button - The add to cart button that was clicked
 */
async function addToCart(button) {
    const productId = button.dataset.productId;
    const quantity = button.dataset.quantity || 1;
    const url = `/store/cart/add/${productId}/`;
    
    // Show loading state
    const originalHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...';
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFTTOKEN': getCookie('csrftoken')
            },
            body: JSON.stringify({ quantity: parseInt(quantity) })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Failed to add item to cart');
        }
        
        // Update cart count in the navbar
        updateCartCount(data.cart.total_quantity);
        
        // Show success message
        showToast('Success', data.message, 'success');
        
    } catch (error) {
        console.error('Error adding to cart:', error);
        showToast('Error', error.message || 'Failed to add item to cart', 'error');
    } finally {
        // Reset button state
        button.disabled = false;
        button.innerHTML = originalHtml;
    }
}

/**
 * Update cart count in the navbar
 * @param {number} count - The new cart item count
 */
function updateCartCount(count) {
    const cartCountElements = document.querySelectorAll('.cart-count');
    cartCountElements.forEach(el => {
        el.textContent = count || '0';
    });
    
    // Update the cart count in any mini-cart widgets
    const miniCartCounts = document.querySelectorAll('.mini-cart-count');
    miniCartCounts.forEach(el => {
        el.textContent = count || '0';
    });
}

/**
 * Show a toast notification
 * @param {string} title - The title of the toast
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, error, info, warning)
 */
function showToast(title, message, type = 'info') {
    // Create toast container if it doesn't exist
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast show ${type}`;
    toast.style.minWidth = '300px';
    toast.style.padding = '15px';
    toast.style.marginBottom = '10px';
    toast.style.borderRadius = '4px';
    toast.style.color = 'white';
    toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    
    // Set background color based on type
    const colors = {
        'success': '#28a745',
        'error': '#dc3545',
        'info': '#17a2b8',
        'warning': '#ffc107'
    };
    
    toast.style.backgroundColor = colors[type] || '#17a2b8';
    
    // Add title if provided
    if (title) {
        const titleEl = document.createElement('div');
        titleEl.style.fontWeight = 'bold';
        titleEl.style.marginBottom = '5px';
        titleEl.textContent = title;
        toast.appendChild(titleEl);
    }
    
    // Add message
    const messageEl = document.createElement('div');
    messageEl.textContent = message;
    toast.appendChild(messageEl);
    
    // Add close button
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'btn-close btn-close-white';
    closeBtn.style.position = 'absolute';
    closeBtn.style.top = '5px';
    closeBtn.style.right = '5px';
    closeBtn.style.background = 'transparent';
    closeBtn.style.border = 'none';
    closeBtn.style.color = 'white';
    closeBtn.style.opacity = '0.7';
    closeBtn.style.cursor = 'pointer';
    closeBtn.innerHTML = '&times;';
    closeBtn.setAttribute('aria-label', 'Close');
    closeBtn.addEventListener('click', () => {
        toast.remove();
    });
    toast.appendChild(closeBtn);
    
    // Add to container
    container.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s';
        setTimeout(() => {
            toast.remove();
        }, 500);
    }, 5000);
}

/**
 * Get a cookie by name
 * @param {string} name - The name of the cookie to get
 * @returns {string} The cookie value or an empty string if not found
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue || '';
}

/**
 * Update product quantity in the cart
 * @param {HTMLElement} input - The quantity input element
 */
async function updateQuantity(input) {
    const itemId = input.dataset.itemId;
    const newQuantity = parseInt(input.value);
    
    if (isNaN(newQuantity) || newQuantity < 1) {
        input.value = input.dataset.originalValue || '1';
        return;
    }
    
    try {
        const response = await fetch(`/store/cart/update/${itemId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFTTOKEN': getCookie('csrftoken')
            },
            body: JSON.stringify({ quantity: newQuantity })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Failed to update quantity');
        }
        
        // Update cart totals
        updateCartCount(data.cart.total_quantity);
        
        // If we're on the cart page, update the cart display
        if (document.querySelector('.cart-page')) {
            window.location.reload();
        }
        
    } catch (error) {
        console.error('Error updating quantity:', error);
        showToast('Error', error.message || 'Failed to update quantity', 'error');
        input.value = input.dataset.originalValue || '1';
    }
}
