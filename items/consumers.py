import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.room_group_name = None

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # 1. 해당 채팅방 유저 입장
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # 2. 방을 나갈 때 그룹에서 제거
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        data = json.loads(text_data)
        message_content = data.get('message', '')

        # 비어있는 메시지는 무시
        if not message_content:
            return

        # 현재 로그인한 유저 정보 가져오기
        user = self.scope['user']
        username = user.username if user.is_authenticated else "Anonymous"

        # 데이터베이스에 메시지 저장
        if user.is_authenticated:
            await self.save_message(user, message_content)

        # 같은 방에 있는 모든 유저에게 메시지 브로드캐스팅
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_type': 'TALK',
                'message': message_content,
                'sender': username
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message_type': event['message_type'],  # TALK
            'message': event['message'],
            'sender': event['sender']
        }))

    # 시스템 및 결제 관련 팝업 메시지 수신 핸들러
    async def popup_message(self, event):
        await self.send(text_data=json.dumps({
            'message_type': event['message_type'],  # SYSTEM / PAY_FORM / PAY_COMPLETE
            'message': event['message'],
            'sender': event['sender']
        }))

    # DB 백엔드 저장 로직
    @database_sync_to_async
    def save_message(self, user, content):
        try:
            room = ChatRoom.objects.get(pk=self.room_id)

            return ChatMessage.objects.create(
                room=room,
                sender=user,
                message_type='TALK',
                content=content
            )
        except ChatRoom.DoesNotExist:
            return None