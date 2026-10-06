from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Address, Order, UserProfile


# ============================================================
# AUTH
# ============================================================

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="логин",
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "логин",
            "autocomplete": "username",
        }),
    )
    password = forms.CharField(
        label="пароль",
        widget=forms.PasswordInput(attrs={
            "class": "input",
            "placeholder": "пароль",
            "autocomplete": "current-password",
        }),
    )


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        label="почта",
        required=True,
        widget=forms.EmailInput(attrs={
            "class": "input",
            "placeholder": "почта",
            "autocomplete": "email",
        }),
    )

    class Meta:
        model = User
        fields = ("username", "email")
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "логин",
                "autocomplete": "username",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({
            "class": "input",
            "placeholder": "пароль",
            "autocomplete": "new-password",
        })
        self.fields["password2"].widget.attrs.update({
            "class": "input",
            "placeholder": "пароль ещё раз",
            "autocomplete": "new-password",
        })

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с такой почтой уже есть.")
        return email


# ============================================================
# ПРОФИЛЬ
# ============================================================

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("avatar", "phone", "bio")
        widgets = {
            "phone": forms.TelInput(attrs={
                "class": "input",
                "placeholder": "+7 999 123-45-67",
                "autocomplete": "tel",
            }),
            "bio": forms.Textarea(attrs={
                "class": "input input-textarea",
                "placeholder": "пара слов о себе",
                "rows": 3,
                "maxlength": 300,
            }),
        }


# ============================================================
# АДРЕСА
# ============================================================

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            "full_name", "phone", "country", "city",
            "street", "postal_code", "is_default",
        )
        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "input", "placeholder": "Иван Иванов",
                "autocomplete": "name",
            }),
            "phone": forms.TelInput(attrs={
                "class": "input", "placeholder": "+7 999 123-45-67",
                "autocomplete": "tel",
            }),
            "country": forms.TextInput(attrs={
                "class": "input", "placeholder": "Россия",
                "autocomplete": "country-name",
            }),
            "city": forms.TextInput(attrs={
                "class": "input", "placeholder": "Москва",
                "autocomplete": "address-level2",
            }),
            "street": forms.TextInput(attrs={
                "class": "input", "placeholder": "ул. Пушкина, д. 1, кв. 1",
                "autocomplete": "street-address",
            }),
            "postal_code": forms.TextInput(attrs={
                "class": "input", "placeholder": "101000",
                "autocomplete": "postal-code", "inputmode": "numeric",
            }),
        }


# ============================================================
# CHECKOUT
# ============================================================

class CheckoutForm(forms.Form):
    full_name = forms.CharField(
        label="ФИО",
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Иван Иванов",
            "autocomplete": "name",
        }),
    )
    phone = forms.CharField(
        label="Телефон",
        max_length=20,
        widget=forms.TelInput(attrs={
            "class": "input",
            "placeholder": "+7 999 123-45-67",
            "autocomplete": "tel",
        }),
    )
    address = forms.CharField(
        label="Адрес доставки",
        max_length=500,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Город, улица, дом, квартира",
            "autocomplete": "street-address",
        }),
    )
    comment = forms.CharField(
        label="Комментарий",
        required=False,
        widget=forms.Textarea(attrs={
            "class": "input input-textarea",
            "placeholder": "необязательно",
            "rows": 2,
        }),
    )
    payment_method = forms.ChoiceField(
        label="Способ оплаты",
        choices=Order.PaymentMethod.choices,
        widget=forms.RadioSelect(attrs={"class": "radio"}),
    )