# accounts/urls.py
from django.urls import path
from .views import RegisterView, ActivateView, LoginView # LoginView 추가

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('activate/<str:uidb64>/<str:token>/', ActivateView.as_view()),
    path('login/', LoginView.as_view()), # 로그인 경로 추가
]