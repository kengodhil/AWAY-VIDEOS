from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Video",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                (
                    "watch_price",
                    models.PositiveIntegerField(
                        default=2000, help_text="Price to watch full video (TZS)"
                    ),
                ),
                (
                    "download_price",
                    models.PositiveIntegerField(
                        default=1000, help_text="Price to download video (TZS)"
                    ),
                ),
                ("thumbnail", models.ImageField(blank=True, upload_to="thumbnails/")),
                ("video_file", models.FileField(upload_to="videos/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(db_index=True, max_length=64)),
                (
                    "purpose",
                    models.CharField(
                        choices=[("WATCH", "Watch"), ("DOWNLOAD", "Download")],
                        max_length=16,
                    ),
                ),
                ("order_id", models.CharField(max_length=64, unique=True)),
                ("phone", models.CharField(max_length=20)),
                ("amount", models.PositiveIntegerField()),
                ("currency", models.CharField(default="TZS", max_length=8)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                            ("CANCELLED", "Cancelled"),
                            ("EXPIRED", "Expired"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("snippe_reference", models.CharField(blank=True, max_length=128)),
                ("snippe_message", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                (
                    "video",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="catalog.video",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(
                fields=["session_key", "video", "purpose", "status"],
                name="catalog_pay_session_idx",
            ),
        ),
    ]
