from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.db.models import Prefetch, Sum
from django.shortcuts import get_object_or_404, redirect, render
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

from .forms import (
    AddressForm,
    CheckoutForm,
    LoginForm,
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

# Статусы, по которым деньги уже списаны
SPENT_STATUSES = (Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED)


def _safe_next(request):
    """`next` из формы или адреса — только если он ведёт на наш же сайт."""
    url = request.POST.get("next") or request.GET.get("next")
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return None


# ---------- Каталог ----------

class ProductListView(ListView):
    template_name = "app/product_list.html"
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
        # Параметры фильтра без номера страницы — для ссылок пагинации
        query = self.request.GET.copy()
        query.pop("page", None)
        ctx["query_base"] = query.urlencode()
        return ctx


class ProductDetailView(DetailView):
    template_name = "app/product_detail.html"
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
        # Кадры карусели: 3D-модель (если есть) + фото; пустая галерея — один кадр-заглушка
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


# ---------- Auth ----------

class SignupView(FormView):
    template_name = "app/signup.html"
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


class AppLoginView(LoginView):
    template_name = "app/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def logout_view(request):
    logout(request)
    return redirect("product-list")


# ---------- Корзина ----------

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
    return render(request, "cart/detail.html", {
        "cart": cart,
        "items": items,
        "total": total,
    })


@login_required
@require_POST
def cart_add(request, variant_id=None):
    # Вариант приходит либо в адресе, либо из формы выбора размера
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


# ---------- Профиль: обзор и данные ----------

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "account/dashboard.html"
    login_url = "login"

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


class ProfileEditView(LoginRequiredMixin, UpdateView):
    template_name = "account/profile_edit.html"
    form_class = ProfileForm
    success_url = reverse_lazy("profile")
    login_url = "login"

    def get_object(self, queryset=None):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, "профиль обновлён")
        return super().form_valid(form)


# ---------- Профиль: адреса ----------

class AddressListView(LoginRequiredMixin, ListView):
    template_name = "account/addresses.html"
    context_object_name = "addresses"
    login_url = "login"

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressCreateView(LoginRequiredMixin, CreateView):
    template_name = "account/address_form.html"
    form_class = AddressForm
    success_url = reverse_lazy("profile-addresses")
    login_url = "login"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_edit"] = False
        return ctx

    def form_valid(self, form):
        form.instance.user = self.request.user
        if form.cleaned_data.get("is_default"):
            Address.objects.filter(user=self.request.user).update(is_default=False)
        return super().form_valid(form)


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    template_name = "account/address_form.html"
    form_class = AddressForm
    success_url = reverse_lazy("profile-addresses")
    login_url = "login"

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_edit"] = True
        return ctx

    def form_valid(self, form):
        if form.cleaned_data.get("is_default"):
            Address.objects.filter(user=self.request.user).exclude(pk=self.object.pk).update(is_default=False)
        return super().form_valid(form)


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    template_name = "account/address_confirm_delete.html"
    success_url = reverse_lazy("profile-addresses")
    login_url = "login"

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


# ---------- Профиль: заказы ----------

class OrderListView(LoginRequiredMixin, ListView):
    template_name = "account/orders.html"
    context_object_name = "orders"
    login_url = "login"

    def get_queryset(self):
        return (
            self.request.user.orders
            .prefetch_related("items")
            .order_by("-created_at")
        )


class OrderDetailView(LoginRequiredMixin, DetailView):
    template_name = "account/order_detail.html"
    context_object_name = "order"
    login_url = "login"

    def get_queryset(self):
        return self.request.user.orders.prefetch_related(
            "items__variant__product__images"
        )


# ---------- Checkout ----------

class CheckoutView(LoginRequiredMixin, FormView):
    template_name = "checkout/form.html"
    form_class = CheckoutForm
    login_url = "login"

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
        # Основной адрес из профиля — чтобы не вводить заново
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


class PaymentView(LoginRequiredMixin, TemplateView):
    template_name = "checkout/payment.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["order"] = get_object_or_404(
            Order.objects.prefetch_related("items"),
            pk=self.kwargs["order_id"], user=self.request.user,
        )
        return ctx


@login_required
@require_POST
def payment_confirm(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    with transaction.atomic():
        order.status = Order.Status.PAID
        order.save(update_fields=["status"])
        Cart.objects.filter(user=request.user).delete()
    return redirect("checkout-success", order_id=order.id)


class OrderSuccessView(LoginRequiredMixin, TemplateView):
    template_name = "checkout/success.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["order"] = get_object_or_404(
            Order, pk=self.kwargs["order_id"], user=self.request.user
        )
        return ctx
