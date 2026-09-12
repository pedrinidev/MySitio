from django.urls import path

from modules.projects import views

urlpatterns = [
    path("technologies/", views.TechnologyListView.as_view(), name="technology-list"),
    path("projects/", views.ProjectListView.as_view(), name="project-list"),
    path("projects/<slug:slug>/", views.ProjectDetailView.as_view(), name="project-detail"),
]
