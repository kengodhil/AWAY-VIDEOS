import json
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import AddAdminForm, PayForm, StudioLoginForm, VideoForm
from .models import Payment, Video
from .snippe import SnippeClient, SnippeError, is_completed
from .utils import ensure_session, session_has_access

User = get_user_model()
staff_required = user_passes_test(lambda u: u.is_authenticated and u.is_staff)


def home(request):
    ensure_session(request)
    videos = Video.objects.all()
    return render(request, "catalog/home.html", {"videos": videos})


def pay_video(request, pk, purpose):
    ensure_session(request)
    purpose = purpose.upper()
    if purpose not in (Payment.Purpose.WATCH, Payment.Purpose.DOWNLOAD):
        raise Http404("Unknown payment purpose")

    video = get_object_or_404(Video, pk=pk)

    if session_has_access(request, video, purpose):
        if purpose == Payment.Purpose.WATCH:
            return redirect("watch_video", pk=video.pk)
        return redirect("download_video", pk=video.pk)

    amount = video.watch_price if purpose == Payment.Purpose.WATCH else video.download_price
    form = PayForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        order_id = uuid.uuid4().hex
        payment = Payment.objects.create(
            session_key=request.session.session_key,
            video=video,
            purpose=purpose,
            order_id=order_id,
            phone=phone,
            amount=amount,
        )

        if settings.SNIPPE_MOCK:
            payment.snippe_message = "Demo mode: confirm payment on the next screen."
            payment.save(update_fields=["snippe_message"])
            messages.info(request, "Demo payment started. Confirm it on the next screen.")
            return redirect("payment_status", order_id=payment.order_id)

        webhook = settings.SNIPPE_WEBHOOK_URL or request.build_absolute_uri(
            reverse("snippe_webhook")
        )
        client = SnippeClient()
        try:
            result = client.create_mobile_payment(
                amount=amount,
                phone=phone,
                webhook_url=webhook,
                metadata={
                    "order_id": order_id,
                    "video_id": str(video.pk),
                    "purpose": purpose,
                },
                idempotency_key=order_id,
            )
            ref = str(result.get("reference") or "")
            payment.snippe_reference = ref
            payment.snippe_message = str(result.get("status") or "pending")
            payment.save(update_fields=["snippe_reference", "snippe_message"])
            messages.success(request, "Check your phone and approve the USSD payment prompt.")
            return redirect("payment_status", order_id=payment.order_id)
        except SnippeError as exc:
            payment.status = Payment.Status.FAILED
            payment.snippe_message = str(exc)
            payment.save(update_fields=["status", "snippe_message"])
            messages.error(request, str(exc))
            return redirect("pay_video", pk=video.pk, purpose=purpose.lower())

    return render(
        request,
        "catalog/pay.html",
        {
            "form": form,
            "video": video,
            "purpose": purpose,
            "amount": amount,
            "is_download": purpose == Payment.Purpose.DOWNLOAD,
        },
    )


def payment_status(request, order_id):
    ensure_session(request)
    payment = get_object_or_404(
        Payment, order_id=order_id, session_key=request.session.session_key
    )
    return render(
        request,
        "catalog/payment_status.html",
        {"payment": payment, "mock": settings.SNIPPE_MOCK},
    )


def payment_status_json(request, order_id):
    ensure_session(request)
    payment = get_object_or_404(
        Payment, order_id=order_id, session_key=request.session.session_key
    )

    if payment.status == Payment.Status.PENDING and not settings.SNIPPE_MOCK:
        if payment.snippe_reference:
            try:
                data = SnippeClient().get_payment(payment.snippe_reference)
                st = data.get("status")
                if is_completed(st):
                    payment.mark_completed(
                        reference=payment.snippe_reference,
                        message=str(st or "completed"),
                    )
                elif str(st or "").lower() in {"failed", "voided", "expired", "cancelled"}:
                    payment.status = Payment.Status.FAILED
                    payment.snippe_message = str(st)
                    payment.save(update_fields=["status", "snippe_message"])
            except SnippeError:
                pass

    next_url = ""
    if payment.status == Payment.Status.COMPLETED:
        if payment.purpose == Payment.Purpose.WATCH:
            next_url = reverse("watch_video", args=[payment.video_id])
        else:
            next_url = reverse("download_video", args=[payment.video_id])

    return JsonResponse(
        {
            "status": payment.status,
            "message": payment.snippe_message,
            "next_url": next_url,
        }
    )


