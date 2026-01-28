# store/context_processors.py
from .models import Cart

def cart_count(request):
    count = 0
    if request.user.is_authenticated:
        try:
            # search user's cart
            cart = Cart.objects.get(user=request.user)
            # total quantity of all items in the cart
            cart_items = cart.items.all()
            for item in cart_items:
                count += item.quantity
        except Cart.DoesNotExist:
            count = 0
    return {'cart_count': count}