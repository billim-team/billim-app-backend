from django.urls import path
from .views import ItemListCreateView, ItemDetailView, ItemUpdateDeleteView

urlpatterns = [
    path('', ItemListCreateView.as_view(), name='item-list'),
    path('<int:pk>/', ItemDetailView.as_view(), name='item-detail'),
    path('<int:pk>/manage/', ItemUpdateDeleteView.as_view(), name='item-manage'),
]