@require_POST
def mock_complete_payment(request, order_id):
    ensure_session(request)
    payment = get_object_or_404(
        Payment, order_id=order_id, session_key=request.session.session_key
    )
    if not settings.SNIPPE_MOCK:
        return redirect("payment_status", order_id=order_id)
    payment.mark_completed(message="Demo payment completed")
    messages.success(request, "Payment successful.")
    if payment.purpose == Payment.Purpose.WATCH:
        return redirect("watch_video", pk=payment.video_id)
    return redirect("download_video", pk=payment.video_id)


@csrf_exempt
@require_POST
def snippe_webhook(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return HttpResponse("bad json", status=400)

    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    reference = str(data.get("reference") or payload.get("reference") or "")
    metadata = data.get("metadata") or payload.get("metadata") or {}
    order_id = str(metadata.get("order_id") or "")
    status = str(data.get("status") or payload.get("status") or "")

    payment = None
    if order_id:
        payment = Payment.objects.filter(order_id=order_id).first()
    if not payment and reference:
        payment = Payment.objects.filter(snippe_reference=reference).first()
    if not payment:
        return HttpResponse("unknown payment", status=404)

    if is_completed(status):
        payment.mark_completed(reference=reference or payment.snippe_reference, message="Paid via Snippe")
    elif status.lower() in {"failed", "voided", "expired", "cancelled"}:
        payment.status = Payment.Status.FAILED
        payment.snippe_message = status
        payment.save(update_fields=["status", "snippe_message"])

    return JsonResponse({"result": "SUCCESS"})


def watch_video(request, pk):
    ensure_session(request)
    video = get_object_or_404(Video, pk=pk)
    if not session_has_access(request, video, Payment.Purpose.WATCH):
        messages.warning(request, "Pay TZS {:,} to watch this video.".format(video.watch_price))
        return redirect("pay_video", pk=video.pk, purpose="watch")
    can_download = session_has_access(request, video, Payment.Purpose.DOWNLOAD)
    return render(
        request,
        "catalog/watch.html",
        {"video": video, "can_download": can_download},
    )


def download_video(request, pk):
    ensure_session(request)
    video = get_object_or_404(Video, pk=pk)
    if not session_has_access(request, video, Payment.Purpose.DOWNLOAD):
        messages.warning(
            request,
            "Pay TZS {:,} to download this video.".format(video.download_price),
        )
        return redirect("pay_video", pk=video.pk, purpose="download")
    if not video.video_file:
        raise Http404("Video file missing")
    response = FileResponse(
        video.video_file.open("rb"),
        as_attachment=True,
        filename=video.video_file.name.split("/")[-1],
    )
    return response


# ─── Studio (branded admin UI) ───────────────────────────────────────────────

def studio_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("studio_dashboard")
    form = StudioLoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if not user.is_staff:
            messages.error(request, "This account is not an admin.")
        else:
            login(request, user)
            return redirect("studio_dashboard")
    return render(request, "catalog/studio_login.html", {"form": form})


def studio_logout(request):
    logout(request)
    messages.info(request, "Signed out.")
    return redirect("home")


@login_required(login_url="/studio/login/")
@staff_required
def studio_dashboard(request):
    videos = list(Video.objects.all())
    payments = list(Payment.objects.select_related("video")[:50])
    payments_count = Payment.objects.count()
    paid_count = Payment.objects.filter(status=Payment.Status.COMPLETED).count()
    admins = list(User.objects.filter(is_staff=True).order_by("username"))
    return render(
        request,
        "catalog/studio_dashboard.html",
        {
            "videos": videos,
            "payments": payments,
            "payments_count": payments_count,
            "paid_count": paid_count,
            "admins": admins,
        },
    )


@login_required(login_url="/studio/login/")
@staff_required
def studio_add_video(request):
    form = VideoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Video uploaded.")
        return redirect("studio_dashboard")
    return render(request, "catalog/studio_video_form.html", {"form": form})


@login_required(login_url="/studio/login/")
@staff_required
@require_POST
def studio_delete_video(request, pk):
    video = get_object_or_404(Video, pk=pk)
    title = video.title
    video.delete()
    messages.success(request, f'Deleted "{title}".')
    return redirect("studio_dashboard")


@login_required(login_url="/studio/login/")
@staff_required
def studio_add_admin(request):
    form = AddAdminForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Admin “{user.username}” created.")
        return redirect("studio_dashboard")
    return render(request, "catalog/studio_add_admin.html", {"form": form})
