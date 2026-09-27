from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Payment, User, Video


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (("Contact", {"fields": ("phone",)}),)
    list_display = ("username", "email", "phone", "is_staff")


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "created_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order_id", "user", "video", "amount", "status", "created_at")
    list_filter = ("status",)
