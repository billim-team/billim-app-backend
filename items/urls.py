from django.urls import path
from .views import ItemListCreateView, ItemDetailView, ItemUpdateDeleteView, BookingCreateView, ChatMessageListCreateView, BookingActionView, PaymentCompleteView

urlpatterns = [
    path('', ItemListCreateView.as_view(), name='item-list'),
    path('<int:pk>/', ItemDetailView.as_view(), name='item-detail'),
    path('<int:pk>/manage/', ItemUpdateDeleteView.as_view(), name='item-manage'),
    path('bookings/', BookingCreateView.as_view(), name='booking-create'),
    path('chats/<int:room_id>/', ChatMessageListCreateView.as_view(), name='chat-message-list-create'),
    path('bookings/<int:booking_id>/action/', BookingActionView.as_view(), name='booking-action'),
path('bookings/<int:booking_id>/payment-complete/', PaymentCompleteView.as_view(), name='payment-complete'),
]