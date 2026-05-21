import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # 1. 해당 채팅방 그룹에 유저 입장
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

    async def receive(self, text_data):
        """3. 브라우저에서 실시간으로 톡을 보냈을 때 감지 및 DB 저장"""
        data = json.loads(text_data)
        message_content = data.get('message', '')

        # 비어있는 메시지는 무시
        if not message_content:
            return

        # 현재 로그인한 유저 정보 가져오기 (인증 안 되어 있으면 AnonymousUser)
        user = self.scope['user']
        username = user.username if user.is_authenticated else "Anonymous"

        # [핵심] 비동기 환경에서 안전하게 데이터베이스에 메시지 저장
        if user.is_authenticated:
            await self.save_message(user, message_content)

        # 같은 방에 있는 모든 유저(제공자, 대여자)에게 메시지를 브로드캐스팅(뿌리기)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_content,
                'sender': username
            }
        )

    async def chat_message(self, event):
        # 4. 그룹 메시지를 받아서 실제 브라우저 화면으로 밀어 넣어 주기
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender']
        }))

    # ==========================================
    # DB 백엔드 저장 로직 (비동기 변환)
    # ==========================================
    @database_sync_to_async
    def save_message(self, user, content):
        """동기식 장고 ORM을 비동기 안전하게 감싸서 채팅 메시지를 DB에 저장합니다."""
        try:
            # 현재 룸 ID에 해당하는 ChatRoom 객체를 찾습니다.
            room = ChatRoom.objects.get(pk=self.room_id)

            # ChatMessage 테이블에 대화 내용을 기록합니다.
            return ChatMessage.objects.create(
                room=room,
                sender=user,
                message_type='TALK',  # 사용자가 직접 보낸 톡이므로 일반 대화 타입 지정
                content=content
            )
        except ChatRoom.DoesNotExist:
            # 채팅방이 없을 경우 예외 처리
            pass