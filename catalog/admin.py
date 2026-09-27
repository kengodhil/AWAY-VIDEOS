from django.contrib import admin

from .models import Payment, Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "watch_price", "download_price", "created_at")
    search_fields = ("title",)
    list_filter = ("created_at",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "purpose",
        "phone",
        "amount",
        "status",
        "snippe_reference",
        "created_at",
    )
    list_filter = ("status", "purpose", "created_at")
    search_fields = ("order_id", "phone", "snippe_reference", "session_key")
    readonly_fields = ("created_at", "paid_at")
