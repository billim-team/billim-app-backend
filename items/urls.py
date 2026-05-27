from django.urls import path
# ⭐️ Booking 관련 뷰들을 우리가 수정한 Rental 관련 뷰 이름으로 변경하여 임포트합니다.
from .views import (
    ItemListCreateView,
    ItemDetailView,
    ItemUpdateDeleteView,
    RentalCreateView,  # BookingCreateView ➡️ RentalCreateView
    ChatMessageListCreateView,
    RentalActionView,  # BookingActionView ➡️ RentalActionView
    PaymentCompleteView
)

urlpatterns = [
    # 1. 물품(Item) 관련 API 주소
    path('', ItemListCreateView.as_view(), name='item-list'),
    path('<int:pk>/', ItemDetailView.as_view(), name='item-detail'),
    path('<int:pk>/manage/', ItemUpdateDeleteView.as_view(), name='item-manage'),

    # 2. 대여 예약(Rental) 및 결제 관련 API 주소 (정의서 표준 주소로 싱크로율 100% 매핑)
    path('rentals/', RentalCreateView.as_view(), name='rental-create'),  # bookings/ ➡️ rentals/
    path('rentals/<int:rental_id>/action/', RentalActionView.as_view(), name='rental-action'),
    # booking_id ➡️ rental_id
    path('rentals/<int:rental_id>/payment-complete/', PaymentCompleteView.as_view(), name='payment-complete'),

    # 3. 채팅 메시지 관련 API 주소
    path('chats/<int:room_id>/', ChatMessageListCreateView.as_view(), name='chat-message-list-create'),
]