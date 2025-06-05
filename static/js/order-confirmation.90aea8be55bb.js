document.addEventListener('DOMContentLoaded', function() {
    try {
        const transactionData = {
            transaction_id: document.body.dataset.orderId,
            value: 0,
            currency: 'USD',
            tax: 0,
            shipping: 5.99,
            items: []
        };

        // Set total value with fallback
        const totalValue = parseFloat(document.body.dataset.orderTotal || '0');
        if (!isNaN(totalValue) && isFinite(totalValue)) {
            transactionData.value = totalValue;
        }
        
        // Set tax with fallback
        const taxValue = parseFloat(document.body.dataset.orderTax || '0');
        if (!isNaN(taxValue) && isFinite(taxValue)) {
            transactionData.tax = taxValue;
        }
        
        // Add items to transaction data
        document.querySelectorAll('.order-item').forEach(itemElement => {
            const price = parseFloat(itemElement.dataset.price || '0');
            const quantity = parseInt(itemElement.dataset.quantity || '1', 10);
            
            if (!isNaN(price) && isFinite(price) && !isNaN(quantity) && quantity > 0) {
                transactionData.items.push({
                    item_id: itemElement.dataset.itemId || '',
                    item_name: itemElement.dataset.itemName || '',
                    item_category: itemElement.dataset.itemCategory || '',
                    price: price,
                    quantity: quantity
                });
            }
        });
        
        // Send the purchase event to Google Analytics
        if (typeof gtag === 'function') {
            gtag('event', 'purchase', transactionData);
        }
    } catch (error) {
        console.error('Error tracking purchase:', error);
    }
});
