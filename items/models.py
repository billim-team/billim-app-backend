from django.db import models
from django.contrib.auth.models import User


# 1 카테고리 테이블
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)

    def __str__(self):
        return self.category_name


# 2 물품 테이블
class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, db_column='owner_id')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='category_id')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price_day = models.IntegerField()

    def __str__(self):
        return self.title


# 3 물품 이미지 테이블
class ItemImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='item_id', related_name='images')

    # 🚨 CharField 대신 ImageField로 변경하여 실제 파일 업로드가 가능하게 만듭니다.
    image = models.ImageField(upload_to='item_images/', blank=True, null=True)
    status_info = models.TextField(blank=True, null=True)  # AI 상태 분석 결과

    def __str__(self):
        return f"Image {self.image_id} for Item {self.item_id}"


class Booking(models.Model):
    """
    3. 대여 예약 테이블
    """
    STATUS_CHOICES = [
        ('PENDING', '예약 대기'),
        ('APPROVED', '승인됨(결제 대기)'),
        ('REJECTED', '거절됨'),
        ('CONFIRMED', '결제 완료(예약 확정)'),
        ('CANCELED', '취소됨'),
    ]

    booking_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='item_id', related_name='bookings')
    renter = models.ForeignKey(User, on_delete=models.CASCADE, db_column='renter_id', related_name='bookings')  # 대여자

    # 캘린더에서 선택할 대여 시작일과 종료일
    start_date = models.DateField()
    end_date = models.DateField()

    # 최종 협의된 가격을 담을 필드 (기본값은 물품의 1일 대여료)
    total_price = models.IntegerField(default=0)

    # 대여 진행 상태
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # 제공자가 거절했을 때 사유를 기록할 필드 (선택 사항)
    reject_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking {self.booking_id} - {self.item.title} ({self.status})"


class ChatRoom(models.Model):
    """
    4. 채팅방 테이블 (물품과 대여자를 기준으로 방이 개설됩니다)
    """
    room_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='item_id')
    renter = models.ForeignKey(User, on_delete=models.CASCADE, db_column='renter_id', related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ChatRoom {self.room_id} for Item {self.item_id}"


class ChatMessage(models.Model):
    """
    5. 채팅 메시지 테이블
    """
    MESSAGE_TYPES = [
        ('TALK', '일반 대화'),
        ('SYSTEM', '시스템 자동 메시지'),
        ('PAY_FORM', '결제 요청 폼'),
    ]

    message_id = models.AutoField(primary_key=True)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, db_column='room_id', related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, db_column='sender_id')  # 발신자

    # 메시지 타입 (일반 채팅인지, 시스템 메시지인지, 결제 폼인지 구분)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='TALK')

    # 메시지 내용 (자동 메시지 텍스트나 결제 폼 관련 데이터를 담음)
    content = models.TextField()

    # 이 메시지가 특정 예약 요청과 관련이 있다면 연동 (선택)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, blank=True, null=True, db_column='booking_id')

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.message_type}] {self.sender.username}: {self.content[:20]}"