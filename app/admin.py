from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import (
    Address,
    Brand,
    Cart,
    CartItem,
    Category,
    Order,
    OrderItem,
    Product,
    ProductImage,
    ProductVariant,
    UserProfile,
)


# ---------- Каталог ----------

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("parent",)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("sku", "size", "color", "price", "old_price", "stock", "is_active")


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "brand", "gender", "is_active", "created_at")
    list_filter = ("is_active", "gender", "category", "brand")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("category", "brand")
    inlines = [ProductVariantInline, ProductImageInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "size", "color", "price", "stock", "is_active")
    list_filter = ("is_active", "size", "color")
    search_fields = ("sku", "product__name")
    list_select_related = ("product",)


admin.site.register(Brand)


# ---------- Профиль / Адреса ----------

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "updated_at")
    search_fields = ("user__username", "phone")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "street", "is_default", "created_at")
    list_filter = ("is_default", "country")
    search_fields = ("user__username", "city", "street")
    list_select_related = ("user",)


# ---------- Заказы ----------

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "size", "color", "price", "quantity")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "status", "payment_method", "total", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("number", "user__username", "phone", "full_name")
    readonly_fields = ("number", "created_at", "updated_at")
    list_select_related = ("user",)
    inlines = [OrderItemInline]


# ---------- Корзина ----------

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    search_fields = ("user__username",)
    list_select_related = ("user",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "variant", "quantity", "is_selected")
    list_select_related = ("cart", "variant")