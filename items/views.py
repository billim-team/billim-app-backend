from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import ChatMessage, ChatRoom, Item, Rental, ItemFile, Review, Category
from .serializers import (
    BookingCreateSerializer, ItemSerializer, ChatMessageSerializer,
    BookingActionSerializer, ReviewSerializer, CategorySerializer  # CategorySerializer 추가
)

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


# 카테고리 관련 View
class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


# 1. 물품 관련 View
class ItemListCreateView(generics.ListCreateAPIView):
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

        rental = serializer.save(renter=self.request.user, total_price=total_price, status='WAITING')

        chat_room, _ = ChatRoom.objects.get_or_create(
            item=item,
            renter=self.request.user
        )

        user_name = str(self.request.user)
        popup_content = (
            f"📢 '{user_name}'님이 예약을 요청했습니다.\n"
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

        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat_room.room_id}',
                {
                    'type': 'popup_message',
                    'message_type': 'SYSTEM',
                    'message': popup_content,
                    'sender': user_name
                }
            )


class RentalActionView(generics.GenericAPIView):
    """[단계 2] 제공자의 예약 수락(PAY_FORM 팝업) 또는 거절(SYSTEM 사유 메시지) 처리"""
    serializer_class = BookingActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, rental_id):
        try:
            rental = Rental.objects.get(pk=rental_id)
        except Rental.DoesNotExist:
            return Response({"error": "존재하지 않는 예약 요청입니다."}, status=status.HTTP_404_NOT_FOUND)

        if rental.item.owner != request.user:
            return Response({"error": "이 예약 요청을 처리할 권한이 없습니다 (물품 제공자 전용)."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']
        reject_reason = serializer.validated_data.get('reject_reason', '')

        chat_room, _ = ChatRoom.objects.get_or_create(item=rental.item, renter=rental.renter)
        channel_layer = get_channel_layer()
        user_name = str(request.user)

        if action == 'APPROVE':
            rental.status = 'APPROVED'
            rental.save()

            pay_content = f"💳 제공자가 대여 요청을 승인했습니다! 아래 결제하기 버튼을 눌러 결제를 진행해 주세요.\n결제 금액: {rental.total_price}원"
            ChatMessage.objects.create(
                room=chat_room,
                sender=request.user,
                message_type='PAY_FORM',
                content=pay_content,
                rental=rental
            )

            if channel_layer is not None:
                async_to_sync(channel_layer.group_send)(
                    f'chat_{chat_room.room_id}',
                    {
                        'type': 'popup_message',
                        'message_type': 'PAY_FORM',
                        'message': pay_content,
                        'sender': user_name
                    }
                )
            return Response({"message": "예약을 승인하였고 결제 폼 팝업을 전송했습니다.", "status": rental.status})

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
                rental=rental
            )

            if channel_layer is not None:
                async_to_sync(channel_layer.group_send)(
                    f'chat_{chat_room.room_id}',
                    {
                        'type': 'popup_message',
                        'message_type': 'SYSTEM',
                        'message': reject_msg,
                        'sender': user_name
                    }
                )
            return Response({"message": "예약을 거절하였고 안내 메시지를 전송했습니다.", "status": rental.status})


class PaymentCompleteView(generics.GenericAPIView):
    """[단계 3] 대여자가 결제를 마쳤을 때 제공자를 향해 결제 완료 팝업(PAY_COMPLETE)을 전송하는 API"""
    serializer_class = BookingActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, rental_id):
        try:
            rental = Rental.objects.get(pk=rental_id)
        except Rental.DoesNotExist:
            return Response({"error": "존재하지 않는 예약 내역입니다."}, status=status.HTTP_404_NOT_FOUND)

        if rental.renter != request.user:
            return Response({"error": "이 결제를 완료 처리할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        rental.status = 'PAID'
        rental.save()

        chat_room = ChatRoom.objects.get(item=rental.item, renter=rental.renter)
        user_name = str(request.user)

        complete_content = f"🎉 대여자 '{user_name}'님이 결제를 완료했습니다!\n물품을 안전하게 전달할 준비를 해주세요."
        ChatMessage.objects.create(
            room=chat_room,
            sender=request.user,
            message_type='PAY_COMPLETE',
            content=complete_content,
            rental=rental
        )

        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat_room.room_id}',
                {
                    'type': 'popup_message',
                    'message_type': 'PAY_COMPLETE',
                    'message': complete_content,
                    'sender': user_name
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


# 4. 대여자의 반납 요청 및 가이드 기반 사진 업로드 View
class RentalReturnView(generics.GenericAPIView):
    """[단계 4] 대여자가 가이드에 맞춰 반납 사진 4장을 제출하는 API"""
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, rental_id):
        try:
            rental = Rental.objects.get(pk=rental_id)
        except Rental.DoesNotExist:
            return Response({"error": "존재하지 않는 대여 내역입니다."}, status=status.HTTP_404_NOT_FOUND)

        if rental.renter != request.user:
            return Response({"error": "반납을 신청할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        if rental.status != 'PAID':
            return Response({"error": "현재 반납 가능한 대여 상태가 아닙니다."}, status=status.HTTP_400_BAD_REQUEST)

        directions = {
            'img_front': 'RENTER_FRONT',
            'img_back': 'RENTER_BACK',
            'img_left': 'RENTER_LEFT',
            'img_right': 'RENTER_RIGHT'
        }

        has_file = False
        for key, file_type in directions.items():
            file_obj = request.FILES.get(key)
            if file_obj:
                ItemFile.objects.create(
                    item=rental.item,
                    file_url=file_obj,
                    file_type=file_type
                )
                has_file = True

        if not has_file:
            return Response({"error": "반납 검증을 위한 사진이 최소 1장 이상 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        rental.status = 'APPROVED'
        rental.save()

        chat_room = ChatRoom.objects.get(item=rental.item, renter=rental.renter)
        user_name = str(request.user)
        return_content = f"📦 대여자 '{user_name}'님이 반납 사진 등록을 마쳤습니다!\n제공자님은 사진을 확인하고 보증금 정산을 진행해 주세요."

        ChatMessage.objects.create(
            room=chat_room,
            sender=request.user,
            message_type='SYSTEM',
            content=return_content,
            rental=rental
        )

        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat_room.room_id}',
                {
                    'type': 'popup_message',
                    'message_type': 'SYSTEM',
                    'message': return_content,
                    'sender': user_name
                }
            )

        return Response({"message": "반납 사진 등록이 완료되었으며, 제공자 승인 요청 알림을 보냈습니다.", "status": rental.status})


# 5. 제공자의 보증금 정산 및 거래 최종 완료 View
class RentalCompleteView(generics.GenericAPIView):
    """[단계 5] 제공자가 대여자의 반납 사진 확인 후 보증금 차감액을 확정하고 거래를 최종 종료하는 API"""
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, rental_id):
        try:
            rental = Rental.objects.get(pk=rental_id)
        except Rental.DoesNotExist:
            return Response({"error": "존재하지 않는 대여 내역입니다."}, status=status.HTTP_404_NOT_FOUND)

        if rental.item.owner != request.user:
            return Response({"error": "정산 권한이 없습니다 (물품 제공자 전용)."}, status=status.HTTP_403_FORBIDDEN)

        final_deposit = request.data.get('deposit', None)
        if final_deposit is None:
            return Response({"error": "최종 반환할 보증금 금액(deposit)을 입력해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rental.deposit = int(final_deposit)
        except ValueError:
            return Response({"error": "보증금은 올바른 숫자 형식이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        rental.save()

        chat_room = ChatRoom.objects.get(item=rental.item, renter=rental.renter)
        user_name = str(request.user)
        complete_msg = f"🏁 정산 및 대여 거래가 최종 종료되었습니다.\n💰 최종 보증금 환불액: {rental.deposit}원\n✍️ 이제 상대방에 대한 리뷰를 작성하실 수 있습니다."

        ChatMessage.objects.create(
            room=chat_room,
            sender=request.user,
            message_type='SYSTEM',
            content=complete_msg,
            rental=rental
        )

        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat_room.room_id}',
                {
                    'type': 'popup_message',
                    'message_type': 'SYSTEM',
                    'message': complete_msg,
                    'sender': user_name
                }
            )

        return Response({"message": "정산 처리가 마감되었으며 거래를 최종 종료했습니다.", "deposit_refund": rental.deposit})


# 6. 대여 거래가 종료된 후 리뷰 작성 View
class ReviewCreateView(generics.CreateAPIView):
    """[단계 6] 정산까지 완전히 마감된 대여 예약 건에 한해 대여자가 리뷰를 등록하는 API"""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        rental_id = request.data.get('rental')
        try:
            rental = Rental.objects.get(pk=rental_id)
        except Rental.DoesNotExist:
            return Response({"error": "존재하지 않는 대여 예약 내역입니다."}, status=status.HTTP_404_NOT_FOUND)

        if rental.renter != request.user:
            return Response({"error": "리뷰는 물품을 빌린 대여자 본인만 작성할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)

        if hasattr(rental, 'review'):
            return Response({"error": "이미 이 대여 건에 대한 리뷰를 등록하셨습니다."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(rental=rental, writer=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)