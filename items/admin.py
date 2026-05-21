from django.contrib import admin
from .models import Category, Item, ItemImage, Booking, ChatRoom, ChatMessage


# ==========================================
# 1. 카테고리(Category) 설정
# ==========================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_id', 'category_name']


# ==========================================
# 2. 물품(Item) 및 인라인 이미지 설정
# ==========================================
# 물품 등록 화면 하단에 이미지 업로드 창을 끼워 넣는 인라인 클래스
class ItemImageInline(admin.TabularInline):
    model = ItemImage
    extra = 1  # 기본으로 제공할 이미지 업로드 칸 개수


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['item_id', 'title', 'price_day', 'category', 'owner']
    search_fields = ['title', 'description']
    list_filter = ['category']
    inlines = [ItemImageInline]  # 물품 등록할 때 사진도 같이 올릴 수 있게 결합


@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    list_display = ['image_id', 'item', 'image', 'status_info']


# ==========================================
# 3. 대여(Booking) 및 채팅(Chat) 설정
# ==========================================
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_id', 'item', 'renter', 'start_date', 'end_date', 'status', 'total_price']
    list_filter = ['status']


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['room_id', 'item', 'renter', 'created_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'room', 'sender', 'message_type', 'content', 'timestamp']
    list_filter = ['message_type']