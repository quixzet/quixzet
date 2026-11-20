from django.contrib.messages import get_messages
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.cache import add_never_cache_headers
from django.utils.timezone import localtime

from .cart import cart_count
from .selectors import size_key


def file_data(field):
    return {"url": field.url} if field else None


def fields(instance, names):
    return {name: getattr(instance, name) for name in names.split()}


def image_data(image):
    return {"image": file_data(image.image), "alt": image.alt}


def variant_data(variant):
    return fields(variant, "id size color price old_price stock")


def product_data(product):
    return {
        **fields(product, "name slug"),
        "images": [image_data(image) for image in product.images.all()],
    }


def card_data(product):
    variants = list(product.variants.all())
    return {
        **product_data(product),
        **fields(product, "price_min price_max stock_total"),
        "brand": fields(product.brand, "name") if product.brand else None,
        "has_model": bool(product.model_3d),
        "cheapest": variant_data(variants[0]) if variants else None,
        "variants": [variant_data(variant) for variant in sorted(variants, key=size_key)],
    }


def detail_data(product):
    category = fields(product.category, "name slug")
    parent = product.category.parent
    category["parent"] = fields(parent, "name slug") if parent else None
    return {
        **product_data(product),
        "description": product.description,
        "category": category,
        "brand": fields(product.brand, "name") if product.brand else None,
        "gender_label": product.get_gender_display(),
        "model_3d": file_data(product.model_3d),
    }


def cart_item_data(item):
    return {
        **fields(item, "id quantity subtotal"),
        "variant": {
            **variant_data(item.variant),
            "product": product_data(item.variant.product),
        },
    }


def address_data(address):
    return fields(address, "id full_name phone country city street postal_code is_default")


def order_data(order, *, detail=False):
    items = order.items.all()
    data = {
        **fields(order, "id number status total"),
        "created_at": localtime(order.created_at),
        "status_label": order.get_status_display(),
        "item_count": sum(item.quantity for item in items),
    }
    if detail:
        data.update(fields(order, "full_name phone address comment"))
        data["payment_label"] = order.get_payment_method_display()
        data["items"] = [
            {
                **fields(item, "product_name size color price quantity subtotal"),
                "product": product_data(item.variant.product),
            }
            for item in items
        ]
    return data


def form_data(form):
    values = {
        name: form[name].value()
        for name in form.fields
        if name not in {"password", "password1", "password2", "avatar"}
    }
    return {
        "values": values,
        "errors": {name: [str(error) for error in errors] for name, errors in form.errors.items()},
    }


def response(data, status=200):
    result = JsonResponse(data, status=status)
    add_never_cache_headers(result)
    return result


def page_data(request, data=None, *, status=200):
    user = request.user
    account = None
    if user.is_authenticated:
        profile = getattr(user, "profile", None)
        account = {
            **fields(user, "username email"),
            "date_joined": localtime(user.date_joined),
            "avatar": file_data(profile.avatar) if profile else None,
        }
    return response({
        "user": account,
        "cart_count": cart_count(user),
        "csrf_token": get_token(request),
        "messages": [{"text": str(message), "tags": message.tags} for message in get_messages(request)],
        **(data or {}),
    }, status=status)


def session_data(request):
    return page_data(request)


def api_not_found(request, exception):
    return response({"error": "Не найдено"}, status=404)


def csrf_failure(request, reason=""):
    if request.path.startswith("/api/"):
        return response({"error": "Обновите страницу и повторите действие."}, status=403)
    from django.views.csrf import csrf_failure as django_csrf_failure

    return django_csrf_failure(request, reason=reason)
