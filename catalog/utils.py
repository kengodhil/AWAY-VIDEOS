import uuid

from .models import Payment


def ensure_session(request):
    if not request.session.session_key:
        request.session["_away_init"] = True
        request.session.save()
    if not request.session.get("visitor_id"):
        request.session["visitor_id"] = uuid.uuid4().hex
        request.session.save()
    return request.session["visitor_id"]


def visitor_id(request) -> str:
    return ensure_session(request)


def session_has_access(request, video, purpose: str) -> bool:
    vid = request.session.get("visitor_id") or request.session.session_key
    if not vid:
        return False
    return Payment.objects.filter(
        session_key=vid,
        video=video,
        purpose=purpose,
        status=Payment.Status.COMPLETED,
    ).exists()
