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
import items.routing  # items 앱 내부에 만들 실시간 노선 라우팅 파일

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 🚨 ProtocolTypeRouter를 통해 요청이 HTTP인지 WebSocket인지 판별하여 분기합니다.
application = ProtocolTypeRouter({
    # 1. 일반적인 웹 페이지 및 REST API 요청 (http:// 또는 https://)
    "http": get_asgi_application(),

    # 2. 실시간 채팅방 연결 요청 (ws:// 또는 wss://)
    "websocket": AuthMiddlewareStack(
        URLRouter(
            items.routing.websocket_urlpatterns
        )
    ),
})