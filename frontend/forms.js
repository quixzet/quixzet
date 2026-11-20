const username = {placeholder: 'логин', autocomplete: 'username', required: true};
const phone = {type: 'tel', placeholder: '+7 999 123-45-67', autocomplete: 'tel', max: 20};
const fullName = {placeholder: 'Иван Иванов', autocomplete: 'name', max: 200, required: true};
const address = {
    full_name: fullName,
    phone: {...phone, required: true},
    country: {placeholder: 'Россия', autocomplete: 'country-name', max: 64, required: true},
    city: {placeholder: 'Москва', autocomplete: 'address-level2', max: 128, required: true},
    street: {placeholder: 'ул. Пушкина, д. 1, кв. 1', autocomplete: 'street-address', max: 255, required: true},
    postal_code: {placeholder: '101000', autocomplete: 'postal-code', max: 20, required: true},
};

export const formFields = {
    login: {
        username,
        password: {type: 'password', placeholder: 'пароль', autocomplete: 'current-password', required: true},
    },
    signup: {
        username: {...username, max: 150},
        email: {type: 'email', placeholder: 'почта', autocomplete: 'email', required: true},
        password1: {type: 'password', placeholder: 'пароль', autocomplete: 'new-password', required: true},
        password2: {type: 'password', placeholder: 'пароль ещё раз', autocomplete: 'new-password', required: true},
    },
    'profile-edit': {
        phone,
        bio: {type: 'textarea', placeholder: 'пара слов о себе', rows: 3, max: 300},
    },
    'profile-address-create': address,
    'profile-address-edit': address,
    checkout: {
        full_name: fullName,
        phone: {...phone, required: true},
        address: {placeholder: 'Город, улица, дом, квартира', autocomplete: 'street-address', max: 500, required: true},
        comment: {type: 'textarea', placeholder: 'необязательно', rows: 2},
    },
};
