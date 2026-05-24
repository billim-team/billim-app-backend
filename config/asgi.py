"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# 1. 장고 설정 환경 변수를 가장 먼저 선언
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 2. HTTP ASGI 어플리케이션을 먼저 가져와 장고 내부 앱들을 정상 로드(초기화)
django_asgi_app = get_asgi_application()

import items.routing

# ProtocolTypeRouter를 통해 요청이 HTTP인지 WebSocket인지 판별하여 분기
application = ProtocolTypeRouter({
    # 1. 일반적인 웹 페이지 및 REST API 요청 (http:// 또는 https://)
    "http": django_asgi_app,

    # 2. 실시간 채팅방 연결 요청 (ws:// 또는 wss://)
    "websocket": AuthMiddlewareStack(
        URLRouter(
            items.routing.websocket_urlpatterns
        )
    ),
})