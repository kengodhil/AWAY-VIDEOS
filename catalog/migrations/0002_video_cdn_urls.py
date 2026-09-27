from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="video",
            name="thumbnail_cdn",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="video",
            name="video_cdn",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name="video",
            name="video_file",
            field=models.FileField(blank=True, upload_to="videos/"),
        ),
    ]
