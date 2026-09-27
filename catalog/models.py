from django.conf import settings
from django.db import models
from django.utils import timezone


def _video_storage():
    if getattr(settings, "USE_CLOUDINARY", False):
        from cloudinary_storage.storage import VideoMediaCloudinaryStorage

        return VideoMediaCloudinaryStorage()
    return None


def _image_storage():
    if getattr(settings, "USE_CLOUDINARY", False):
        from cloudinary_storage.storage import MediaCloudinaryStorage

        return MediaCloudinaryStorage()
    return None


class Video(models.Model):
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    watch_price = models.PositiveIntegerField(
        default=2000,
        help_text="Price to watch full video (TZS)",
    )
    download_price = models.PositiveIntegerField(
        default=1000,
        help_text="Price to download video (TZS)",
    )
    thumbnail = models.ImageField(
        upload_to="thumbnails/",
        blank=True,
        storage=_image_storage,
    )
    video_file = models.FileField(
        upload_to="videos/",
        storage=_video_storage,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def has_playable_file(self) -> bool:
        return bool(self.video_file and self.video_file.name)


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    class Purpose(models.TextChoices):
        WATCH = "WATCH", "Watch"
        DOWNLOAD = "DOWNLOAD", "Download"

    session_key = models.CharField(max_length=64, db_index=True)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="payments")
    purpose = models.CharField(max_length=16, choices=Purpose.choices)
    order_id = models.CharField(max_length=64, unique=True)
    phone = models.CharField(max_length=20)
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=8, default="TZS")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    snippe_reference = models.CharField(max_length=128, blank=True)
    snippe_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session_key", "video", "purpose", "status"]),
        ]

    def mark_completed(self, reference="", message=""):
        self.status = self.Status.COMPLETED
        if reference:
            self.snippe_reference = reference
        if message:
            self.snippe_message = message
        self.paid_at = timezone.now()
        self.save(
            update_fields=["status", "snippe_reference", "snippe_message", "paid_at"]
        )

    def __str__(self):
        return f"{self.order_id} {self.purpose} ({self.status})"
