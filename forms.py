from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User, Video
from .utils import normalize_msisdn


class StyledFormMixin:
    def _style(self):
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} field-input".strip()


class RegisterForm(StyledFormMixin, UserCreationForm):
    phone = forms.CharField(label="Mobile number", help_text="Use 07XXXXXXXX or 2557XXXXXXXX")

    class Meta:
        model = User
        fields = ("phone", "username", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = "This is how you sign in."
        self.fields["password1"].help_text = "At least 6 characters."
        self._style()

    def clean_phone(self):
        return normalize_msisdn(self.cleaned_data["phone"])

    


class LoginForm(StyledFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username"
        self.fields["password"].label = "Password"
        self._style()


class PayForm(StyledFormMixin, forms.Form):
    phone = forms.CharField(label="Mobile money number", help_text="You will receive a payment prompt on this phone.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_phone(self):
        return normalize_msisdn(self.cleaned_data["phone"])


class VideoForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Video
        fields = ("title", "description", "price", "thumbnail", "video_file")
        labels = {
            "title": "Video title",
            "description": "Short description",
            "price": "Price (TZS)",
            "thumbnail": "Cover image (optional)",
            "video_file": "Video file",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].widget.attrs["rows"] = 4
        self._style()
