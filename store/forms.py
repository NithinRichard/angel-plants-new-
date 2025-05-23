from django import forms
from django.forms import ModelForm, inlineformset_factory
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import (
    Product, Category, ProductImage, ProductTag, Order, OrderItem, 
    OrderActivity, Address, Coupon, ProductVariation, Variation, VariationOption
)

User = get_user_model()

from .models import Profile

class ProfileForm(forms.ModelForm):
    """Form for updating user profile information."""
    class Meta:
        model = Profile
        fields = ['phone', 'profile_picture', 'bio', 'date_of_birth', 'website']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'phone': _('Phone Number'),
            'profile_picture': _('Profile Picture'),
            'bio': _('Bio'),
            'date_of_birth': _('Date of Birth'),
            'website': _('Website'),
        }

class UserForm(forms.ModelForm):
    """Form for updating basic user information."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'email': _('Email Address'),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError(_('This email address is already in use.'))
        return email

class OrderForm(forms.ModelForm):
    """
    Form for staff to update order details.
    """
    class Meta:
        model = Order
        fields = [
            'status', 'tracking_number', 'tracking_url', 'shipping_fee', 'notes'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'tracking_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tracking_url': forms.URLInput(attrs={'class': 'form-control'}),
            'shipping_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # Customize the status choices if needed
        self.fields['status'].choices = Order.STATUS_CHOICES

    def save(self, commit=True):
        order = super().save(commit=False)
        
        # Check if status has changed
        if 'status' in self.changed_data:
            # Create an activity log for status change
            OrderActivity.objects.create(
                order=order,
                activity_type='status_change',
                note=f'Order status changed to {order.get_status_display()}',
                created_by=self.request.user if self.request and hasattr(self.request, 'user') else None
            )
        
        # Add a note if this is a new note
        if 'notes' in self.changed_data and self.cleaned_data['notes']:
            OrderActivity.objects.create(
                order=order,
                activity_type='note',
                note=f'Note added: {self.cleaned_data["notes"]}',
                created_by=self.request.user if self.request and hasattr(self.request, 'user') else None
            )
        
        if commit:
            order.save()
        return order


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'address_type', 'first_name', 'last_name', 'company',
            'address_line1', 'address_line2', 'city', 'state',
            'postal_code', 'country', 'phone', 'default'
        ]
        widgets = {
            'address_type': forms.HiddenInput(),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        address = super().save(commit=False)
        if self.user:
            address.user = self.user
            
            # If this is set as default, unset default for other addresses of the same type
            if address.default and address.address_type:
                self.user.addresses.filter(
                    address_type=address.address_type,
                    default=True
                ).exclude(pk=address.pk if address.pk else None).update(default=False)
        
        if commit:
            address.save()
        return address


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Name',
            'required': True
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Email',
            'required': True
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject',
            'required': True
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Your Message',
            'required': True
        })
    )


class ProductForm(ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'price', 'compare_at_price', 'cost_per_item',
            'quantity', 'track_quantity', 'allow_backorder', 'description',
            'short_description', 'care_instructions', 'light_requirements',
            'watering_needs', 'mature_size', 'difficulty_level', 'is_featured',
            'is_bestseller', 'is_active', 'meta_title', 'meta_description', 'tags'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'short_description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'care_instructions': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'meta_description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_bestseller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'track_quantity': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_backorder': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['is_featured', 'is_bestseller', 'is_active', 'track_quantity', 'allow_backorder']:
                field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = 'required'
    
    def clean(self):
        cleaned_data = super().clean()
        compare_at_price = cleaned_data.get('compare_at_price')
        price = cleaned_data.get('price')
        
        if compare_at_price and price and compare_at_price <= price:
            self.add_error('compare_at_price', 
                         'Compare at price must be higher than the selling price')
        
        return cleaned_data


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_featured', 'order']
        widgets = {
            'alt_text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


# Formset for product images
ProductImageFormSet = inlineformset_factory(
    Product, ProductImage,
    form=ProductImageForm,
    extra=5,
    can_delete=True,
    can_delete_extra=True
)


class ProductTagForm(forms.ModelForm):
    class Meta:
        model = ProductTag
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Add a new tag...'
            })
        }


class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(
        label='Shipping Address',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter your complete shipping address'
        })
    )
    billing_address = forms.CharField(
        label='Billing Address',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'If different from shipping address'
        })
    )
    payment_method = forms.ChoiceField(
        label='Payment Method',
        choices=[
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('upi', 'UPI'),
            ('cod', 'Cash on Delivery')
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        # Add any custom validation here
        return cleaned_data


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_type', 'discount_value', 'valid_from', 'valid_to', 'max_uses', 'used_count', 'min_order_value', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'max_uses': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_order_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductVariationForm(forms.ModelForm):
    class Meta:
        model = ProductVariation
        fields = ['product', 'variation', 'option', 'price_adjustment', 'quantity', 'sku', 'is_default']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'variation': forms.Select(attrs={'class': 'form-select'}),
            'option': forms.Select(attrs={'class': 'form-select'}),
            'price_adjustment': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class VariationForm(forms.ModelForm):
    class Meta:
        model = Variation
        fields = ['name', 'product_type', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class VariationOptionForm(forms.ModelForm):
    class Meta:
        model = VariationOption
        fields = ['variation', 'name', 'color_code', 'is_active']
        widgets = {
            'variation': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'color_code': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ReviewForm(forms.Form):
    RATING_CHOICES = [
        (5, '★★★★★'),
        (4, '★★★★☆'),
        (3, '★★★☆☆'),
        (2, '★★☆☆☆'),
        (1, '★☆☆☆☆'),
    ]
    
    rating = forms.ChoiceField(
        label='Rating',
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'rating-radio'}),
        required=True
    )
    title = forms.CharField(
        label='Review Title',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    comment = forms.CharField(
        label='Your Review',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Share your experience with this product...'
        }),
        required=True
    )
