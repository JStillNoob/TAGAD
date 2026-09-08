from django.urls import path

from .consumers import EngagementConsumer


websocket_urlpatterns = [
    path('ws/sessions/<int:session_id>/engagement/', EngagementConsumer.as_asgi()),
]
