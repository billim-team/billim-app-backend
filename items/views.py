from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import ChatMessage, ChatRoom, Item, Booking
from .serializers import BookingCreateSerializer, ItemSerializer, ChatMessageSerializer, BookingActionSerializer


# ==========================================
# 1. 물품(Item) 관련 View
# ==========================================
class ItemListCreateView(generics.ListCreateAPIView):
    """물품 목록 조회 및 생성"""
    serializer_class = ItemSerializer

    def get_permissions(self):
        # [POST] 물품 등록은 로그인 필수, [GET] 목록 조희는 누구나 가능
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        # 카테고리 쿼리 파라미터(?category=ID) 필터링 처리
        queryset = Item.objects.all()
        category_id = self.request.query_params.get('category', None)

        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)

        return queryset

    def perform_create(self, serializer):
        # 글 작성자를 현재 로그인한 유저(owner)로 저장
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
        # 본인이 등록한 물품만 조회/수정/삭제 가능하도록 제한
        return Item.objects.filter(owner=self.request.user)


# ==========================================
# 2. 대여 예약(Booking) 관련 View
# ==========================================
class BookingCreateView(generics.CreateAPIView):
    """대여 예약 요청 생성 및 채팅방 자동 연동"""
    serializer_class = BookingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def perform_create(self, serializer):
        # 1. 예약 입력 데이터 가공 및 총 대여 금액 산정
        item = serializer.validated_data['item']
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']

        days = (end_date - start_date).days + 1
        total_price = item.price_day * days

        # 2. 예약 데이터 최종 저장
        booking = serializer.save(renter=self.request.user, total_price=total_price)

        # 3. 제공자와 대여자 사이의 채팅방 조회 혹은 신규 개설
        chat_room, created = ChatRoom.objects.get_or_create(
            item=item,
            renter=self.request.user
        )

        # 4. 채팅방 내 시스템 자동 메시지 생성 및 발송
        system_content = (
            f"📢 '{self.request.user.username}'님이 예약을 요청했습니다.\n"
            f"🗓️ 기간: {start_date} ~ {end_date}\n"
            f"💰 예상 금액: {total_price}원"
        )
        ChatMessage.objects.create(
            room=chat_room,
            sender=self.request.user,
            message_type='SYSTEM',
            content=system_content,
            booking=booking
        )


class ChatMessageListCreateView(generics.ListCreateAPIView):
    """특정 채팅방(room_id)의 메시지 목록 조회 및 메시지 전송"""
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # URL 주소에서 room_id를 추출하여 해당 방의 메시지만 시간순으로 정렬
        return ChatMessage.objects.filter(room_id=self.kwargs['room_id']).order_by('timestamp')

    def perform_create(self, serializer):
        # 메시지 발신자를 현재 로그인한 유저로 지정
        serializer.save(sender=self.request.user)


class BookingActionView(generics.GenericAPIView):
    """제공자가 예약을 승인(APPROVE)하거나 거절(REJECT)하는 액션 API"""
    serializer_class = BookingActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, booking_id, *args, **kwargs):
        # 1. 예약 객체 가져오기
        try:
            booking = Booking.objects.get(pk=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "존재하지 않는 예약 요청입니다."}, status=status.HTTP_404_NOT_FOUND)

        # 2. 권한 검증: 이 물품의 제공자(owner)만 승인/거절을 할 수 있어야 합니다.
        if booking.item.owner != request.user:
            return Response({"error": "이 예약 요청을 처리할 권한이 없습니다 (물품 제공자 전용)."}, status=status.HTTP_403_FORBIDDEN)

        # 3. 데이터 검증 (APPROVE 인지 REJECT 인지 구분)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']
        reject_reason = serializer.validated_data.get('reject_reason', '')

        # 4. 연동된 채팅방 찾아오기 (없으면 새로 개설)
        chat_room, _ = ChatRoom.objects.get_or_create(item=booking.item, renter=booking.renter)

        # 5. 액션별 분기 처리
        if action == 'APPROVE':
            booking.status = 'APPROVED'
            booking.save()

            # 채팅방에 결제를 요구하는 폼과 자동 메시지 전송 기획 구현
            ChatMessage.objects.create(
                room=chat_room,
                sender=request.user,
                message_type='PAY_FORM',  # 결제 폼 타입으로 지정하여 프론트가 버튼을 띄우게 함
                content=f"💳 제공자가 대여 요청을 승인했습니다! 아래 결제하기 버튼을 눌러 결제를 진행해 주세요.\n결제 금액: {booking.total_price}원",
                booking=booking
            )
            return Response({"message": "예약을 승인하였고 결제 폼을 전송했습니다.", "status": booking.status})

        elif action == 'REJECT':
            booking.status = 'REJECTED'
            booking.reject_reason = reject_reason
            booking.save()

            # 채팅방에 거절 자동 메시지 전송
            reject_msg = "❌ 제공자의 개인 사정으로 인해 대여 요청이 거절되었습니다."
            if reject_reason:
                reject_msg += f"\n💬 거절 사유: {reject_reason}"

            ChatMessage.objects.create(
                room=chat_room,
                sender=request.user,
                message_type='SYSTEM',
                content=reject_msg,
                booking=booking
            )
            return Response({"message": "예약을 거절하였고 안내 메시지를 전송했습니다.", "status": booking.status})