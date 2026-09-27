from .models import Payment


def ensure_session(request):
    """Ensure the visitor has a session key (cookie-based; no DB required)."""
    if not request.session.session_key:
        # Force a key to be assigned without requiring django_session table
        request.session["_away_init"] = True
        request.session.save()
    return request.session.session_key


def session_has_access(request, video, purpose: str) -> bool:
    session_key = request.session.session_key
    if not session_key:
        return False
    return Payment.objects.filter(
        session_key=session_key,
        video=video,
        purpose=purpose,
        status=Payment.Status.COMPLETED,
    ).exists()
