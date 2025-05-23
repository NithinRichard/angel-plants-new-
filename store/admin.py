from django.contrib import admin
from django.contrib.admin import AdminSite
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from .models import (
    Category, Product, Order, OrderItem, 
    Wishlist, Review, Coupon,
    Payment, BlogPost, BlogCategory, BlogTag,
    Variation, VariationOption, ProductVariation, Address
)

# Custom admin site
class AngelPlantsAdminSite(AdminSite):
    site_header = "Angel's Plant Shop Administration"
    site_title = "Angel's Plant Shop Admin"
    index_title = "Welcome to Angel's Plant Shop Admin"

# Create an instance of the custom admin site
angel_plants_admin = AngelPlantsAdminSite(name='angel_plants_admin')

# Admin classes
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_category', 'price', 'get_quantity', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at', 'updated_at', 'category']
    list_editable = ['price', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    date_hierarchy = 'created_at'
    
    def get_category(self, obj):
        return obj.category.name if obj.category else 'No Category'
    get_category.short_description = 'Category'
    get_category.admin_order_field = 'category__name'
    
    def get_quantity(self, obj):
        return obj.quantity
    get_quantity.short_description = 'Qty'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'updated_at', 'payment_status']
    list_filter = ['payment_status', 'created_at', 'updated_at']
    search_fields = ['user__username', 'id']
    inlines = [OrderItemInline]
    ordering = ['-created_at']

class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'product', 'price', 'quantity', 'get_cost']
    list_filter = ['order__payment_status', 'order__created_at']
    search_fields = ['order__id', 'product__name']
    raw_id_fields = ['order', 'product']
    list_select_related = ['order', 'product']

class WishlistAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_username', 'product', 'quantity', 'is_public', 'created_at', 'updated_at']
    list_filter = [
        'is_public',
        'created_at',
        'updated_at',
        'product__category'
    ]
    search_fields = [
        'user__username',
        'product__name',
        'product__description',
        'notes'
    ]
    raw_id_fields = ['user', 'product']
    list_select_related = ['user', 'product', 'product__category']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['quantity', 'is_public']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'product', 'quantity', 'is_public')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_username(self, obj):
        return obj.user.username if obj.user else 'Anonymous'
    get_username.short_description = 'User'
    get_username.admin_order_field = 'user__username'

# Register models with the default admin site
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Wishlist, WishlistAdmin)

# Register models with the custom admin site
angel_plants_admin.register(Category, CategoryAdmin)
angel_plants_admin.register(Product, ProductAdmin)
angel_plants_admin.register(Order, OrderAdmin)
angel_plants_admin.register(OrderItem, OrderItemAdmin)
angel_plants_admin.register(Wishlist, WishlistAdmin)
