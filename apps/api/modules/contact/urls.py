from django.urls import path

from modules.contact import views

urlpatterns = [
    path("", views.create_contact_message, name="contact-create"),
]
