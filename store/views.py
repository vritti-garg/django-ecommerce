from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.views import View
from .forms import SignUpForm, CheckoutForm
from .models import Product, Category, Order, Cart, CartItem
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

# ==========================================
# AUTHENTICATION VIEWS
# ==========================================

def signup_view(request):
    """
    Handles user registration.
    If valid, creates a user and logs them in automatically.
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Auto-login after successful signup
            return redirect('homepage')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    """
    Handles user login.
    Note: We pass 'request' to AuthenticationForm to support security middleware 
    like 'django-axes' which tracks IP addresses for brute-force protection.
    """
    if request.method == 'POST':
        # Security Fix: Pass 'request' first so Axes can track the attempt
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            # Retrieve the user object and create a session
            user = form.get_user()
            login(request, user)
            
            # Redirect to the previous page if available, otherwise Homepage
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            else:
                return redirect('homepage')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """
    Logs out the user and clears the session.
    """
    logout(request)
    return redirect('homepage')


# ==========================================
# PRODUCT & CATALOG VIEWS
# ==========================================

def homepage(request):
    """
    Displays the product catalog with filtering and pagination.
    Supports filtering by Category and Search Query.
    """
    products = Product.objects.all()
    
    # 1. Filter by Category ID
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    # 2. Filter by Search Query (Case-Insensitive)
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)

    # 3. Pagination Logic (Show 12 products per page)
    paginator = Paginator(products, 12) 
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)

    # Fetch categories for the sidebar/filter menu
    categories = Category.objects.all()
    
    context = {
        'products': products_page, 
        'categories': categories,
        'query': query  # Pass query back to template to keep search box populated
    }
        
    return render(request, 'index.html', context)


def product_detail(request, pk):
    """
    Displays a single product's details.
    Also fetches 4 related products from the same category.
    """
    # Gracefully handle 404 errors if product ID doesn't exist
    product = get_object_or_404(Product, pk=pk)
    
    # Fetch related products: Same category, exclude current product, limit to 4
    related_products = Product.objects.filter(category=product.category).exclude(id=pk)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'product_detail.html', context)


# ==========================================
# CART MANAGEMENT VIEWS
# ==========================================

@login_required(login_url='/login/')
def add_to_cart(request, product_id):
    """
    Adds a product to the user's persistent database cart.
    If the item exists, increments quantity. If not, creates a new line item.
    """
    user = request.user
    product = Product.objects.get(id=product_id)
    
    # 1. Get or Create a Cart for the logged-in user
    cart, created = Cart.objects.get_or_create(user=user)
    
    # 2. Get or Create a CartItem for the specific product
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not item_created:
        # If item was already in cart, just increment quantity
        cart_item.quantity += 1
        cart_item.save()
    
    return redirect('homepage')


@login_required(login_url='/login/')
def view_cart(request):
    """
    Displays the user's cart and calculates the total price.
    """
    try:
        cart = Cart.objects.get(user=request.user)
        items = cart.items.all()
        total = cart.total_price
    except Cart.DoesNotExist:
        cart = None
        items = []
        total = 0
    
    return render(request, 'cart.html', {'cart': cart, 'items': items, 'total': total})


@login_required(login_url='/login/')
def remove_from_cart(request, item_id):
    """
    Completely removes a specific item from the cart.
    Includes a security check to ensure the item belongs to the user.
    """
    try:
        cart_item = CartItem.objects.get(id=item_id)
        
        # Security Check: Prevent users from deleting other users' items via ID manipulation
        if cart_item.cart.user == request.user:
            cart_item.delete()
    except CartItem.DoesNotExist:
        pass  # Silently ignore if item doesn't exist
    
    return redirect('view_cart')


@login_required(login_url='/login/')
def remove_single_item(request, item_id):
    """
    Decrements the quantity of an item by 1.
    If quantity reaches 0, the item is removed entirely.
    """
    try:
        cart_item = CartItem.objects.get(id=item_id)
        if cart_item.cart.user == request.user:
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
    except CartItem.DoesNotExist:
        pass
    return redirect('view_cart')


# ==========================================
# CHECKOUT & ORDER VIEWS
# ==========================================

def checkout(request):
    """
    Handles the Checkout process.
    1. Validates the Address Form.
    2. Performs a final Inventory Check.
    3. Creates Order records.
    4. Deducts Inventory.
    5. Clears the Cart.
    """
    # 1. Retrieve the user's cart
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all()
    except Cart.DoesNotExist:
        return redirect('homepage')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            address = form.cleaned_data.get('address')
            phone = form.cleaned_data.get('phone')

            # --- TRANSACTION LOGIC START ---
            for item in cart_items:
                # A. Final Stock Check (Race Condition Mitigation)
                if item.product.inventory >= item.quantity:
                    
                    # B. Create Order Record
                    Order.objects.create(
                        user=request.user,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price, # Lock the price at time of purchase
                        address=address,
                        phone=phone,
                        status=False # Default status: Pending/Not Delivered
                    )

                    # C. Deduct Inventory
                    item.product.inventory -= item.quantity
                    item.product.save()

                else:
                    # Logic Error: Item went out of stock during checkout process
                    messages.error(request, f"Sorry, {item.product.name} is out of stock.")
                    return redirect('view_cart')

            # D. Clear the Cart after successful order
            cart.delete() 
            
            messages.success(request, "Order Placed Successfully!")
            return redirect('order_success') 
            # --- TRANSACTION LOGIC END ---
            
    else:
        form = CheckoutForm()
        # Calculate total for display on checkout page
        total = cart.total_price

    return render(request, 'checkout.html', {'form': form, 'cart_items': cart_items, 'total': total})


def order_success(request):
    """
    Displays a static success page after purchase.
    """
    return render(request, 'success.html')


@login_required(login_url='/login/')
def orders(request):
    """
    Displays order history for the current user.
    Sorted by newest first.
    """
    orders = Order.objects.filter(user=request.user).order_by('-date')
    return render(request, 'orders.html', {'orders': orders})