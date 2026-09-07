from django.urls import path

from .views import (
    CameraDetailView,
    CameraListCreateView,
    ClassManagementOptionsView,
    ClassroomDetailView,
    ClassroomListCreateView,
    CsrfView,
    CurrentUserView,
    LoginView,
    LogoutView,
    RegistrationView,
    SubjectDetailView,
    SubjectListCreateView,
    UserDetailView,
    UserListCreateView,
    UserOptionsView,
)


urlpatterns = [
    path('csrf/', CsrfView.as_view(), name='csrf'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('register/', RegistrationView.as_view(), name='register'),
    path('users/', UserListCreateView.as_view(), name='user-list'),
    path('users/options/', UserOptionsView.as_view(), name='user-options'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('classrooms/', ClassroomListCreateView.as_view(), name='classroom-list'),
    path('classrooms/<int:pk>/', ClassroomDetailView.as_view(), name='classroom-detail'),
    path('subjects/', SubjectListCreateView.as_view(), name='subject-list'),
    path('subjects/<int:pk>/', SubjectDetailView.as_view(), name='subject-detail'),
    path('class-management/options/', ClassManagementOptionsView.as_view(), name='class-management-options'),
    path('cameras/', CameraListCreateView.as_view(), name='camera-list'),
    path('cameras/<int:pk>/', CameraDetailView.as_view(), name='camera-detail'),
]
