from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import ChatMessage, ChatRoom, Item, Rental
from .serializers import BookingCreateSerializer, ItemSerializer, ChatMessageSerializer, BookingActionSerializer

# 실시간 웹소켓 팝업 연동을 위한 패키지 임포트
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


# 1. 물품(Item) 관련 View
class ItemListCreateView(generics.ListCreateAPIView):
    """물품 목록 조회 및 생성"""
    serializer_class = ItemSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = Item.objects.all()
        category_id = self.request.query_params.get('category', None)
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ItemDetailView(generics.RetrieveAPIView):
    """물품 상세 조회"""
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_classes = [permissions.AllowAny]


class ItemUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """물품 수정 및 삭제 (작성자 본인만 가능)"""
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Item.objects.filter(owner=self.request.user)


# 2. 대여 예약(Rental) 및 채팅방 팝업 흐름 View
class RentalCreateView(generics.CreateAPIView):
    """[단계 1] 대여 예약 요청 생성 및 예약 정보 팝업 전송"""
    serializer_class = BookingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def perform_create(self, serializer):
        item = serializer.validated_data['item']
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']

        days = (end_date - start_date).days + 1
        total_price = item.price_day * days

        # 1. 예약 데이터 대기 상태로 저장 (Rental 모델로 저장)
        rental = serializer.save(renter=self.request.user, total_price=total_price, status='WAITING')

        # 2. 제공자와 대여자 사이의 채팅방 조회 혹은 신규 개설
        chat_room, created = ChatRoom.objects.get_or_create(
            item=item,
            renter=self.request.user
        )

        # 3. 대여자가 설정한 예약 정보를 담은 팝업(SYSTEM) 생성
        popup_content = (
            f"📢 '{self.request.user.username}'님이 예약을 요청했습니다.\n"
            f"🗓️ 기간: {start_date} ~ {end_date}\n"
            f"💰 예상 금액: {total_price}원"
        )
        ChatMessage.objects.create(
            room=chat_room,
            sender=self.request.user,
            message_type='SYSTEM',
            content=popup_content,
            rental=rental
        )

        # [실시간 알림] 웹소켓 채널로 예약 요청 팝업 브로드캐스팅
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{chat_room.room_id}',  # consumers.py와 매핑되는 방 그룹 이름
            {
                'type': 'popup_message',  # consumers.py에 작성해둔 popup_message 함수 호출
                'message_type': 'SYSTEM',
                'message': popup_content,
                'sender': self.request.user.username
            }
        )


class RentalActionView(generics.GenericAPIView):
    """[단계 2] 제공자의 예약 수락(PAY_FORM 팝업) 또는 거절(SYSTEM 사유 메시지) 처리"""
    serializer_class = BookingActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, rental_id, *args, **kwargs):
        try:
            rental = Rental.objects.get(pk=rental_id)  #Rental 조회로 변경
        except Rental.DoesNotExist:
            return Response({"error": "존재하지 않는 예약 요청입니다."}, status=status.HTTP_404_NOT_FOUND)

        if rental.item.owner != request.user:
            return Response({"error": "이 예약 요청을 처리할 권한이 없습니다 (물품 제공자 전용)."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']
        reject_reason = serializer.validated_data.get('reject_reason', '')

        chat_room, _ = ChatRoom.objects.get_or_create(item=rental.item, renter=rental.renter)

        # 실시간 선로 라이브 연결
        channel_layer = get_channel_layer()

        # Case A: 제공자가 예약을 수락했을 경우
        if action == 'APPROVE':
            rental.status = 'APPROVED'
            rental.save()

            pay_content = f"💳 제공자가 대여 요청을 승인했습니다! 아래 결제하기 버튼을 눌러 결제를 진행해 주세요.\n결제 금액: {rental.total_price}원"
            ChatMessage.objects.create(
                room=chat_room,
                sender=request.user,
                message_type='PAY_FORM',
                content=pay_content,
                rental=rental  #rental 매핑
            )

            # [실시간 알림] 웹소켓 채널로 결제 폼 팝업 브로드캐스팅
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat_room.room_id}',
                {
                    'type': 'popup_message',
                    'message_type': 'PAY_FORM',
                    'message': pay_content,
                    'sender': request.user.username
                }
            )
            return Response({"message": "예약을 승인하였고 결제 폼 팝업을 전송했습니다.", "status": rental.status})

        # Case B: 제공자가 예약을 거절했을 경우
        elif action == 'REJECT':
            rental.status = 'REJECTED'
            rental.reject_reason = reject_reason
            rental.save()

            reject_msg = "❌ 제공자의 개인 사정으로 인해 대여 요청이 거절되었습니다."
            if reject_reason:
                reject_msg += f"\n💬 거절 사유: {reject_reason}"

            ChatMessage.objects.create(
                room=chat_room,
                sender=request.user,
                message_type='SYSTEM',
                content=reject_msg,
                rental=rental  #rental 매핑
            )

            # [실시간 알림] 웹소켓 채널로 거절 안내 사유 팝업 브로드캐스팅
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat_room.room_id}',
                {
                    'type': 'popup_message',
                    'message_type': 'SYSTEM',
                    'message': reject_msg,
                    'sender': request.user.username
                }
            )
            return Response({"message": "예약을 거절하였고 안내 메시지를 전송했습니다.", "status": rental.status})


class PaymentCompleteView(generics.GenericAPIView):
    """[단계 3] 대여자가 결제를 마쳤을 때 제공자를 향해 결제 완료 팝업(PAY_COMPLETE)을 전송하는 API"""
    serializer_class = BookingActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, rental_id, *args, **kwargs):
        try:
            rental = Rental.objects.get(pk=rental_id)  # Rental 조회로 변경
        except Rental.DoesNotExist:
            return Response({"error": "존재하지 않는 예약 내역입니다."}, status=status.HTTP_404_NOT_FOUND)

        if rental.renter != request.user:
            return Response({"error": "이 결제를 완료 처리할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        rental.status = 'PAID'
        rental.save()

        chat_room = ChatRoom.objects.get(item=rental.item, renter=rental.renter)

        complete_content = f"🎉 대여자 '{request.user.username}'님이 결제를 완료했습니다!\n물품을 안전하게 전달할 준비를 해주세요."
        ChatMessage.objects.create(
            room=chat_room,
            sender=request.user,
            message_type='PAY_COMPLETE',
            content=complete_content,
            rental=rental  # rental 매핑
        )

        # [실시간 알림] 웹소켓 채널로 최종 결제 완료 안내 팝업 브로드캐스팅
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{chat_room.room_id}',
            {
                'type': 'popup_message',
                'message_type': 'PAY_COMPLETE',
                'message': complete_content,
                'sender': request.user.username
            }
        )

        return Response({"message": "결제 처리가 완료되었으며, 제공자용 알림 팝업을 전송했습니다.", "status": rental.status})


# 3. 순수 대화(Chat) 관련 View
class ChatMessageListCreateView(generics.ListCreateAPIView):
    """특정 채팅방(room_id)의 메시지 목록 조회 및 '사용자가 직접 보낸 것만' 전송"""
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatMessage.objects.filter(room_id=self.kwargs['room_id']).order_by('timestamp')

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user, message_type='TALK')