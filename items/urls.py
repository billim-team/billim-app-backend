from django.urls import path
from .views import (
    ItemListCreateView,
    ItemDetailView,
    ItemUpdateDeleteView,
    RentalCreateView,
    ChatMessageListCreateView,
    RentalActionView,
    PaymentCompleteView,
    RentalReturnView,
    RentalCompleteView,
    ReviewCreateView
)

urlpatterns = [
    # 1. 물품(Item) 관련 API 주소
    path('', ItemListCreateView.as_view(), name='item-list'),
    path('<int:pk>/', ItemDetailView.as_view(), name='item-detail'),
    path('<int:pk>/manage/', ItemUpdateDeleteView.as_view(), name='item-manage'),

    # 2. 대여 예약(Rental) 및 결제/반납/정산 관련 API 주소
    path('rentals/', RentalCreateView.as_view(), name='rental-create'),
    path('rentals/<int:rental_id>/action/', RentalActionView.as_view(), name='rental-action'),
    path('rentals/<int:rental_id>/payment-complete/', PaymentCompleteView.as_view(), name='payment-complete'),

    # 반납 가이드 사진 업로드 및 제공자 최종 보증금 정산 주소
    path('rentals/<int:rental_id>/return/', RentalReturnView.as_view(), name='rental-return'),
    path('rentals/<int:rental_id>/complete/', RentalCompleteView.as_view(), name='rental-complete'),

    # 3. 리뷰(Review) 관련 API 주소
    # 정산 마감 후 대여자가 별점과 한줄평을 등록하는 주소
    path('reviews/', ReviewCreateView.as_view(), name='review-create'),

    # 4. 채팅 메시지 관련 API 주소
    path('chats/<int:room_id>/', ChatMessageListCreateView.as_view(), name='chat-message-list-create'),
]