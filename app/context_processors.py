from django.db.models import Sum

from .models import CartItem


def cart(request):
    """Сколько вещей в корзине — для счётчика в шапке."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"cart_count": 0}
    total = (
        CartItem.objects.filter(cart__user=user)
        .aggregate(n=Sum("quantity"))["n"]
    )
    return {"cart_count": total or 0}
