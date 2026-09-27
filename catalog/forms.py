from django import forms

from .snippe import normalize_phone


class PayForm(forms.Form):
    phone = forms.CharField(
        max_length=20,
        label="Mobile money number",
        widget=forms.TextInput(
            attrs={
                "placeholder": "07XXXXXXXX or 2557XXXXXXXX",
                "inputmode": "tel",
                "autocomplete": "tel",
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
