from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.urls import reverse_lazy
from . import views

# Import cart views from the cart_views module
from .cart_views import add_to_cart, update_cart, remove_from_cart

# Import payment views
from .payment_views import (
    PaymentView,
    CreateRazorpayOrderView,
    PaymentSuccessView,
    PaymentFailedView,
    payment_webhook
)

app_name = 'store'

urlpatterns = [
    # Home and core pages
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('contact/thanks/', views.ContactThanksView.as_view(), name='contact_thanks'),
    path('faq/', views.FAQView.as_view(), name='faq'),
    path('terms/', views.TermsView.as_view(), name='terms'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('shipping-returns/', views.ShippingReturnsView.as_view(), name='shipping_returns'),
    
    # Shop
    path('shop/', views.ProductListView.as_view(), name='product_list'),
    path('category/<slug:category_slug>/', views.ProductListView.as_view(), name='product_list_by_category'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('search/', views.ProductSearchView.as_view(), name='product_search'),
    
    # Cart and Checkout
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/update/', update_cart, name='update_cart'),
    path('cart/update/<int:item_id>/', update_cart, name='update_cart_item'),
    path('cart/add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.ClearCartView.as_view(), name='clear_cart'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('checkout/payment/<int:order_id>/', PaymentView.as_view(), name='payment'),
    path('checkout/payment/create-order/', CreateRazorpayOrderView.as_view(), name='create_razorpay_order'),
    path('checkout/payment/success/', PaymentSuccessView.as_view(), name='payment_success'),
    path('checkout/payment/failed/', PaymentFailedView.as_view(), name='payment_failed'),
    path('checkout/success/<str:order_number>/', views.CheckoutSuccessView.as_view(), name='checkout_success'),
    path('checkout/cancel/', views.CheckoutCancelView.as_view(), name='checkout_cancel'),
    path('payment/webhook/', payment_webhook, name='payment_webhook'),
    
    # User account
    path('account/', views.AccountView.as_view(), name='account'),
    path('account/orders/', views.OrderHistoryView.as_view(), name='order_history'),
    path('account/orders/<str:order_number>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('invoice/<int:pk>/', views.InvoiceView.as_view(), name='invoice'),
    # Address Management
    path('account/addresses/', views.AddressBookView.as_view(), name='address_book'),
    path('account/addresses/add/', views.AddressCreateView.as_view(), name='address_create'),
    path('account/addresses/<int:pk>/edit/', views.AddressUpdateView.as_view(), name='address_update'),
    path('account/addresses/<int:pk>/delete/', views.AddressDeleteView.as_view(), name='address_delete'),
    path('account/addresses/<int:pk>/set-default/', views.SetDefaultAddressView.as_view(), name='set_default_address'),
    
    # Wishlist
    path('account/wishlist/', views.WishlistView.as_view(), name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('account/settings/', views.AccountSettingsView.as_view(), name='account_settings'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='account/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='account/password_reset.html',
        email_template_name='emails/password_reset_email.html',
        subject_template_name='emails/password_reset_subject.txt',
        success_url='/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='account/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='account/password_reset_confirm.html',
        success_url='/password-reset/complete/'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='account/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Blog
    path('blog/', views.BlogPostListView.as_view(), name='blog_post_list'),
    path('blog/<int:year>/<int:month>/<int:day>/<slug:slug>/', views.BlogPostDetailView.as_view(), name='blog_post_detail'),
    path('blog/category/<slug:category_slug>/', views.BlogCategoryView.as_view(), name='blog_category'),
    path('blog/tag/<slug:tag_slug>/', views.BlogTagView.as_view(), name='blog_tag'),
    path('blog/archive/<int:year>/<int:month>/', views.BlogMonthArchiveView.as_view(), name='blog_archive_month'),
    path('blog/archive/<int:year>/', views.BlogYearArchiveView.as_view(), name='blog_archive_year'),
    
    # API Endpoints
    path('api/wishlist/toggle/<int:product_id>/', views.api_toggle_wishlist, name='api_toggle_wishlist'),
    path('api/cart/update/', views.api_update_cart, name='api_update_cart'),
    path('api/product/rate/', views.api_rate_product, name='api_rate_product'),
    
    # Admin/Staff
    path('staff/dashboard/', views.StaffDashboardView.as_view(), name='staff_dashboard'),
    path('staff/orders/', views.StaffOrderListView.as_view(), name='staff_order_list'),
    path('staff/orders/<str:order_number>/', views.StaffOrderDetailView.as_view(), name='staff_order_detail'),
    path('staff/orders/<str:order_number>/update/', views.StaffOrderUpdateView.as_view(), name='staff_order_update'),
    path('staff/orders/<str:order_number>/status/update/', views.update_order_status, name='update_order_status'),
    path('staff/products/', views.StaffProductListView.as_view(), name='staff_product_list'),
    path('staff/products/add/', views.StaffProductCreateView.as_view(), name='staff_product_add'),
    path('staff/products/<int:pk>/', views.StaffProductUpdateView.as_view(), name='staff_product_edit'),
    path('staff/products/<int:pk>/delete/', views.StaffProductDeleteView.as_view(), name='staff_product_delete'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
