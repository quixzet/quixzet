from django.db.models import F, Max, Min, Prefetch, Q, QuerySet, Sum

from .models import Brand, Category, Product, ProductImage, ProductVariant

# Порядок размеров в сетке; всё, чего тут нет, — после, по числу или по алфавиту
_SIZE_RANK = {
    "XXS": 0, "XS": 1, "S": 2, "M": 3, "L": 4, "XL": 5,
    "XXL": 6, "2XL": 6, "XXXL": 7, "3XL": 7, "4XL": 8,
}


def size_key(variant):
    size = variant.size.strip().upper()
    if size in _SIZE_RANK:
        return (0, _SIZE_RANK[size], "")
    try:
        return (1, float(size.replace(",", ".")), "")
    except ValueError:
        return (2, 0, size)


def product_list(
    *,
    category_slug: str | None = None,
    brand_slug: str | None = None,
    gender: str | None = None,
) -> QuerySet[Product]:
    """
    Список активных товаров с префетчем вариантов и фото.
    Всё, что нужно для карточки в каталоге, — без N+1:
    price_min / price_max / stock_total считаются в одном запросе.
    """
    active_variants = Q(variants__is_active=True)
    qs = (
        Product.objects.filter(is_active=True)
        .select_related("category", "brand")
        .annotate(
            price_min=Min("variants__price", filter=active_variants),
            price_max=Max("variants__price", filter=active_variants),
            stock_total=Sum("variants__stock", filter=active_variants),
        )
        .prefetch_related(
            # Самый дешёвый вариант первым — из него берём старую цену
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.filter(is_active=True)
                .order_by("price", "id")
                .only("id", "product_id", "size", "color", "price", "old_price", "stock"),
            ),
            # Главное фото первым (ordering модели), второе — для смены при наведении
            Prefetch(
                "images",
                queryset=ProductImage.objects.only(
                    "id", "product_id", "image", "alt", "is_main", "position"
                ),
            ),
        )
    )
    if category_slug:
        # Родительская категория показывает и товары дочерних
        qs = qs.filter(
            Q(category__slug=category_slug) | Q(category__parent__slug=category_slug)
        )
    if brand_slug:
        qs = qs.filter(brand__slug=brand_slug)
    if gender:
        qs = qs.filter(gender=gender)
    return qs.order_by("-created_at")


def catalog_filters(params) -> list[dict]:
    """
    Группы чипов для фильтра каталога. Показываем только значения,
    по которым реально есть товары, и только группы, где есть выбор.
    """
    active = Product.objects.filter(is_active=True)

    def chip_url(key, value):
        query = params.copy()
        query.pop("page", None)
        if value is None:
            query.pop(key, None)
        else:
            query[key] = value
        encoded = query.urlencode()
        return f"?{encoded}" if encoded else "?"

    def group(key, label, options):
        if len(options) < 2:
            return None
        current = params.get(key)
        chips = [{"label": "всё", "url": chip_url(key, None), "active": not current}]
        chips += [
            {"label": text, "url": chip_url(key, value), "active": current == value}
            for value, text in options
        ]
        return {"label": label, "chips": chips}

    category_ids = set(active.values_list("category_id", flat=True))
    parent_ids = set(
        Category.objects.filter(id__in=category_ids, parent__isnull=False)
        .values_list("parent_id", flat=True)
    )
    categories = (
        Category.objects.filter(is_active=True, id__in=category_ids | parent_ids)
        .order_by(F("parent_id").asc(nulls_first=True), "name")
    )

    genders = set(active.values_list("gender", flat=True))
    brands = Brand.objects.filter(products__is_active=True).distinct().order_by("name")

    groups = [
        group("category", "категория", [(c.slug, c.name.lower()) for c in categories]),
        group("gender", "для кого", [
            (value, text.lower())
            for value, text in Product.Gender.choices if value in genders
        ]),
        group("brand", "бренд", [(b.slug, b.name.lower()) for b in brands]),
    ]
    return [g for g in groups if g]
