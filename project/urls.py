from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from app.views import (
    AddressCreateView,
    AddressDeleteView,
    AddressListView,
    AddressUpdateView,
    AppLoginView,
    CheckoutView,
    OrderDetailView,
    OrderListView,
    OrderSuccessView,
    PaymentView,
    ProductDetailView,
    ProductListView,
    ProfileEditView,
    ProfileView,
    SignupView,
    cart_add,
    cart_detail,
    cart_remove,
    cart_update,
    logout_view,
    payment_confirm,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # ---------- Каталог ----------
    path("", ProductListView.as_view(), name="product-list"),
    path("p/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),

    # ---------- Auth ----------
    path("login/", AppLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("signup/", SignupView.as_view(), name="signup"),

    # ---------- Корзина ----------
    path("cart/", cart_detail, name="cart-detail"),
    path("cart/add/", cart_add, name="cart-add-selected"),
    path("cart/add/<int:variant_id>/", cart_add, name="cart-add"),
    path("cart/update/<int:item_id>/", cart_update, name="cart-update"),
    path("cart/remove/<int:item_id>/", cart_remove, name="cart-remove"),

    # ---------- Профиль ----------
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", ProfileEditView.as_view(), name="profile-edit"),
    path("profile/addresses/", AddressListView.as_view(), name="profile-addresses"),
    path("profile/addresses/new/", AddressCreateView.as_view(), name="profile-address-create"),
    path("profile/addresses/<int:pk>/edit/", AddressUpdateView.as_view(), name="profile-address-edit"),
    path("profile/addresses/<int:pk>/delete/", AddressDeleteView.as_view(), name="profile-address-delete"),
    path("profile/orders/", OrderListView.as_view(), name="profile-orders"),
    path("profile/orders/<int:pk>/", OrderDetailView.as_view(), name="profile-order-detail"),

    # ---------- Checkout ----------
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("checkout/pay/<int:order_id>/", PaymentView.as_view(), name="checkout-payment"),
    path("checkout/pay/<int:order_id>/confirm/", payment_confirm, name="checkout-pay-confirm"),
    path("checkout/success/<int:order_id>/", OrderSuccessView.as_view(), name="checkout-success"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)