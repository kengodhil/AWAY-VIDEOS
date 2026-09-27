import json
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import LoginForm, PayForm, RegisterForm, VideoForm
from .models import Payment, User, Video
from .selcom import SelcomClient, SelcomError, is_success_result, verify_webhook
from .utils import user_has_access


staff_required = user_passes_test(lambda u: u.is_authenticated and u.is_staff)


def home(request):
    if request.user.is_authenticated:
        return redirect("video_list")
    return render(request, "catalog/home.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("video_list")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome. Choose a video and pay with your phone number.")
        return redirect("video_list")
    return render(request, "catalog/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("video_list")
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get("next") or "video_list")
    return render(request, "catalog/login.html", {"form": form})


@login_required
def video_list(request):
    videos = Video.objects.all()
    paid_ids = set(
        request.user.payments.filter(status=Payment.Status.COMPLETED).values_list("video_id", flat=True)
    )
    return render(request, "catalog/video_list.html", {"videos": videos, "paid_ids": paid_ids})


@login_required
def video_detail(request, pk):
    video = get_object_or_404(Video, pk=pk)
    unlocked = user_has_access(request.user, video)
    return render(request, "catalog/video_detail.html", {"video": video, "unlocked": unlocked})


@login_required
def pay_video(request, pk):
    video = get_object_or_404(Video, pk=pk)
    if user_has_access(request.user, video):
        return redirect("watch_video", pk=video.pk)

    form = PayForm(request.POST or None, initial={"phone": request.user.phone})
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        request.user.phone = phone
        request.user.save(update_fields=["phone"])

        order_id = uuid.uuid4().hex[:16]
        transid = uuid.uuid4().hex[:12].upper()
        payment = Payment.objects.create(
            user=request.user,
            video=video,
            order_id=order_id,
            transid=transid,
            phone=phone,
            amount=video.price,
        )

        if settings.SELCOM_MOCK:
            payment.selcom_message = "Demo mode: waiting for you to confirm payment."
            payment.save(update_fields=["selcom_message"])
            messages.info(request, "Demo payment started. Confirm it on the next screen.")
            return redirect("payment_status", order_id=payment.order_id)

        webhook = settings.SELCOM_WEBHOOK_URL or request.build_absolute_uri(reverse("selcom_webhook"))
        client = SelcomClient()
        try:
            order = client.create_order(
                order_id=order_id,
                buyer_email=request.user.email or f"{request.user.username}@adureel.local",
                buyer_name=request.user.get_full_name() or request.user.username,
                buyer_phone=phone,
                amount=video.price,
                webhook=webhook,
            )
            payment.selcom_reference = str(order.get("reference") or "")
            payment.selcom_message = order.get("message") or ""
            payment.save(update_fields=["selcom_reference", "selcom_message"])
            if str(order.get("result") or "").upper() not in {"SUCCESS", "PENDING"}:
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status"])
                messages.error(request, order.get("message") or "Selcom could not create this order.")
                return redirect("pay_video", pk=video.pk)

            wallet = client.wallet_payment(transid=transid, order_id=order_id, msisdn=phone)
            payment.selcom_message = wallet.get("message") or payment.selcom_message
            payment.save(update_fields=["selcom_message"])
            messages.success(request, "Check your phone and approve the payment prompt.")
            return redirect("payment_status", order_id=payment.order_id)
        except SelcomError as exc:
            payment.status = Payment.Status.FAILED
            payment.selcom_message = str(exc)
            payment.save(update_fields=["status", "selcom_message"])
            messages.error(request, str(exc))
            return redirect("pay_video", pk=video.pk)

    return render(request, "catalog/pay.html", {"form": form, "video": video})


@login_required
def payment_status(request, order_id):
    payment = get_object_or_404(Payment, order_id=order_id, user=request.user)
    return render(
        request,
        "catalog/payment_status.html",
        {"payment": payment, "mock": settings.SELCOM_MOCK},
    )


