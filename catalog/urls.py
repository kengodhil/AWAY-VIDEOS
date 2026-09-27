from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("videos/", views.video_list, name="video_list"),
    path("videos/<int:pk>/", views.video_detail, name="video_detail"),
    path("videos/<int:pk>/pay/", views.pay_video, name="pay_video"),
    path("videos/<int:pk>/watch/", views.watch_video, name="watch_video"),
    path("payments/<str:order_id>/", views.payment_status, name="payment_status"),
    path("payments/<str:order_id>/status/", views.payment_status_json, name="payment_status_json"),
    path("payments/<str:order_id>/demo-complete/", views.mock_complete_payment, name="mock_complete_payment"),
    path("webhooks/selcom/", views.selcom_webhook, name="selcom_webhook"),
    path("studio/", views.studio, name="studio"),
    path("studio/videos/new/", views.add_video, name="add_video"),
    path("studio/videos/<int:pk>/delete/", views.delete_video, name="delete_video"),
    path("studio/users/<int:pk>/delete/", views.delete_user, name="delete_user"),
]
