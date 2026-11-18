
from django.urls import path

from .views import OrderCheckoutView

app_name = "marketplace"

urlpatterns = [
    path(
        "orders/<int:order_id>/checkout/",
        OrderCheckoutView.as_view(),
        name="order_checkout",
    ),
]
