import uuid

from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


# ============================================================
# БАЗОВЫЕ
# ============================================================

class TimeStampedModel(models.Model):
    """Абстрактная база: created/updated."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ============================================================
# КАТАЛОГ
# ============================================================

class Category(TimeStampedModel):
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        indexes = [models.Index(fields=["is_active", "parent"])]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Brand(TimeStampedModel):
    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    logo = models.ImageField(upload_to="brands/", blank=True, null=True)

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"

    def __str__(self) -> str:
        return self.name


class Product(TimeStampedModel):
    class Gender(models.TextChoices):
        MEN = "men", "Мужское"
        WOMEN = "women", "Женское"
        UNISEX = "unisex", "Унисекс"
        KIDS = "kids", "Детское"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="products",
    )
    gender = models.CharField(
        max_length=10, choices=Gender.choices, default=Gender.UNISEX,
        db_index=True,
    )
    model_3d = models.FileField(
        "3D-модель",
        upload_to="products/3d/",
        blank=True,
        validators=[FileExtensionValidator(["glb"])],
        help_text="Файл .glb. Держите до ~5 МБ — тяжёлые модели сначала сожмите.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        indexes = [
            models.Index(fields=["is_active", "category"]),
            models.Index(fields=["is_active", "brand"]),
            models.Index(fields=["is_active", "gender"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:280]
        super().save(*args, **kwargs)


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=64, unique=True)
    size = models.CharField(max_length=16, db_index=True)
    color = models.CharField(max_length=32, db_index=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Вариант товара"
        verbose_name_plural = "Варианты товаров"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "size", "color"],
                name="uniq_variant_per_product_size_color",
            ),
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="variant_price_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["size", "color"]),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} [{self.size}/{self.color}]"


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/%Y/%m/")
    alt = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"
        ordering = ["-is_main", "position", "id"]
        indexes = [models.Index(fields=["product", "is_main"])]

    def __str__(self) -> str:
        return f"Image for {self.product_id}"


# ============================================================
# КОРЗИНА
# ============================================================

class Cart(models.Model):
    user = models.OneToOneField(
        "auth.User", on_delete=models.CASCADE, related_name="cart",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self) -> str:
        return f"Cart of {self.user}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items"
    )
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    is_selected = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Позиция корзины"
        verbose_name_plural = "Позиции корзины"
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "variant"],
                name="uniq_cart_variant",
            ),
        ]
        indexes = [models.Index(fields=["cart", "is_selected"])]

    def __str__(self) -> str:
        return f"{self.variant} × {self.quantity}"

    @property
    def subtotal(self):
        return self.variant.price * self.quantity


# ============================================================
# ПРОФИЛЬ
# ============================================================

def avatar_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"avatars/{instance.user_id}/avatar.{ext}"


class UserProfile(models.Model):
    user = models.OneToOneField(
        "auth.User", on_delete=models.CASCADE, related_name="profile",
    )
    avatar = models.ImageField(
        upload_to=avatar_upload_path, blank=True, null=True,
    )
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True, max_length=300)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self) -> str:
        return f"Profile of {self.user.username}"

    @property
    def avatar_url(self) -> str | None:
        if self.avatar:
            return self.avatar.url
        return None


# ============================================================
# АДРЕСА
# ============================================================

class Address(models.Model):
    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="addresses"
    )
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    country = models.CharField(max_length=64, default="Россия")
    city = models.CharField(max_length=128)
    street = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Адрес"
        verbose_name_plural = "Адреса"
        ordering = ["-is_default", "-created_at"]

    def __str__(self) -> str:
        return f"{self.city}, {self.street}"


# ============================================================
# ЗАКАЗЫ
# ============================================================

class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новый"
        AWAITING_PAYMENT = "awaiting_payment", "Ожидает оплаты"
        PAID = "paid", "Оплачен"
        SHIPPED = "shipped", "Отправлен"
        DELIVERED = "delivered", "Доставлен"
        CANCELLED = "cancelled", "Отменён"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Банковская карта"
        SBP = "sbp", "СБП"
        CASH = "cash", "При получении"

    number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        "auth.User", on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.NEW, db_index=True
    )
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, blank=True
    )

    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=500)
    comment = models.TextField(blank=True)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Заказ {self.number}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = f"QX-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items"
    )
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, related_name="order_items"
    )
    product_name = models.CharField(max_length=255)
    size = models.CharField(max_length=16)
    color = models.CharField(max_length=32)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self) -> str:
        return f"{self.product_name} × {self.quantity}"

    @property
    def subtotal(self):
        return self.price * self.quantity