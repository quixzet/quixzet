from django.db.models import Sum

from .models import CartItem


def cart_count(user):
    if user is None or not user.is_authenticated:
        return 0
    total = (
        CartItem.objects.filter(cart__user=user)
        .aggregate(n=Sum("quantity"))["n"]
    )
    return total or 0
