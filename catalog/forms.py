from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from .models import Video
from .snippe import normalize_phone

User = get_user_model()


class PayForm(forms.Form):
    phone = forms.CharField(
        max_length=20,
        required=False,
        label="INGIZA NAMBA YA MALIPO",
        widget=forms.TextInput(
            attrs={
                "id": "id_phone",
                "placeholder": "7XXXXXXXX",
                "inputmode": "numeric",
                "autocomplete": "tel",
                "aria-label": "INGIZA NAMBA YA MALIPO",
                "class": "phone-local",
            }
        ),
    )

    def clean_phone(self):
        raw = (self.cleaned_data.get("phone") or "").strip()
        digits = "".join(c for c in raw if c.isdigit())
        if not digits:
            return "255700000000"
        if digits.startswith("255"):
            return digits[:15]
        if digits.startswith("0") and len(digits) >= 10:
            return "255" + digits[1:15]
        if len(digits) == 9:
            return "255" + digits
        return normalize_phone(digits) or digits


class StudioLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Username", "autocomplete": "username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password", "autocomplete": "current-password"})
    )


class VideoForm(forms.ModelForm):
    video_cdn = forms.URLField(
        required=False,
        label="Video URL (optional)",
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://res.cloudinary.com/.../video.mp4",
            }
        ),
        help_text="Paste a direct MP4 link if file upload fails.",
    )
    thumbnail_cdn = forms.URLField(
        required=False,
        label="Thumbnail URL (optional)",
        widget=forms.URLInput(attrs={"placeholder": "https://.../image.jpg"}),
    )

    class Meta:
        model = Video
        fields = (
            "title",
            "description",
            "watch_price",
            "download_price",
            "thumbnail",
            "video_file",
            "video_cdn",
            "thumbnail_cdn",
        )
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Video title"}),
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Short description (optional)"}
            ),
            "watch_price": forms.NumberInput(attrs={"min": 500}),
            "download_price": forms.NumberInput(attrs={"min": 500}),
            "video_file": forms.ClearableFileInput(
                attrs={"accept": "video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov"}
            ),
            "thumbnail": forms.ClearableFileInput(
                attrs={"accept": "image/jpeg,image/png,image/webp,.jpg,.jpeg,.png"}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        f = cleaned.get("video_file")
        url = (cleaned.get("video_cdn") or "").strip()
        if not f and not url and not getattr(self.instance, "video_cdn", None):
            raise forms.ValidationError("Upload a video file or paste a Video URL.")
        if f and f.size and f.size > 100 * 1024 * 1024:
            raise forms.ValidationError("Max 100MB.")
        return cleaned


class AddAdminForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"placeholder": "Username"}))
    email = forms.EmailField(
        required=False, widget=forms.EmailInput(attrs={"placeholder": "Email (optional)"})
    )
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
