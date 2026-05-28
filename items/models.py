from django.db import models
from django.conf import settings


# 1. 카테고리 테이블 (정의서 명칭: category)
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'category'

    def __str__(self):
        return self.category_name


# 2. 물품 테이블 (정의서 명칭: item)
class Item(models.Model):
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
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='AVAILABLE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'item'

    def __str__(self):
        return self.title


# 3. 물품 이미지/파일 테이블 (정의서 명칭: item_file)
class ItemFile(models.Model):
    FILE_TYPE_CHOICES = [
        ('OWNER_FRONT', '제공자 등록 - 앞면'),
        ('OWNER_BACK', '제공자 등록 - 뒷면'),
        ('OWNER_LEFT', '제공자 등록 - 좌측'),
        ('OWNER_RIGHT', '제공자 등록 - 우측'),
        ('RENTER_FRONT', '대여자 반납 - 앞면'),
        ('RENTER_BACK', '대여자 반납 - 뒷면'),
        ('RENTER_LEFT', '대여자 반납 - 좌측'),
        ('RENTER_RIGHT', '대여자 반납 - 우측'),
    ]

    file_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='item_id', related_name='files')
    file_url = models.ImageField(upload_to='item_images/', blank=True, null=True)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='OWNER_FRONT')
    status_info = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'item_file'

    def __str__(self):
        get_display = getattr(self, 'get_file_type_display', lambda: "알 수 없음")
        return f"[{get_display()}] File {self.file_id} for Item {self.item.item_id}"


# 4. 대여 예약 테이블 (정의서 명칭: rental)
class Rental(models.Model):
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
    deposit = models.IntegerField(default=0)
    total_price = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WAITING')
    reject_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    canceled_at = models.DateTimeField(blank=True, null=True)

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
        ('PAY_COMPLETE', '결제 완료 알림'),
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
    rental = models.ForeignKey(Rental, on_delete=models.SET_NULL, blank=True, null=True, db_column='rental_id')
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_message'

    def __str__(self):
        return f"[{self.message_type}] {self.sender.username}: {self.content[:20]}"


# 7. 리뷰 테이블 
class Review(models.Model):
    rental = models.OneToOneField(Rental, on_delete=models.CASCADE, related_name='review')
    writer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review'

    def __str__(self):
        return f"Review for Rental {self.rental.rental_id} - ⭐{self.rating}"