from rest_framework import serializers
from .models import Item, Category, ItemImage, Booking, ChatRoom, ChatMessage


# ==========================================
# 1. 인증 및 카테고리 시리얼라이저
# ==========================================
class LoginSerializer(serializers.Serializer):
    """로그인 처리용 시리얼라이저"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class CategorySerializer(serializers.ModelSerializer):
    """카테고리 정보 조회용 시리얼라이저"""
    class Meta:
        model = Category
        fields = ['category_id', 'category_name']


# ==========================================
# 2. 물품(Item) 및 이미지(Image) 시리얼라이저
# ==========================================
class ItemImageSerializer(serializers.ModelSerializer):
    """물품에 속한 다중 이미지 서빙용 시리얼라이저"""
    class Meta:
        model = ItemImage
        fields = ['image_id', 'image', 'status_info']


class ItemSerializer(serializers.ModelSerializer):
    """물품 상세 정보 및 리스트 조회용 시리얼라이저"""
    owner_name = serializers.ReadOnlyField(source='owner.username')
    images = ItemImageSerializer(many=True, read_only=True)
    category_name = serializers.ReadOnlyField(source='category.category_name')

    class Meta:
        model = Item
        fields = [
            'item_id',
            'owner_name',
            'category',
            'category_name',
            'title',
            'description',
            'price_day',
            'images'
        ]


# ==========================================
# 3. 대여 예약(Booking) 시리얼라이저
# ==========================================
class BookingCreateSerializer(serializers.ModelSerializer):
    """대여자가 예약을 신청할 때 날짜만 검증하는 시리얼라이저"""

    class Meta:
        model = Booking
        # 🚨 renter_note를 빼고 딱 필요한 필드만 남겼습니다.
        fields = ['booking_id', 'item', 'start_date', 'end_date', 'total_price', 'status']
        read_only_fields = ['total_price', 'status']

    def validate(self, attrs):
        # [유효성 검사] 대여 시작일과 종료일 역전 방지
        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError("대여 시작일은 종료일보다 빨라야 합니다.")
        return attrs

class ChatMessageSerializer(serializers.ModelSerializer):
    """채팅 메시지 조회 및 전송용 시리얼라이저"""
    sender_name = serializers.ReadOnlyField(source='sender.username')

    class Meta:
        model = ChatMessage
        fields = ['message_id', 'room', 'sender', 'sender_name', 'message_type', 'content', 'timestamp', 'booking']
        read_only_fields = ['sender']


class BookingActionSerializer(serializers.Serializer):
    """제공자가 예약을 승인하거나 거절할 때 사용하는 액션 시리얼라이저"""
    # 'APPROVE' 또는 'REJECT' 값을 받습니다.
    action = serializers.ChoiceField(choices=['APPROVE', 'REJECT'])
    # 거절 시에만 사유를 받도록 처리 (선택 사항)
    reject_reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs['action'] == 'REJECT' and not attrs.get('reject_reason'):
            # 기획에 따라 거절 사유를 필수 항목으로 만들고 싶다면 여기서 에러를 발생시킬 수 있습니다.
            pass
        return attrs