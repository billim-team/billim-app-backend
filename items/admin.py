from django.contrib import admin
from .models import Category, Item, ItemImage


# 1. 카테고리 등록
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_id', 'category_name']


# 2. 물품 등록 화면 하단에 이미지 업로드 창을 끼워 넣는 설정
class ItemImageInline(admin.TabularInline):
    model = ItemImage
    extra = 1


# 3. 물품 등록 설정 수정
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['item_id', 'title', 'price_day', 'category', 'owner']
    search_fields = ['title', 'description']
    list_filter = ['category']
    inlines = [ItemImageInline]


# 4. 이미지 단독 등록 테이블 유지
@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    list_display = ['image_id', 'item', 'image', 'status_info']