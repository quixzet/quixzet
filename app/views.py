from django.contrib import messages
from django.contrib.auth import login, logout
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.db.models import Prefetch, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .api import (
    address_data, card_data, cart_item_data, detail_data, form_data,
    order_data, page_data, variant_data,
)
from .forms import (
    AddressForm,
    CheckoutForm,
    ProfileForm,
    SignupForm,
)
from .models import (
    Address,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    UserProfile,
)
from .selectors import catalog_filters, product_list, size_key


SPENT_STATUSES = (Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED)


def _safe_next(request):
    url = request.POST.get("next") or request.GET.get("next")
    if url and url.startswith("/") and not url.startswith("//") and url_has_allowed_host_and_scheme(
        url, allowed_hosts=set(), require_https=request.is_secure()
    ):
        return url
    return None


def _login_redirect(request):
    return redirect_to_login(request.get_full_path().removeprefix("/api"), reverse_lazy("login"))


def login_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _login_redirect(request)
        return view(request, *args, **kwargs)

    return wrapped


class AccountRequiredMixin(LoginRequiredMixin):
    def handle_no_permission(self):
        return _login_redirect(self.request)


class ApiViewMixin:
    def render_to_response(self, context, **kwargs):
        data = self.get_data(context)
        form = context.get("form")
        if form is not None:
            data["form"] = form_data(form)
        status = 422 if form is not None and form.errors else 200
        return page_data(self.request, data, status=status)

    def get_data(self, context):
        return {}


class ProductListView(ApiViewMixin, ListView):
    def get_data(self, context):
        page = context["page_obj"]
        return {
            "products": [card_data(product) for product in page],
            "filters": context["filters"],
            "is_filtered": context["is_filtered"],
            "query_base": context["query_base"],
            "pagination": {
                "count": page.paginator.count,
                "pages": list(page.paginator.page_range),
                "number": page.number,
                "start": page.start_index(),
                "previous": page.previous_page_number() if page.has_previous() else None,
                "next": page.next_page_number() if page.has_next() else None,
            },
        }

    context_object_name = "products"
    paginate_by = 24

    def get_queryset(self):
        return product_list(
            category_slug=self.request.GET.get("category"),
            brand_slug=self.request.GET.get("brand"),
            gender=self.request.GET.get("gender"),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filters"] = catalog_filters(self.request.GET)
        ctx["is_filtered"] = any(
            self.request.GET.get(key) for key in ("category", "brand", "gender")
        )

        query = self.request.GET.copy()
        query.pop("page", None)
        ctx["query_base"] = query.urlencode()
        return ctx


class ProductDetailView(ApiViewMixin, DetailView):
    def get_data(self, context):
        return {
            "product": detail_data(context["product"]),
            "slides_count": context["slides_count"],
            "variants": [{**variant_data(v), "sku": v.sku} for v in context["variants"]],
            "selected_variant_id": context["selected_variant"].id if context["selected_variant"] else None,
            "colors": context["colors"],
            "related": [card_data(product) for product in context["related"]],
        }

    context_object_name = "product"

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("category", "category__parent", "brand")
            .prefetch_related(
                Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True)),
                "images",
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.object
        images = list(product.images.all())
        ctx["images"] = images

        ctx["slides_count"] = max(1, len(images) + (1 if product.model_3d else 0))
        variants = sorted(product.variants.all(), key=size_key)
        ctx["variants"] = variants
        ctx["selected_variant"] = next((v for v in variants if v.stock > 0), None)
        ctx["colors"] = list(dict.fromkeys(v.color for v in variants))
        ctx["related"] = (
            product_list(category_slug=product.category.slug)
            .exclude(pk=product.pk)[:4]
        )
        return ctx


class SignupView(ApiViewMixin, FormView):
    def get_data(self, context):
        return {"next": context["next"]}

    form_class = SignupForm
    success_url = reverse_lazy("product-list")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("product-list")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["next"] = _safe_next(self.request) or ""
        return ctx

    def get_success_url(self):
        return _safe_next(self.request) or super().get_success_url()

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class AppLoginView(ApiViewMixin, LoginView):
    def get_redirect_url(self):
        return _safe_next(self.request) or ""

    def get_data(self, context):
        return {"next": self.get_redirect_url()}

    redirect_authenticated_user = True


