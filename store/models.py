from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator, FileExtensionValidator
from django.db.models import F, Q, Sum
from django.core.exceptions import ValidationError
from django.conf import settings
from django.dispatch import receiver
from django_countries.fields import CountryField
from model_utils import FieldTracker
from ckeditor.fields import RichTextField
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.html import strip_tags
from django.db.models import Avg, Count, Sum, F, Q, DecimalField
from django.db.models.functions import Coalesce
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from PIL import Image

User = get_user_model()

class Payment(models.Model):
    """
    Model to store payment information for orders.
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('refunded', _('Refunded')),
        ('partially_refunded', _('Partially Refunded')),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', _('Credit Card')),
        ('debit_card', _('Debit Card')),
        ('upi', _('UPI')),
        ('net_banking', _('Net Banking')),
        ('wallet', _('Wallet')),
        ('cod', _('Cash on Delivery')),
    ]
    
    order = models.OneToOneField(
        'Order',
        on_delete=models.CASCADE,
        related_name='payment',
        verbose_name=_('order')
    )
    payment_id = models.CharField(_('payment ID'), max_length=100, unique=True)
    payment_method = models.CharField(
        _('payment method'),
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES
    )
    amount = models.DecimalField(
        _('amount'),
        max_digits=10,
        decimal_places=2
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    transaction_id = models.CharField(
        _('transaction ID'),
        max_length=100,
        blank=True,
        null=True
    )
    payment_gateway_response = models.JSONField(
        _('payment gateway response'),
        default=dict,
        blank=True
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('payment')
        verbose_name_plural = _('payments')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.payment_id} - {self.get_status_display()}"


class Profile(models.Model):
    """Profile model to store additional user information."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    phone = models.CharField(
        _('phone number'),
        max_length=15,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to='profile_pictures/',
        default='profile_pictures/default-avatar.png',
        blank=True
    )
    bio = models.TextField(_('bio'), blank=True)
    date_of_birth = models.DateField(_('date of birth'), null=True, blank=True)
    website = models.URLField(_('website'), blank=True)
    
    class Meta:
        verbose_name = _('profile')
        verbose_name_plural = _('profiles')
        
    def __str__(self):
        return f"Profile for {self.user.get_full_name()}"

    def get_full_name(self):
        """Return the user's full name."""
        return self.user.get_full_name()

    def get_short_name(self):
        """Return the user's short name."""
        return self.user.get_short_name()

    def get_profile_picture_url(self):
        """Return the URL of the profile picture."""
        if hasattr(self, 'profile_picture') and self.profile_picture:
            return self.profile_picture.url
        return '/static/profile_pictures/default-avatar.png'

    def save(self, *args, **kwargs):
        """Ensure profile picture is saved correctly."""
        try:
            super().save(*args, **kwargs)
            if self.profile_picture:
                # Resize image if needed
                from PIL import Image
                img = Image.open(self.profile_picture.path)
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size)
                    img.save(self.profile_picture.path)
        except Exception as e:
            print(f"Error saving profile: {str(e)}")

