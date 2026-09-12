from django.urls import path

from modules.games import views

urlpatterns = [
    path("", views.GameListView.as_view(), name="game-list"),
    path("<slug:slug>/questions/", views.QuizQuestionListView.as_view(), name="quiz-questions"),
    path("<slug:slug>/session/", views.start_session, name="game-session"),
    path("<slug:slug>/scores/", views.LeaderboardView.as_view(), name="leaderboard"),
    path("<slug:slug>/scores/submit/", views.submit_score, name="score-submit"),
]
