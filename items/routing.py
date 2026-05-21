from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # ws://127.0.0.1:8000/ws/chat/방번호/ 형태로 프론트와 소켓 연결을 맺습니다.
    re_path(r'ws/chat/(?P<room_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]