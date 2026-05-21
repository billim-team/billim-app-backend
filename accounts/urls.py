# accounts/urls.py
from django.urls import path
from .views import logout_view
from .views import RegisterView, ActivateView, LoginView, MySettingsView

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('activate/<str:uidb64>/<str:token>/', ActivateView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', logout_view, name='logout'),
    path('my-settings/', MySettingsView.as_view(), name='my-settings'),
]