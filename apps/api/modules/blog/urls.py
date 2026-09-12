from django.urls import path

from modules.blog import views

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("tags/", views.TagListView.as_view(), name="tag-list"),
    path("posts/", views.PostListView.as_view(), name="post-list"),
    path("posts/<slug:slug>/", views.PostDetailView.as_view(), name="post-detail"),
    path("posts/<slug:slug>/view/", views.register_post_view, name="post-view"),
]
