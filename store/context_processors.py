# store/context_processors.py
from .models import Cart

def cart_count(request):
    count = 0
    if request.user.is_authenticated:
        try:
            # User ki cart dhundo
            cart = Cart.objects.get(user=request.user)
            # Saare items ki quantity total karo
            cart_items = cart.items.all()
            for item in cart_items:
                count += item.quantity
        except Cart.DoesNotExist:
            count = 0
    return {'cart_count': count}