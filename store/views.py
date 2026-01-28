from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.views import View
from .forms import SignUpForm
from .models import Product, Category, Order, Cart, CartItem
from django.contrib.auth.decorators import login_required
from .forms import CheckoutForm
from django.shortcuts import render, redirect, get_object_or_404

@login_required(login_url='/login/')

def orders(request):
    # Show orders of current user (order_by -date)
    orders = Order.objects.filter(user=request.user).order_by('-date')
    return render(request, 'orders.html', {'orders': orders})

def checkout(request):
    # 1. Get the user's cart
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

            # --- LOGICAL TRANSACTION START ---
            for item in cart_items:
                # A. Check Stock one last time
                if item.product.inventory >= item.quantity:
                    
                    # B. Create Order Record
                    Order.objects.create(
                        user=request.user,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price, # Lock the price at time of purchase
                        address=address,
                        phone=phone,
                        status=False # Not delivered yet
                    )

                    # C. Deduct Inventory
                    item.product.inventory -= item.quantity
                    item.product.save()

                else:
                    # Logic Error: Item went out of stock while in cart
                    messages.error(request, f"Sorry, {item.product.name} is out of stock.")
                    return redirect('view_cart')

            # D. Empty the Cart (Delete the Cart Object entirely or just items)
            cart.delete() 
            
            messages.success(request, "Order Placed Successfully!")
            return redirect('order_success') 
            # --- LOGICAL TRANSACTION END ---
            
    else:
        form = CheckoutForm()
        # Calculate total for display
        total = cart.total_price

    return render(request, 'checkout.html', {'form': form, 'cart_items': cart_items, 'total': total})

# --- 1. SIGNUP VIEW ---
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Auto-login after signup
            return redirect('homepage')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

# --- 2. LOGIN VIEW ---
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            # Get the user and log them in
            user = form.get_user()
            login(request, user)
            
            # Redirect to where they wanted to go, or homepage
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            else:
                return redirect('homepage')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

# --- 3. LOGOUT VIEW ---
def logout_view(request):
    logout(request)
    return redirect('homepage')

# --- 4. HOMEPAGE (Catalog) ---
def homepage(request):
    products = Product.objects.all()
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    # 2. Filter by Search Query 
    query = request.GET.get('q')
    if query:
        # 'name__icontains' means search inside the name (case-insensitive)
        products = products.filter(name__icontains=query)

    categories = Category.objects.all()
    
    # pass 'query' so that search box can keeps the value
    context = {
        'products': products, 
        'categories': categories,
        'query': query 
    }
        
    return render(request, 'index.html', context)
# --- ADD TO CART VIEW ---
@login_required(login_url='/login/') # ensure that the user is logined in
def add_to_cart(request, product_id):
    user = request.user
    product = Product.objects.get(id=product_id)
    
    # 1. Get or Create Cart for this User
    cart, created = Cart.objects.get_or_create(user=user)
    
    # 2. Check if item already exists in cart
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not item_created:
        # if was already there, just increase quantity
        cart_item.quantity += 1
        cart_item.save()
    
    return redirect('homepage')

# --- VIEW CART PAGE ---
@login_required(login_url='/login/')
def view_cart(request):
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
    # 1. Fetch the specific item
    try:
        cart_item = CartItem.objects.get(id=item_id)
        
        # 2. Security Check: Ensure this item belongs to the logged-in user's cart
        if cart_item.cart.user == request.user:
            cart_item.delete()
    except CartItem.DoesNotExist:
        pass # If item doesn't exist, just ignore
    
    # 3. Go back to cart page
    return redirect('view_cart')
@login_required(login_url='/login/')
def remove_single_item(request, item_id):
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

def order_success(request):
    return render(request, 'success.html')

def product_detail(request, pk):
    # This tries to get the product, or shows a 404 error page if not found
    product = get_object_or_404(Product, pk=pk)
    # Logic: Same category, but exclude the current product, limit to 4 items
    related_products = Product.objects.filter(category=product.category).exclude(id=pk)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'product_detail.html', context)