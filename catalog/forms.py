from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from .models import Video
from .snippe import normalize_phone

User = get_user_model()


class PayForm(forms.Form):
    phone = forms.CharField(
        max_length=20,
        label="",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter number",
                "inputmode": "tel",
                "autocomplete": "tel",
                "aria-label": "Mobile money number",
            }
        ),
    )

    def clean_phone(self):
        raw = self.cleaned_data["phone"].strip()
        normalized = normalize_phone(raw)
        if not (normalized.startswith("255") and len(normalized) == 12):
            raise forms.ValidationError(
                "Enter a valid Tanzania mobile number (e.g. 07XXXXXXXX)."
            )
        return normalized


class StudioLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Username", "autocomplete": "username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password", "autocomplete": "current-password"})
    )


class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ("title", "description", "watch_price", "download_price", "thumbnail", "video_file")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Video title"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Short description (optional)"}),
            "watch_price": forms.NumberInput(attrs={"min": 500}),
            "download_price": forms.NumberInput(attrs={"min": 500}),
        }


class AddAdminForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"placeholder": "Username"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"placeholder": "Email (optional)"}))
    password = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={"placeholder": "Password (min 6 characters)"}),
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm password"}),
        label="Confirm password",
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password_confirm")
        if p1 and p2 and p1 != p2:
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data.get("email") or "",
            password=self.cleaned_data["password"],
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])
        return user
