from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True, help_text="Mobile money number, e.g. 2557XXXXXXXX")

    def __str__(self):
        return self.get_full_name() or self.username


class Video(models.Model):
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    price = models.PositiveIntegerField(help_text="Price in Tanzanian Shillings (TZS)")
    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True)
    video_file = models.FileField(upload_to="videos/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="payments")
    order_id = models.CharField(max_length=40, unique=True)
    transid = models.CharField(max_length=40, blank=True)
    phone = models.CharField(max_length=20)
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=8, default="TZS")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    selcom_reference = models.CharField(max_length=64, blank=True)
    selcom_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_completed(self, reference="", message=""):
        self.status = self.Status.COMPLETED
        if reference:
            self.selcom_reference = reference
        if message:
            self.selcom_message = message
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "selcom_reference", "selcom_message", "paid_at"])

    def __str__(self):
        return f"{self.order_id} ({self.status})"
