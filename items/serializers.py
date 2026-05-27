from rest_framework import serializers
from .models import Item, Category, ItemFile, Rental, ChatRoom, ChatMessage  # ⭐️ ItemImage -> ItemFile, Booking -> Rental 변경


# 1. 카테고리 시리얼라이저
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


# 2. 물품 이미지/파일 시리얼라이저
class ItemFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemFile
        fields = ['file_id', 'file_url', 'status_info']  # 정의서 칼럼명 반영


# 3. 물품 상세 정보 시리얼라이저
class ItemSerializer(serializers.ModelSerializer):
    owner_username = serializers.ReadOnlyField(source='owner.username')
    category_name = serializers.ReadOnlyField(source='category.category_name')
    files = ItemFileSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = [
            'item_id', 'owner', 'owner_username', 'category', 'category_name',
            'title', 'description', 'price_day', 'status', 'files', 'created_at', 'updated_at'
        ]


# 4. 대여 예약 생성 시리얼라이저 (views.py의 통일성을 위해 클래스 이름은 유지하되 내부 모델을 바꿉니다)
class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rental
        fields = ['item', 'start_date', 'end_date']


# 5. 제공자 수락/거절 액션 시리얼라이저
class BookingActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['APPROVE', 'REJECT'])
    reject_reason = serializers.CharField(required=False, allow_blank=True)


# 6. 순수 채팅 메시지 시리얼라이저
class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source='sender.username')

    class Meta:
        model = ChatMessage
        fields = ['message_id', 'room', 'sender', 'sender_username', 'message_type', 'content', 'rental', 'timestamp']  # booking -> rental


# 7. 채팅방 목록/상세 시리얼라이저
class ChatRoomSerializer(serializers.ModelSerializer):
    item_title = serializers.ReadOnlyField(source='item.title')
    renter_username = serializers.ReadOnlyField(source='renter.username')

    class Meta:
        model = ChatRoom
        fields = ['room_id', 'item', 'item_title', 'renter', 'renter_username', 'created_at']