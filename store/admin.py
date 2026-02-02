from django.contrib import admin
from .models import Product, Category, Order, Cart, CartItem, Profile

class AdminProduct(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'inventory']

class AdminCategory(admin.ModelAdmin):
    list_display = ['name']

admin.site.register(Product, AdminProduct)
admin.site.register(Category, AdminCategory)
admin.site.register(Order)
admin.site.register(Profile)

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    inlines = [CartItemInline] # shows items only in the cart detail view

admin.site.register(Cart, CartAdmin)