class Wishlist(models.Model):
    """
    Model to store user's wishlist items
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name=_('user'),
        db_index=True,
        null=True,  # Allow null for anonymous users
        blank=True  # Allow blank in forms
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name=_('product'),
        db_index=True
    )
    quantity = models.PositiveIntegerField(
        _('quantity'),
        default=1,
        validators=[MinValueValidator(1)],
        help_text=_('Number of items')
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Any additional notes about this item')
    )
    is_public = models.BooleanField(
        _('is public'),
        default=False,
        help_text=_('Allow others to see this wishlist item')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True, db_index=True)
    
    class Meta:
        app_label = 'store'
        verbose_name = _('wishlist item')
        verbose_name_plural = _('wishlist items')
        ordering = ['-created_at']
        unique_together = ['user', 'product']
        db_table = 'store_wishlist'
    
    def __str__(self):
        username = self.user.get_username() if self.user else 'Anonymous'
        product_name = getattr(self.product, 'name', 'Unknown Product')
        return f"{username}'s wishlist: {product_name} (x{self.quantity})"
    
    def clean(self):
        # Ensure the user exists for non-anonymous wishlist items
        if not self.user and not hasattr(self, 'session_key'):
            raise ValidationError(_('Either a user or session key is required'))
            
        # Ensure the product exists
        if not hasattr(self, 'product') or not self.product.pk:
            raise ValidationError({'product': _('A valid product is required')})
    
    def save(self, *args, **kwargs):
        # Ensure quantity is at least 1
        if self.quantity < 1:
            self.quantity = 1
            
        # Clean and validate
        self.clean()
        
        # Save the item
        super().save(*args, **kwargs)
    
    @classmethod
    def add_to_wishlist(cls, user, product, quantity=1, notes='', is_public=False):
        """
        Add an item to the wishlist or update quantity if it already exists
        """
        with transaction.atomic():
            item, created = cls.objects.get_or_create(
                user=user,
                product=product,
                defaults={
                    'quantity': quantity,
                    'notes': notes,
                    'is_public': is_public
                }
            )
            if not created:
                item.quantity += quantity
                if notes:
                    item.notes = notes
                item.is_public = is_public
                item.save()
        return item
    
    @classmethod
    def get_user_wishlist(cls, user):
        """
        Get all wishlist items for a user
        """
        return cls.objects.filter(user=user).select_related('product')
    
    @classmethod
    def get_public_wishlists(cls):
        """
        Get all public wishlist items
        """
        return cls.objects.filter(is_public=True).select_related('product', 'user')


class Review(models.Model):
    """
    Model to store product reviews and ratings from customers.
    """
    RATING_CHOICES = [
        (1, _('1 - Poor')),
        (2, _('2 - Fair')),
        (3, _('3 - Good')),
        (4, _('4 - Very Good')),
        (5, _('5 - Excellent')),
    ]
    
    product = models.ForeignKey(
        'Product', 
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name=_('product')
    )
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='reviews',
        verbose_name=_('user')
    )
    rating = models.PositiveSmallIntegerField(
        _('rating'),
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(_('review title'), max_length=200)
    comment = models.TextField(_('comment'))
    is_approved = models.BooleanField(_('is approved'), default=False)
    is_featured = models.BooleanField(_('is featured'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('review')
        verbose_name_plural = _('reviews')
        ordering = ['-created_at']
        unique_together = ['product', 'user']
    
    def __str__(self):
        return f"{self.rating} star review by {self.user} for {self.product}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update product rating average when a review is saved
        self.product.update_average_rating()
    
    def delete(self, *args, **kwargs):
        product = self.product
        super().delete(*args, **kwargs)
        # Update product rating average when a review is deleted
        product.update_average_rating()

class Variation(models.Model):
    """
    Model to define types of variations (e.g., Color, Size, etc.)
    """
    name = models.CharField(_('variation name'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    product_type = models.CharField(
        _('product type'), 
        max_length=50, 
        help_text=_('Type of product this variation applies to')
    )
    is_active = models.BooleanField(_('is active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('variation')
        verbose_name_plural = _('variations')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class VariationOption(models.Model):
    """
    Model to define specific options for a variation (e.g., Red, Blue, Small, Large)
    """
    variation = models.ForeignKey(
        Variation, 
        on_delete=models.CASCADE, 
        related_name='options',
        verbose_name=_('variation')
    )
    name = models.CharField(_('option name'), max_length=100)
    color_code = models.CharField(
        _('color code'), 
        max_length=20, 
        blank=True, 
        help_text=_('Hex color code for color variations')
    )
    is_active = models.BooleanField(_('is active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('variation option')
        verbose_name_plural = _('variation options')
        ordering = ['variation', 'name']
        unique_together = ['variation', 'name']
    
    def __str__(self):
        return f"{self.variation.name}: {self.name}"


class ProductVariation(models.Model):
    """
    Model to link products with their variations and options
    """
    product = models.ForeignKey(
        'Product', 
        on_delete=models.CASCADE, 
        related_name='variations',
        verbose_name=_('product')
    )
    variation = models.ForeignKey(
        Variation, 
        on_delete=models.CASCADE, 
        related_name='product_variations',
        verbose_name=_('variation')
    )
    option = models.ForeignKey(
        VariationOption, 
        on_delete=models.CASCADE, 
        related_name='product_variations',
        verbose_name=_('variation option')
    )
    price_adjustment = models.DecimalField(
        _('price adjustment'), 
        max_digits=10, 
        decimal_places=2,
        default=0.00,
        help_text=_('Additional cost (can be negative for discounts)')
    )
    quantity = models.PositiveIntegerField(
        _('quantity'), 
        default=0,
        help_text=_('Available quantity for this variation')
    )
    sku = models.CharField(
        _('SKU'), 
        max_length=100, 
        blank=True,
        help_text=_('Stock Keeping Unit')
    )
    is_default = models.BooleanField(
        _('is default'), 
        default=False,
        help_text=_('Is this the default variation?')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('product variation')
        verbose_name_plural = _('product variations')
        ordering = ['product', 'variation', 'option']
        unique_together = ['product', 'variation', 'option']
    
    def __str__(self):
        return f"{self.product.name} - {self.variation.name}: {self.option.name}"
    
    def get_price(self):
        """Get the final price for this variation"""
        return self.product.price + self.price_adjustment


class Address(models.Model):
    """
    Model to store user addresses for shipping and billing.
    """
    ADDRESS_TYPE_CHOICES = [
        ('shipping', 'Shipping Address'),
        ('billing', 'Billing Address'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES)
    default = models.BooleanField(default=False)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    company = models.CharField(max_length=100, blank=True, null=True)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = CountryField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-default', '-updated_at']
        unique_together = ['user', 'address_type', 'default']
    
    def __str__(self):
        return f"{self.get_address_type_display()} - {self.address_line1}, {self.city}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_address_html(self):
        """Return address as HTML"""
        address_html = f"""
            {self.get_full_name()}<br>
            {self.address_line1}<br>
        """
        if self.address_line2:
            address_html += f"{self.address_line2}<br>"
        address_html += f"""
            {self.city}, {self.state} {self.postal_code}<br>
            {self.country.name}
        """
        if self.phone:
            address_html += f"<br>Phone: {self.phone}"
        return address_html


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name

class Product(models.Model):
    # Basic Information
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    sku = models.CharField(max_length=50, unique=True, blank=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_per_item = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Inventory
    quantity = models.PositiveIntegerField(default=0)
    track_quantity = models.BooleanField(default=True)
    allow_backorder = models.BooleanField(default=False)
    
    # Product Details
    description = models.TextField()
    short_description = models.TextField(max_length=200, blank=True)
    care_instructions = models.TextField(blank=True)
    
    # Media
    image = models.ImageField(upload_to='products/')
    additional_images = models.ManyToManyField(
        'ProductImage', 
        blank=True,
        related_name='additional_product_images'  # Changed related_name
    )
    
    # Organization
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    tags = models.ManyToManyField('ProductTag', blank=True, related_name='products')
    
    # Plant Specific
    light_requirements = models.CharField(max_length=100, blank=True)
    watering_needs = models.CharField(max_length=100, blank=True)
    mature_size = models.CharField(max_length=100, blank=True)
    difficulty_level = models.CharField(max_length=50, choices=[
        ('easy', 'Easy'),
        ('moderate', 'Moderate'),
        ('difficult', 'Difficult')
    ], default='easy')
    
    # SEO
    meta_title = models.CharField(max_length=100, blank=True)
    meta_description = models.TextField(blank=True)
    
    # Status
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property
    def in_stock(self):
        return self.quantity > 0
    
    @property
    def on_sale(self):
        return self.compare_at_price and self.compare_at_price > self.price
    
    @property
    def discount_percentage(self):
        if self.on_sale:
            return int(((self.compare_at_price - self.price) / self.compare_at_price) * 100)
        return 0


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='product_images',
        verbose_name=_('product')
    )
    image = models.ImageField(
        _('image'),
        upload_to='products/additional/'
    )
    alt_text = models.CharField(
        _('alt text'),
        max_length=200, 
        blank=True,
        help_text=_('Alternative text for accessibility')
    )
    is_featured = models.BooleanField(
        _('is featured'),
        default=False,
        help_text=_('Mark this image as the featured image')
    )
    order = models.PositiveIntegerField(
        _('order'),
        default=0,
        help_text=_('Order in which the image appears')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('product image')
        verbose_name_plural = _('product images')
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"Image for {self.product.name}"


class ProductTag(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Cart(models.Model):
    """
    Model representing a shopping cart.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('abandoned', 'Abandoned'),
        ('converted', 'Converted to Order'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carts',
        verbose_name=_('user')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_('status')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    total = models.DecimalField(
        _('total'),
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_('Total amount for the cart')
    )
    
    class Meta:
        verbose_name = _('cart')
        verbose_name_plural = _('carts')
        ordering = ['-updated_at']
    
    def save(self, *args, **kwargs):
        if self.status == 'active' and self.user_id:
            # Get all active carts for this user
            active_carts = Cart.objects.filter(
                user=self.user,
                status='active'
            ).exclude(pk=getattr(self, 'pk', None))
            
            # Mark other active carts as abandoned
            active_carts.update(status='abandoned')
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Cart for {self.user.email}"
    
    @property
    def item_count(self):
        """Return the number of items in the cart."""
        return self.items.aggregate(
            total=models.Sum('quantity', default=0)
        )['total']
    
    @property
    def total_quantity(self):
        """Return the total quantity of items in the cart."""
        return self.items.aggregate(
            total=models.Sum('quantity', default=0)
        )['total']
    
    @property
    def subtotal(self):
        """Calculate the subtotal of all items in the cart."""
        from django.db.models import Sum, F, DecimalField, Value
        from decimal import Decimal
        
        result = self.items.aggregate(
            subtotal=Sum(
                F('quantity') * F('price'),
                output_field=DecimalField(max_digits=10, decimal_places=2),
                default=Decimal('0.00')
            )
        )
        return result['subtotal'] or Decimal('0.00')
    
    @property
    def total(self):
        """Calculate the total amount."""
        return self.subtotal
    
    def update_totals(self, save=True):
        """Update the cart's totals based on its items."""
        # Calculate new total based on items
        new_total = self.subtotal
        
        # Update the total if it has changed
        if self.total != new_total:
            self.total = new_total
            if save:
                self.save(update_fields=['total', 'updated_at'])
        return self.total
        
    def clear(self):
        """Remove all items from the cart."""
        self.items.all().delete()
        self.save()
    



class CartItem(models.Model):
    """
    Model representing an item in a shopping cart.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('cart')
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name=_('product')
    )
    quantity = models.PositiveIntegerField(
        _('quantity'),
        default=1,
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        _('price'),
        max_digits=10,
        decimal_places=2,
        help_text=_('Price at time of adding to cart')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('cart item')
        verbose_name_plural = _('cart items')
        ordering = ['-created_at']
        unique_together = ['cart', 'product']
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in cart"
    
    @property
    def total_price(self):
        """Calculate the total price for this cart item."""
        return self.quantity * self.price
    
    def increase_quantity(self, quantity=1):
        """Increase the quantity of this item in the cart."""
        self.quantity += quantity
        self.save(update_fields=['quantity', 'updated_at'])
    
    def decrease_quantity(self, quantity=1):
        """Decrease the quantity of this item in the cart."""
        self.quantity -= quantity
        if self.quantity <= 0:
            self.delete()
            return False
        self.save(update_fields=['quantity', 'updated_at'])
        return True
    
    def clean(self):
        """Validate the cart item before saving."""
        if not self.product or not self.product.is_active:
            raise ValidationError({
                'product': 'This product is no longer available.'
            })
            
        if self.quantity < 1:
            raise ValidationError({
                'quantity': 'Quantity must be at least 1.'
            })
            
        if self.product.track_quantity and self.quantity > self.product.quantity:
            raise ValidationError({
                'quantity': f'Only {self.product.quantity} items available in stock.'
            })
    
    def save(self, *args, **kwargs):
        """Save the cart item and update the cart's updated_at timestamp."""
        from decimal import Decimal
        
        # Set price from product if not set or if it's a new item
        if not self.pk or not hasattr(self, 'price') or not self.price:
            self.price = Decimal(str(self.product.price))
            
        # Ensure quantity is positive
        self.quantity = max(1, int(self.quantity))
        
        # Validate before saving
        self.full_clean()
        
        # Save the item
        with transaction.atomic():
            # Lock the cart to prevent race conditions
            cart = Cart.objects.select_for_update().get(pk=self.cart_id)
            super().save(*args, **kwargs)
            
            # Update cart's updated_at and totals without triggering another save
            cart.updated_at = timezone.now()
            cart.update_totals(save=True)
            
            # Refresh the cart from database to get latest values
            cart.refresh_from_db()


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        SHIPPED = 'shipped', _('Shipped')
        DELIVERED = 'delivered', _('Delivered')
        CANCELLED = 'cancelled', _('Cancelled')
        REFUNDED = 'refunded', _('Refunded')

    # Cart relationship
    cart = models.OneToOneField(
        Cart,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order'
    )
    
    # Order information
    order_number = models.CharField(_('order number'), max_length=32, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Customer information
    email = models.EmailField(_('email address'), max_length=255)
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=30)
    phone = models.CharField(_('phone'), max_length=20, blank=True)
    
    # Shipping information
    address = models.TextField(_('shipping address'))
    address2 = models.TextField(_('address line 2'), blank=True, null=True)
    district = models.CharField(_('district'), max_length=100, null=True, blank=True)
    city = models.CharField(_('city'), max_length=100)
    state = models.CharField(_('state'), max_length=100)
    postal_code = models.CharField(_('postal code'), max_length=20)
    country = models.CharField(_('country'), max_length=100, default='India')
    
    # Order status and tracking
    status = models.CharField(_('status'), max_length=20, choices=Status.choices, default=Status.PENDING)
    tracking_number = models.CharField(_('tracking number'), max_length=100, blank=True, null=True)
    tracking_url = models.URLField(_('tracking URL'), max_length=500, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    # Financial information
    total_amount = models.DecimalField(_('total amount'), max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_('tax amount'), max_digits=10, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(_('shipping fee'), max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(_('discount amount'), max_digits=10, decimal_places=2, default=0)
    
    # Payment information
    payment_method = models.CharField(_('payment method'), max_length=50, default='cash_on_delivery')
    payment_status = models.BooleanField(_('payment status'), default=False)
    payment_id = models.CharField(_('payment id'), max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(_('razorpay order id'), max_length=100, blank=True, null=True)
    payment_signature = models.CharField(_('payment signature'), max_length=200, blank=True, null=True)
    
    # Additional information
    notes = models.TextField(_('notes'), blank=True, null=True)
    
    # Field tracker for detecting changes
    tracker = FieldTracker(fields=['status', 'tracking_number', 'tracking_url'])

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('order')
        verbose_name_plural = _('orders')
    
    def __str__(self):
        return f'Order {self.order_number or self.id}'
        
    def save(self, *args, **kwargs):
        # First save to get an ID
        super().save(*args, **kwargs)
        
        # Update order number if needed
        if not self.order_number:
            self.order_number = f'ORD-{self.created_at.strftime("%Y%m%d")}-{self.id}'
            super().save(update_fields=['order_number'])
            return
            
        # Update item prices to match current product prices
        for item in self.items.all():
            item.update_price()
    
    def get_total_cost(self, update_db=True):
        """Calculate total cost of all items in the order"""
        items = self.items.all()
        total = sum(item.quantity * item.price for item in items)
        if update_db:
            self.total_amount = total
            self.save(update_fields=['total_amount'])
        return total
        
    def get_total_with_tax_and_shipping(self):
        """
        Calculate the total order amount including tax and shipping.
        This is used for display purposes in templates.
        """
        subtotal = self.total_amount or self.get_total_cost(update_db=False)
        # Calculate tax if not already set (18% GST)
        tax = self.tax_amount if self.tax_amount is not None else subtotal * Decimal('0.18')
        # Calculate total including tax and shipping
        total = subtotal + tax + (self.shipping_fee or 0)
        # Apply any discount
        total -= self.discount_amount or 0
        return max(total, Decimal('0.00'))  # Ensure total is not negative


class OrderItem(models.Model):
    """Model to store items in an order"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('order')
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name=_('product')
    )
    price = models.DecimalField(
        _('price'),
        max_digits=10,
        decimal_places=2,
        help_text=_('Price at time of order')
    )
    quantity = models.PositiveIntegerField(
        _('quantity'),
        default=1,
        validators=[MinValueValidator(1)]
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('order item')
        verbose_name_plural = _('order items')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    def get_cost(self):
        """Calculate cost of this item"""
        return self.price * self.quantity

    def update_price(self):
        """Update price to match current product price"""
        self.price = self.product.price
        self.save(update_fields=['price'])


class OrderActivity(models.Model):
    """
    Model to track order status changes and activities.
    Each activity represents an important event in the order lifecycle.
    """
    ACTIVITY_TYPES = [
        ('status_change', _('Status Change')),
        ('note_added', _('Note Added')),
        ('payment_received', _('Payment Received')),
        ('shipping_update', _('Shipping Update')),
        ('tracking_updated', _('Tracking Updated')),
        ('customer_notified', _('Customer Notified')),
        ('other', _('Other')),
    ]
    
    # Core fields
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='activities',
        verbose_name=_('order')
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_('user')
    )
    
    # Activity details
    activity_type = models.CharField(
        _('activity type'),
        max_length=20, 
        choices=ACTIVITY_TYPES, 
        default='other'
    )
    details = models.TextField(_('details'))
    note = models.TextField(_('internal note'), blank=True, null=True)
    
    # System fields
    timestamp = models.DateTimeField(_('timestamp'), auto_now_add=True)
    notification_sent = models.BooleanField(_('notification sent'), default=False)
    notification_sent_at = models.DateTimeField(_('notification sent at'), null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    user_agent = models.TextField(_('user agent'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('order activity')
        verbose_name_plural = _('order activities')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['order', 'activity_type']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return _("%(type)s for Order %(order)s at %(time)s") % {
            'type': self.get_activity_type_display(),
            'order': self.order.order_number,
            'time': self.timestamp.strftime('%Y-%m-%d %H:%M')
        }
    
    def mark_notification_sent(self, commit=True):
        """
        Mark this activity as having a notification sent.
        """
        self.notification_sent = True
        self.notification_sent_at = timezone.now()
        if commit:
            self.save(update_fields=['notification_sent', 'notification_sent_at'])
    
    @classmethod
    def create_activity(
        cls, 
        order, 
        user=None, 
        activity_type='other', 
        details='', 
        note=None,
        request=None
    ):
        """
        Helper method to create a new activity with request context.
        """
        activity = cls(
            order=order,
            user=user,
            activity_type=activity_type,
            details=details,
            note=note
        )
        
        # Add request information if available
        if request:
            activity.ip_address = cls.get_client_ip(request)
            activity.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        activity.save()
        return activity
    
    @staticmethod
    def get_client_ip(request):
        """
        Get the client's IP address from the request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip








class BlogCategory(models.Model):
    """
    Model to categorize blog posts
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=100)
    description = models.TextField(blank=True)
    meta_title = models.CharField(max_length=100, blank=True)
    meta_description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    rating_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Blog Category'
        verbose_name_plural = 'Blog Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BlogTag(models.Model):
    """
    Model for blog post tags
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductRating(models.Model):
    """Model to store product ratings and reviews"""
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_ratings')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    review = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Product Rating'
        verbose_name_plural = 'Product Ratings'
        unique_together = ['user', 'product']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s {self.rating} star rating for {self.product.name}"


from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg

@receiver(post_save, sender=ProductRating)
@receiver(post_save, sender=Order)
def convert_cart_to_order(sender, instance, created, **kwargs):
    """
    When an order is created from a cart, update the cart status and clear its items.
    """
    if created and instance.cart:
        cart = instance.cart
        cart.status = 'converted'
        cart.save()

@receiver(post_save, sender=ProductRating)
@receiver(post_delete, sender=ProductRating)
def update_product_rating(sender, instance, **kwargs):
    """Update the average rating of a product when a rating is saved or deleted"""
    product = instance.product
    ratings = product.ratings.filter(is_approved=True)
    count = ratings.count()
    
    if count > 0:
        product.average_rating = ratings.aggregate(avg=Avg('rating'))['avg']
        product.rating_count = count
    else:
        product.average_rating = None
        product.rating_count = 0
    
    product.save(update_fields=['average_rating', 'rating_count'])


class BlogPost(models.Model):
    """Model for blog posts"""
    DRAFT = 'draft'
    PUBLISHED = 'published'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PUBLISHED, 'Published'),
    ]
    

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique_for_date='publish_date', max_length=200)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blog_posts')
    excerpt = models.TextField(blank=True, help_text='A short summary of the post')
    content = RichTextField()
    featured_image = models.ImageField(upload_to='blog/featured_images/', blank=True, null=True)
    categories = models.ManyToManyField(BlogCategory, related_name='blog_posts')
    tags = models.ManyToManyField(BlogTag, related_name='blog_posts', blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)
    allow_comments = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0, editable=False)
    meta_title = models.CharField(max_length=100, blank=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    publish_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-publish_date']
        get_latest_by = 'publish_date'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.status == self.PUBLISHED and not self.publish_date:
            self.publish_date = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if not self.publish_date:
            return ''
        return reverse('store:blog_post_detail', kwargs={
            'year': self.publish_date.year,
            'month': self.publish_date.month,
            'day': self.publish_date.day,
            'slug': self.slug
        })

    @property
    def excerpt_text(self):
        """Return plain text excerpt, falling back to first 200 chars of content"""
        if self.excerpt:
            return self.excerpt
        return strip_tags(self.content)[:200] + '...'

    @classmethod
    def add_to_wishlist(cls, user, product, notes=''):
        """
        Add a product to user's wishlist
        Returns (wishlist_item, created) tuple
        """
        return cls.objects.get_or_create(
            user=user,
            product=product,
            defaults={'notes': notes}
        )

    @classmethod
    def remove_from_wishlist(cls, user, product):
        """
        Remove a product from user's wishlist
        Returns True if item was removed, False if it didn't exist
        """
        deleted, _ = cls.objects.filter(user=user, product=product).delete()
        return deleted > 0

    @classmethod
    def get_user_wishlist(cls, user):
        """
        Get all wishlist items for a user with product prefetching
        """
        return cls.objects.filter(user=user).select_related('product')

    @property
    def product_in_stock(self):
        """Check if the product is in stock"""
        return self.product.in_stock

    def move_to_cart(self, cart, quantity=1):
        """
        Move this wishlist item to the user's cart
        Returns the created cart item or None if product is out of stock
        """
        if not self.product_in_stock:
            return None
            
        # Check if product is already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=self.product,
            defaults={
                'price': self.product.price,
                'quantity': min(quantity, self.product.quantity) if self.product.track_quantity else quantity
            }
        )
        
        if not created:
            cart_item.increase_quantity(quantity)
            
        # Remove from wishlist after adding to cart
        self.delete()
        return cart_item
