from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

from ..models import Order
from ..selectors import size_key

register = template.Library()

NBSP = " "


def _decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


# ============================================================
# ЧИСЛА И ЦЕНЫ
# ============================================================

@register.filter
def rub(value):
    """29990.00 → «29 990 ₽». Копейки показываем, только если они есть."""
    amount = _decimal(value)
    if amount is None:
        return ""
    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole, frac = divmod(abs(amount), 1)
    text = f"{int(whole):,}".replace(",", NBSP)
    if frac:
        text += "," + f"{frac:.2f}"[2:]
    sign = "−" if amount < 0 else ""
    return f"{sign}{text}{NBSP}₽"


@register.filter
def discount(price, old_price):
    """Скидка в процентах: 29990 и 34990 → 14. Пусто, если скидки нет."""
    price, old = _decimal(price), _decimal(old_price)
    if price is None or not old or old <= price:
        return ""
    return int(((old - price) / old * 100).to_integral_value(rounding=ROUND_HALF_UP))


@register.filter
def plural(number, forms):
    """{{ n|plural:"товар,товара,товаров" }} — русское склонение по числу."""
    one, few, many = forms.split(",")
    try:
        n = abs(int(number)) % 100
    except (TypeError, ValueError):
        return many
    if 11 <= n <= 19:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


@register.filter
def pad(value, width=3):
    """7 → «007», {{ n|pad:2 }} → «07»."""
    try:
        return str(int(value)).zfill(int(width))
    except (TypeError, ValueError):
        return value


@register.filter
def sumattr(items, attr):
    """Сумма атрибута по списку: {{ order.items.all|sumattr:"quantity" }}."""
    return sum(getattr(item, attr, 0) or 0 for item in items)


# ============================================================
# ТОВАРЫ И ЗАКАЗЫ
# ============================================================

@register.filter
def by_size(variants):
    """Варианты по размерной сетке: XS, S, M, L… а не по алфавиту."""
    return sorted(variants, key=size_key)


_STEP_INDEX = {
    Order.Status.NEW: 0,
    Order.Status.AWAITING_PAYMENT: 0,
    Order.Status.PAID: 1,
    Order.Status.SHIPPED: 2,
    Order.Status.DELIVERED: 3,
}
_STEP_LABELS = ("оформлен", "оплачен", "в пути", "доставлен")


@register.simple_tag
def order_steps(order):
    """Шаги трекинга заказа. Для отменённого — пустой список."""
    current = _STEP_INDEX.get(order.status)
    if current is None:
        return []
    return [
        {"label": label, "done": i <= current, "current": i == current}
        for i, label in enumerate(_STEP_LABELS)
    ]
