from django.db import models
from django.conf import settings


# 1. 카테고리 테이블 (정의서 명칭: category)
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'category'  # MySQL 테이블 이름을 정의서와 강제로 일치시킵니다.

    def __str__(self):
        return self.category_name


# 2. 물품 테이블 (정의서 명칭: item)
class Item(models.Model):
    # 프로젝트 중 추가되거나 수정한 상태 로직을 유지하기 위한 예시입니다.
    ITEM_STATUS_CHOICES = [
        ('AVAILABLE', '대여 가능'),
        ('RENTED', '대여 중'),
        ('DISABLED', '비활성화'),
    ]

    item_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='owner_id',
        related_name='items'
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='category_id')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price_day = models.IntegerField()
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='AVAILABLE')  # 정의서 항목 반영
    created_at = models.DateTimeField(auto_now_add=True)  # 정의서 항목 반영
    updated_at = models.DateTimeField(auto_now=True)      # 정의서 항목 반영

    class Meta:
        db_table = 'item'

    def __str__(self):
        return self.title


# 3. 물품 이미지/파일 테이블 (정의서 명칭: item_file)
class ItemFile(models.Model):
    file_id = models.AutoField(primary_key=True)  # 정의서 기준 기본키
    item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='item_id', related_name='files')
    file_url = models.ImageField(upload_to='item_images/', blank=True, null=True)  # 정의서 칼럼명 일치 (image -> file_url)
    status_info = models.TextField(blank=True, null=True)  # 작업 중 추가된 AI 상태 분석 결과 유지

    class Meta:
        db_table = 'item_file'

    def __str__(self):
        return f"File {self.file_id} for Item {self.item.item_id}"


# 4. 대여 예약 테이블 (정의서 명칭: rental)
class Rental(models.Model):
    """
    대여 예약 테이블 (클래스명을 Booking에서 정의서 표준인 Rental로 변경하고 실시간 상태 로직을 병합했습니다)
    """
    STATUS_CHOICES = [
        ('WAITING', '예약 대기'),
        ('APPROVED', '승인됨(결제 대기)'),
        ('REJECTED', '거절됨'),
        ('PAID', '결제 완료(예약 확정)'),
        ('CANCELED', '취소됨'),
    ]

    rental_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='item_id', related_name='rentals')
    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='renter_id',
        related_name='rentals'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    deposit = models.IntegerField(default=0)  # 정의서 항목 반영 (보증금)
    total_price = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WAITING')
    reject_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    canceled_at = models.DateTimeField(blank=True, null=True)  # 정의서 항목 반영 (취소 일자)

    class Meta:
        db_table = 'rental'

    def __str__(self):
        return f"Rental {self.rental_id} - {self.item.title} ({self.status})"


# 5. 채팅방 테이블 (정의서 명칭: chat)
class ChatRoom(models.Model):
    room_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='item_id')
    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='renter_id',
        related_name='chat_rooms'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat'

    def __str__(self):
        return f"ChatRoom {self.room_id} for Item {self.item.item_id}"


# 6. 채팅 메시지 테이블 (정의서 명칭: chat_message)
class ChatMessage(models.Model):
    MESSAGE_TYPES = [
        ('TALK', '일반 대화'),
        ('SYSTEM', '시스템 자동 메시지'),
        ('PAY_FORM', '결제 요청 폼'),
        ('PAY_COMPLETE', '결제 완료 알림'),  # 실시간 웹소켓 검증 완료 타입 유지
    ]

    message_id = models.AutoField(primary_key=True)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, db_column='room_id', related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='sender_id',
        related_name='chat_messages'
    )
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='TALK')
    content = models.TextField()
    rental = models.ForeignKey(Rental, on_delete=models.SET_NULL, blank=True, null=True, db_column='rental_id')  # booking -> rental 변경
    is_read = models.BooleanField(default=False)  # 정의서 항목 반영 (읽음 여부)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_message'

    def __str__(self):
        return f"[{self.message_type}] {self.sender.username}: {self.content[:20]}"