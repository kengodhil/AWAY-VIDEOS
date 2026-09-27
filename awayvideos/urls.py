from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("catalog.urls")),
]

# Serve media in DEBUG and on simple single-dyno deploys (Render free tier).
# For serious production, put media on S3/Cloudinary instead.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