@require_POST
def logout_view(request):
    logout(request)
    return redirect("product-list")


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def cart_detail(request):
    cart = _get_cart(request.user)
    items = list(
        cart.items
        .select_related("variant", "variant__product")
        .prefetch_related("variant__product__images")
        .order_by("-added_at")
    )
    total = sum(item.subtotal for item in items if item.is_selected)
    return page_data(request, {
        "items": [cart_item_data(item) for item in items],
        "total": total,
    })


@login_required
@require_POST
def cart_add(request, variant_id=None):

    if variant_id is None:
        try:
            variant_id = int(request.POST.get("variant", ""))
        except ValueError:
            messages.error(request, "выберите размер")
            return redirect(_safe_next(request) or "product-list")

    variant = get_object_or_404(
        ProductVariant.objects.select_related("product"), pk=variant_id, is_active=True
    )
    if variant.stock == 0:
        messages.error(request, "этого размера нет в наличии")
        return redirect("product-detail", slug=variant.product.slug)

    cart = _get_cart(request.user)
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
        defaults={"quantity": 1},
    )
    if not created:
        if item.quantity >= variant.stock:
            messages.info(request, f"больше нет в наличии — в корзине уже {item.quantity} шт.")
            return redirect("cart-detail")
        item.quantity += 1
        item.save(update_fields=["quantity"])

    messages.success(request, f"{variant.product.name.lower()}, {variant.size} — в корзине")
    return redirect("cart-detail")


@login_required
@require_POST
def cart_update(request, item_id):
    cart = _get_cart(request.user)
    item = get_object_or_404(CartItem.objects.select_related("variant"), pk=item_id, cart=cart)
    op = request.POST.get("op")
    if op == "inc":
        if item.quantity < item.variant.stock:
            item.quantity += 1
            item.save(update_fields=["quantity"])
        else:
            messages.info(request, "это всё, что есть в наличии")
    elif op == "dec":
        if item.quantity > 1:
            item.quantity -= 1
            item.save(update_fields=["quantity"])
        else:
            item.delete()
    return redirect("cart-detail")


@login_required
@require_POST
def cart_remove(request, item_id):
    cart = _get_cart(request.user)
    CartItem.objects.filter(pk=item_id, cart=cart).delete()
    return redirect("cart-detail")


class ProfileView(ApiViewMixin, AccountRequiredMixin, TemplateView):
    def get_data(self, context):
        return {
            "spent": context["spent"],
            "orders_count": context["orders_count"],
            "items_count": context["items_count"],
            "recent_orders": [order_data(order) for order in context["recent_orders"]],
        }


    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        orders = user.orders.all()
        ctx["spent"] = (
            orders.filter(status__in=SPENT_STATUSES).aggregate(s=Sum("total"))["s"] or 0
        )
        ctx["orders_count"] = orders.count()
        ctx["items_count"] = (
            OrderItem.objects.filter(order__user=user, order__status__in=SPENT_STATUSES)
            .aggregate(n=Sum("quantity"))["n"] or 0
        )
        ctx["recent_orders"] = orders.prefetch_related("items")[:3]
        return ctx


class ProfileEditView(ApiViewMixin, AccountRequiredMixin, UpdateView):
    form_class = ProfileForm
    success_url = reverse_lazy("profile")

    def get_object(self, queryset=None):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, "профиль обновлён")
        return super().form_valid(form)


class AddressListView(ApiViewMixin, AccountRequiredMixin, ListView):
    def get_data(self, context):
        return {"addresses": [address_data(address) for address in context["addresses"]]}

    context_object_name = "addresses"

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressCreateView(ApiViewMixin, AccountRequiredMixin, CreateView):
    form_class = AddressForm
    success_url = reverse_lazy("profile-addresses")

    @transaction.atomic
    def form_valid(self, form):
        form.instance.user = self.request.user
        if form.cleaned_data.get("is_default"):
            Address.objects.filter(user=self.request.user).update(is_default=False)
        return super().form_valid(form)


