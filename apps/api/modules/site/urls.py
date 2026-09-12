from django.urls import path

from modules.site import views

urlpatterns = [
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
