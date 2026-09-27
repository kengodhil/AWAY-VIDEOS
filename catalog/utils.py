import re


def normalize_msisdn(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0") and len(digits) == 10:
        digits = "255" + digits[1:]
    if digits.startswith("255") and len(digits) == 12:
        return digits
    raise ValueError("Enter a valid Tanzania mobile number, for example 07XXXXXXXX or 2557XXXXXXXX.")


def user_has_access(user, video) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return user.payments.filter(video=video, status="COMPLETED").exists()
