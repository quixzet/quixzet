export const routes = [
    ['product-list', '/', 'app/product_list.html'],
    ['product-detail', '/p/:slug/', 'app/product_detail.html'],
    ['login', '/login/', 'app/login.html'],
    ['logout', '/logout/'],
    ['signup', '/signup/', 'app/signup.html'],
    ['cart-detail', '/cart/', 'cart/detail.html'],
    ['cart-add-selected', '/cart/add/'],
    ['cart-add', '/cart/add/:id/'],
    ['cart-update', '/cart/update/:id/'],
    ['cart-remove', '/cart/remove/:id/'],
    ['profile', '/profile/', 'account/dashboard.html'],
    ['profile-edit', '/profile/edit/', 'account/profile_edit.html'],
    ['profile-addresses', '/profile/addresses/', 'account/addresses.html'],
    ['profile-address-create', '/profile/addresses/new/', 'account/address_form.html'],
    ['profile-address-edit', '/profile/addresses/:id/edit/', 'account/address_form.html'],
    ['profile-address-delete', '/profile/addresses/:id/delete/', 'account/address_confirm_delete.html'],
    ['profile-orders', '/profile/orders/', 'account/orders.html'],
    ['profile-order-detail', '/profile/orders/:id/', 'account/order_detail.html'],
    ['checkout', '/checkout/', 'checkout/form.html'],
    ['checkout-payment', '/checkout/pay/:id/', 'checkout/payment.html'],
    ['checkout-pay-confirm', '/checkout/pay/:id/confirm/'],
    ['checkout-success', '/checkout/success/:id/', 'checkout/success.html'],
];

const paths = new Map(routes.map(([name, path]) => [name, path]));

export function url(name, value) {
    return paths.get(name).replace(/:\w+/, () => encodeURIComponent(value));
}
