from django.urls import path

from .views import CsrfView, CurrentUserView, LoginView, LogoutView, RegistrationView


urlpatterns = [
    path('csrf/', CsrfView.as_view(), name='csrf'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('register/', RegistrationView.as_view(), name='register'),
]
