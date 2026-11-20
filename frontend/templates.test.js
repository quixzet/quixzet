import assert from 'node:assert/strict';
import test from 'node:test';
import {render} from './templates.js';

const imageUrl = '/media/products/2026/10/dolce.jpg';
const product = {
    name: 'Бомбер',
    category: {name: 'Куртки', slug: 'jackets'},
    images: [{image: {url: imageUrl}, alt: 'Бомбер спереди'}],
};
const variant = {id: 3, size: 'S', price: '129990.00', old_price: '159990.00', stock: 2, sku: 'BOMBER-S'};
const formattedPrice = /129\s990\s₽/;

function productPage(data) {
    return render('app/product_detail.html', {route: 'product-detail', product, ...data});
}

test('карточка выводит фото из товара и цену выбранного размера', () => {
    const html = productPage({
        variants: [{...variant, id: 2, stock: 0, price: '99990.00'}, variant],
        selected_variant_id: variant.id,
    });
    assert.ok(html.includes(`src="${imageUrl}"`));
    assert.ok(!html.includes('фото скоро'));
    assert.match(html, /data-price-now>129\s990\s₽</);
    assert.match(html, /data-price-old-value>159\s990\s₽</);
});

test('карточка без фотографий сохраняет заглушку и цену распроданного размера', () => {
    const html = productPage({
        product: {...product, images: []},
        variants: [{...variant, stock: 0}],
        selected_variant_id: null,
    });
    assert.ok(html.includes('фото скоро'));
    assert.ok(html.includes('нет в наличии'));
    assert.match(html, formattedPrice);
});

test('карточка без вариантов показывает отсутствие продажи', () => {
    assert.ok(productPage({variants: []}).includes('нет в продаже'));
});
