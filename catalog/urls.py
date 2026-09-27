from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("videos/<int:pk>/pay/<str:purpose>/", views.pay_video, name="pay_video"),
    path("videos/<int:pk>/watch/", views.watch_video, name="watch_video"),
    path("videos/<int:pk>/download/", views.download_video, name="download_video"),
    path("payments/<str:order_id>/", views.payment_status, name="payment_status"),
    path("payments/<str:order_id>/status/", views.payment_status_json, name="payment_status_json"),
    path("payments/<str:order_id>/demo-complete/", views.mock_complete_payment, name="mock_complete_payment"),
    path("webhooks/snippe/", views.snippe_webhook, name="snippe_webhook"),
    # Custom studio (branded admin UI)
    path("studio/login/", views.studio_login, name="studio_login"),
    path("studio/logout/", views.studio_logout, name="studio_logout"),
    path("studio/", views.studio_dashboard, name="studio_dashboard"),
    path("studio/videos/new/", views.studio_add_video, name="studio_add_video"),
    path("studio/videos/<int:pk>/delete/", views.studio_delete_video, name="studio_delete_video"),
    path("studio/admins/new/", views.studio_add_admin, name="studio_add_admin"),
]