@login_required
def payment_status_json(request, order_id):
    payment = get_object_or_404(Payment, order_id=order_id, user=request.user)
    if payment.status == Payment.Status.PENDING and not settings.SELCOM_MOCK:
        try:
            data = SelcomClient().order_status(payment.order_id)
            nested = data.get("data") or [{}]
            first = nested[0] if nested else {}
            combined = {**data, **first}
            if is_success_result(combined) or str(first.get("payment_status") or "").upper() == "COMPLETED":
                payment.mark_completed(reference=str(data.get("reference") or ""), message=data.get("message") or "Paid")
            elif str(combined.get("payment_status") or combined.get("result") or "").upper() in {"FAILED", "CANCELLED"}:
                payment.status = combined.get("payment_status") or combined.get("result")
                payment.selcom_message = data.get("message") or ""
                payment.save(update_fields=["status", "selcom_message"])
        except SelcomError:
            pass
    return JsonResponse(
        {
            "status": payment.status,
            "message": payment.selcom_message,
            "watch_url": reverse("watch_video", args=[payment.video_id]) if payment.status == Payment.Status.COMPLETED else "",
        }
    )


@login_required
@require_POST
def mock_complete_payment(request, order_id):
    payment = get_object_or_404(Payment, order_id=order_id, user=request.user)
    if not settings.SELCOM_MOCK:
        return redirect("payment_status", order_id=order_id)
    payment.mark_completed(message="Demo payment completed")
    messages.success(request, "Payment successful. You can now watch the video.")
    return redirect("watch_video", pk=payment.video_id)


@csrf_exempt
@require_POST
def selcom_webhook(request):
    if not settings.SELCOM_MOCK:
        if not verify_webhook(request.headers, request.body, settings.SELCOM_API_SECRET):
            return HttpResponse("invalid signature", status=400)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return HttpResponse("bad json", status=400)

    order_id = payload.get("order_id")
    if not order_id:
        return HttpResponse("missing order", status=400)

    payment = Payment.objects.filter(order_id=order_id).first()
    if not payment:
        return HttpResponse("unknown order", status=404)

    status = str(payload.get("payment_status") or payload.get("result") or "").upper()
    if status == "COMPLETED" or is_success_result(payload):
        payment.mark_completed(reference=str(payload.get("reference") or payload.get("transid") or ""), message="Paid via Selcom")
    elif status in {"FAILED", "CANCELLED"}:
        payment.status = status
        payment.selcom_message = payload.get("message") or status
        payment.save(update_fields=["status", "selcom_message"])
    return JsonResponse({"result": "SUCCESS"})


@login_required
def watch_video(request, pk):
    video = get_object_or_404(Video, pk=pk)
    if not user_has_access(request.user, video):
        messages.warning(request, "Pay for this video first, then you can watch it.")
        return redirect("pay_video", pk=video.pk)
    return render(request, "catalog/watch.html", {"video": video})


@staff_required
def studio(request):
    videos = Video.objects.all()
    users = User.objects.exclude(is_superuser=True).order_by("-date_joined")
    payments = Payment.objects.select_related("user", "video")[:20]
    return render(request, "catalog/studio.html", {"videos": videos, "users": users, "payments": payments})


@staff_required
def add_video(request):
    form = VideoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Video added.")
        return redirect("studio")
    return render(request, "catalog/video_form.html", {"form": form, "heading": "Add a video"})


@staff_required
@require_POST
def delete_video(request, pk):
    video = get_object_or_404(Video, pk=pk)
    title = video.title
    video.delete()
    messages.success(request, f"Deleted “{title}”.")
    return redirect("studio")


@staff_required
@require_POST
def delete_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user or user.is_superuser:
        messages.error(request, "You cannot delete this account.")
        return redirect("studio")
    name = user.get_full_name() or user.username
    user.delete()
    messages.success(request, f"Deleted user {name}.")
    return redirect("studio")
