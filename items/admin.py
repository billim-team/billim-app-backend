from django.contrib import admin
from .models import Category, Item, ItemFile, Rental, ChatRoom, ChatMessage


# 물품 상세 페이지 안에서 파일(이미지)들을 한눈에 넣고 관리할 수 있게 해주는 Inline 설정입니다.
class ItemFileInline(admin.TabularInline):
    model = ItemFile
    extra = 1


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    inlines = [ItemFileInline]
    list_display = ['item_id', 'title', 'owner', 'price_day', 'status', 'created_at']
    list_filter = ['status', 'category']
    search_fields = ['title', 'description']


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ['rental_id', 'item', 'renter', 'start_date', 'end_date', 'status', 'total_price']
    list_filter = ['status']


# 나머지 기본 모델들 등록
admin.site.register(Category)
admin.site.register(ChatRoom)
admin.site.register(ChatMessage)