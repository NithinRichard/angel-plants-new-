// This file contains the main JavaScript for Angel's Plant Shop

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Update cart count in navbar
    function updateCartCount() {
        // This would be updated via AJAX in a real application
        // For now, we'll just update the UI based on the current page
        const cartItems = document.querySelectorAll('.cart-item');
        const cartBadge = document.querySelector('.cart-badge');
        if (cartBadge && cartItems.length > 0) {
            cartBadge.textContent = cartItems.length;
            cartBadge.style.display = 'inline-block';
        }
    }

    // Handle quantity changes in cart
    document.querySelectorAll('.quantity-input').forEach(input => {
        input.addEventListener('change', function() {
            const itemId = this.dataset.itemId;
            const newQuantity = parseInt(this.value);
            
            if (newQuantity < 1) {
                this.value = 1;
                return;
            }
            
            // In a real app, you would make an AJAX call here to update the cart
            console.log(`Updating item ${itemId} quantity to ${newQuantity}`);
            
            // For demo purposes, we'll just update the subtotal
            updateSubtotal(itemId, newQuantity);
        });
    });

    // Update subtotal for an item
    function updateSubtotal(itemId, quantity) {
        const price = parseFloat(document.querySelector(`#item-price-${itemId}`).textContent);
        const subtotal = (price * quantity).toFixed(2);
        document.querySelector(`#item-subtotal-${itemId}`).textContent = subtotal;
        
        // Update the total
        updateCartTotal();
    }

    // Update cart total
    function updateCartTotal() {
        let total = 0;
        document.querySelectorAll('.cart-item').forEach(item => {
            const subtotal = parseFloat(item.querySelector('.item-subtotal').textContent);
            total += subtotal;
        });
        
        document.querySelector('#cart-total').textContent = total.toFixed(2);
    }

    // Initialize cart functionality
    updateCartCount();
    
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Handle image zoom on product detail page
    const productImage = document.querySelector('.product-detail-img');
    if (productImage) {
        productImage.addEventListener('click', function() {
            this.classList.toggle('zoomed');
        });
    }
});

// Form validation
function validateForm() {
    // Add your form validation logic here
    return true;
}

// Function to show loading state for buttons
function setLoading(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        const originalText = button.innerHTML;
        button.setAttribute('data-original-text', originalText);
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
    } else {
        const originalText = button.getAttribute('data-original-text');
        if (originalText) {
            button.innerHTML = originalText;
            button.removeAttribute('data-original-text');
        }
        button.disabled = false;
    }
}