class AddressUpdateView(ApiViewMixin, AccountRequiredMixin, UpdateView):
    form_class = AddressForm
    success_url = reverse_lazy("profile-addresses")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    @transaction.atomic
    def form_valid(self, form):
        if form.cleaned_data.get("is_default"):
            Address.objects.filter(user=self.request.user).exclude(pk=self.object.pk).update(is_default=False)
        return super().form_valid(form)


class AddressDeleteView(ApiViewMixin, AccountRequiredMixin, DeleteView):
    def get_data(self, context):
        return {"address": address_data(context["object"])}

    success_url = reverse_lazy("profile-addresses")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class OrderListView(ApiViewMixin, AccountRequiredMixin, ListView):
    def get_data(self, context):
        return {"orders": [order_data(order) for order in context["orders"]]}

    context_object_name = "orders"

    def get_queryset(self):
        return (
            self.request.user.orders
            .prefetch_related("items")
            .order_by("-created_at")
        )


class OrderDetailView(ApiViewMixin, AccountRequiredMixin, DetailView):
    def get_data(self, context):
        return {"order": order_data(context["order"], detail=True)}

    context_object_name = "order"

    def get_queryset(self):
        return self.request.user.orders.prefetch_related(
            "items__variant__product__images"
        )


class CheckoutView(ApiViewMixin, AccountRequiredMixin, FormView):
    def get_data(self, context):
        return {
            "items": [cart_item_data(item) for item in context["items"]],
            "total": context["total"],
            "payment_methods": list(Order.PaymentMethod.choices),
        }

    form_class = CheckoutForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
            if not cart or not cart.items.exists():
                messages.warning(request, "корзина пуста")
                return redirect("cart-detail")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        profile = getattr(user, "profile", None)

        address = user.addresses.first()
        initial["full_name"] = (
            user.get_full_name() or (address.full_name if address else "") or user.username
        )
        if profile and profile.phone:
            initial["phone"] = profile.phone
        elif address:
            initial["phone"] = address.phone
        if address:
            initial["address"] = ", ".join(
                part for part in (address.city, address.street, address.postal_code) if part
            )
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cart = Cart.objects.get(user=self.request.user)
        items = list(
            cart.items
            .select_related("variant", "variant__product")
            .prefetch_related("variant__product__images")
        )
        ctx["items"] = items
        ctx["total"] = sum(i.subtotal for i in items)
        return ctx

    def form_valid(self, form):
        user = self.request.user
        cart = Cart.objects.get(user=user)
        items = list(cart.items.select_related("variant", "variant__product"))

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                full_name=form.cleaned_data["full_name"],
                phone=form.cleaned_data["phone"],
                address=form.cleaned_data["address"],
                comment=form.cleaned_data.get("comment", ""),
                payment_method=form.cleaned_data["payment_method"],
                status=Order.Status.AWAITING_PAYMENT,
                total=sum(i.subtotal for i in items),
            )
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    product_name=item.variant.product.name,
                    size=item.variant.size,
                    color=item.variant.color,
                    price=item.variant.price,
                    quantity=item.quantity,
                )
        return redirect("checkout-payment", order_id=order.id)


class PaymentView(ApiViewMixin, AccountRequiredMixin, TemplateView):
    def get_data(self, context):
        return {"order": order_data(context["order"], detail=True)}


    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["order"] = get_object_or_404(
            Order.objects.prefetch_related("items__variant__product__images"),
            pk=self.kwargs["order_id"], user=self.request.user,
        )
        return ctx


@login_required
@require_POST
def payment_confirm(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    with transaction.atomic():
        updated = Order.objects.filter(pk=order.pk, status=Order.Status.AWAITING_PAYMENT).update(
            status=Order.Status.PAID,
        )
        if updated:
            Cart.objects.filter(user=request.user).delete()
    return redirect("checkout-success", order_id=order.id)


class OrderSuccessView(ApiViewMixin, AccountRequiredMixin, TemplateView):
    def get_data(self, context):
        return {"order": order_data(context["order"])}


    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["order"] = get_object_or_404(
            Order, pk=self.kwargs["order_id"], user=self.request.user
        )
        return ctx
