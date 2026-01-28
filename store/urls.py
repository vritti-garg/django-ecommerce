from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # Cart Logic
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),

    path('remove-single/<int:item_id>/', views.remove_single_item, name='remove_single_item'),
    path('remove-item/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    #order logic
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.orders, name='orders'),
    path('order-success/', views.order_success, name='order_success'),
    # Product Detail Page 
    # <int:pk> means "Primary Key" or ID. So it will look for product ID 1, 2, 50, etc
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
]