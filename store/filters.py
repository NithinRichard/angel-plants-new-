import django_filters
from django import forms
from django.db.models import Q
from .models import Product, Category

class ProductFilter(django_filters.FilterSet):
    PRICE_CHOICES = [
        ('0-500', 'Under ₹500'),
        ('500-1000', '₹500 - ₹1000'),
        ('1000-2000', '₹1000 - ₹2000'),
        ('2000-5000', '₹2000 - ₹5000'),
        ('5000-', 'Over ₹5000'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('moderate', 'Moderate'),
        ('difficult', 'Difficult'),
    ]
    
    # Price range filter
    price_range = django_filters.ChoiceFilter(
        field_name='price',
        label='Price Range',
        choices=PRICE_CHOICES,
        method='filter_by_price',
    )
    
    # Category filter
    category = django_filters.ModelChoiceFilter(
        field_name='category',
        queryset=Category.objects.all(),
        label='Category',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Difficulty level filter
    difficulty = django_filters.MultipleChoiceFilter(
        field_name='difficulty_level',
        label='Care Level',
        choices=DIFFICULTY_CHOICES,
        widget=forms.CheckboxSelectMultiple
    )
    
    # Featured filter
    featured = django_filters.BooleanFilter(
        field_name='is_featured',
        label='Featured Items Only',
        widget=forms.CheckboxInput
    )
    
    # Bestseller filter
    bestseller = django_filters.BooleanFilter(
        field_name='is_bestseller',
        label='Bestsellers Only',
        widget=forms.CheckboxInput
    )
    
    # In stock filter
    in_stock = django_filters.BooleanFilter(
        field_name='in_stock',
        label='In Stock Only',
        method='filter_in_stock',
        widget=forms.CheckboxInput
    )
    
    class Meta:
        model = Product
        fields = ['category', 'price_range', 'difficulty', 'featured', 'bestseller', 'in_stock']
    
    def filter_by_price(self, queryset, name, value):
        if value == '0-500':
            return queryset.filter(price__lte=500)
        elif value == '500-1000':
            return queryset.filter(price__gt=500, price__lte=1000)
        elif value == '1000-2000':
            return queryset.filter(price__gt=1000, price__lte=2000)
        elif value == '2000-5000':
            return queryset.filter(price__gt=2000, price__lte=5000)
        elif value == '5000-':
            return queryset.filter(price__gt=5000)
        return queryset
    
    def filter_in_stock(self, queryset, name, value):
        if value:
            # Check if the product is in stock based on quantity > 0 or allow_backorder is True
            return queryset.filter(Q(quantity__gt=0) | Q(allow_backorder=True))
        return queryset
