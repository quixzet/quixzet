from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Address, Order, UserProfile


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с такой почтой уже есть.")
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("avatar", "phone", "bio")


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            "full_name", "phone", "country", "city",
            "street", "postal_code", "is_default",
        )


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=200)
    phone = forms.CharField(max_length=20)
    address = forms.CharField(max_length=500)
    comment = forms.CharField(required=False)
    payment_method = forms.ChoiceField(choices=Order.PaymentMethod.choices)
